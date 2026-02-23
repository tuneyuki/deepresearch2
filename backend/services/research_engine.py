from __future__ import annotations

import asyncio
import json
import logging
import re

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


def _parse_json(text: str | None) -> any:
    """Parse JSON from LLM response, handling markdown code blocks and edge cases."""
    if not text:
        return None
    # Strip markdown code block wrappers (```json ... ``` or ``` ... ```)
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    cleaned = cleaned.strip()
    return json.loads(cleaned)

from config import Settings
from services.blob_storage import BlobStorageService
from services.task_registry import TaskRegistry, ProgressEvent
from sources.base import ResearchSource


# Module-level semaphores (shared across all tasks)
_llm_semaphore: asyncio.Semaphore | None = None
_search_semaphore: asyncio.Semaphore | None = None


def _get_semaphores(config: Settings) -> tuple[asyncio.Semaphore, asyncio.Semaphore]:
    global _llm_semaphore, _search_semaphore
    if _llm_semaphore is None:
        _llm_semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_LLM_CALLS)
    if _search_semaphore is None:
        _search_semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_SEARCH_CALLS)
    return _llm_semaphore, _search_semaphore


async def run_research(
    query: str,
    task_id: str,
    registry: TaskRegistry,
    source: ResearchSource,
    config: Settings,
) -> None:
    client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    llm_sem, search_sem = _get_semaphores(config)
    task_info = registry.get_task(task_id)
    if not task_info:
        return

    task_info.status = "running"
    all_findings: list[str] = []

    try:
        # Step 1: Decompose query
        await registry.emit(
            task_id,
            ProgressEvent("progress", "Analyzing query...", 5),
        )

        async with llm_sem:
            decompose_resp = await client.chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a research assistant. Given a research query, "
                            "decompose it into 3-5 specific search queries that will "
                            "help gather comprehensive information. Return JSON: "
                            '{"queries": ["query1", "query2", ...]}.'
                        ),
                    },
                    {"role": "user", "content": query},
                ],
                temperature=0.3,
            )

        try:
            parsed = _parse_json(decompose_resp.choices[0].message.content)
            if isinstance(parsed, dict):
                sub_queries = parsed.get("queries", [query])
            elif isinstance(parsed, list):
                sub_queries = parsed
            else:
                sub_queries = [query]
            if not sub_queries:
                sub_queries = [query]
        except (json.JSONDecodeError, TypeError):
            logger.warning("Failed to parse sub-queries, using original query")
            sub_queries = [query]

        depth = 0
        current_queries = sub_queries

        while depth < config.MAX_RESEARCH_DEPTH:
            # Step 2: Search
            progress_base = 10 + depth * 20
            progress_step = max(1, 30 // max(len(current_queries), 1))

            await registry.emit(
                task_id,
                ProgressEvent(
                    "progress",
                    f"Searching for information (round {depth + 1})...",
                    progress_base,
                ),
            )

            async def _guarded_search(q: str):
                async with search_sem:
                    return await source.search(q)

            search_tasks = [_guarded_search(q) for q in current_queries]
            search_results_lists = await asyncio.gather(*search_tasks)

            all_urls: list[str] = []
            for i, results in enumerate(search_results_lists):
                progress = min(progress_base + (i + 1) * progress_step, 90)
                await registry.emit(
                    task_id,
                    ProgressEvent(
                        "progress",
                        f"Found {len(results)} results for sub-query {i + 1}",
                        progress,
                    ),
                )
                for r in results:
                    if r.url and r.url not in all_urls:
                        all_urls.append(r.url)
                        all_findings.append(
                            f"### {r.title}\nURL: {r.url}\n{r.snippet}"
                        )

            # Fetch full content for top results (max 5)
            top_urls = all_urls[:5]
            if top_urls:
                async def _guarded_fetch(u: str):
                    async with search_sem:
                        return await source.fetch_content(u)

                fetch_tasks = [_guarded_fetch(u) for u in top_urls]
                contents = await asyncio.gather(*fetch_tasks)
                for url, content in zip(top_urls, contents):
                    if content:
                        # Truncate long content
                        truncated = content[:3000]
                        all_findings.append(
                            f"### Full content from {url}\n{truncated}"
                        )

            # Step 3: Analyze if more research needed
            await registry.emit(
                task_id,
                ProgressEvent("progress", "Analyzing findings...", 50 + depth * 10),
            )

            findings_text = "\n\n".join(all_findings[-20:])  # Last 20 findings
            async with llm_sem:
                analysis_resp = await client.chat.completions.create(
                    model="gpt-4o",
                    response_format={"type": "json_object"},
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a research analyst. Given a research query and findings so far, "
                                "decide if more research is needed. Return JSON with: "
                                '{"needs_more_research": bool, "follow_up_queries": ["..."], '
                                '"key_findings": "summary of key findings so far"}.'
                            ),
                        },
                        {
                            "role": "user",
                            "content": (
                                f"Original query: {query}\n\n"
                                f"Findings so far:\n{findings_text}"
                            ),
                        },
                    ],
                    temperature=0.3,
                )

            try:
                analysis = _parse_json(analysis_resp.choices[0].message.content)
                if not isinstance(analysis, dict):
                    analysis = {"needs_more_research": False}
            except (json.JSONDecodeError, TypeError):
                logger.warning("Failed to parse analysis response, stopping research loop")
                analysis = {"needs_more_research": False}

            depth += 1

            if (
                not analysis.get("needs_more_research", False)
                or depth >= config.MAX_RESEARCH_DEPTH
            ):
                break

            current_queries = analysis.get("follow_up_queries", [])
            if not current_queries:
                break

            await registry.emit(
                task_id,
                ProgressEvent(
                    "progress",
                    f"Conducting deeper research (round {depth + 1})...",
                    50 + depth * 10,
                ),
            )

        # Step 4: Generate final report
        await registry.emit(
            task_id,
            ProgressEvent("progress", "Generating report...", 80),
        )

        findings_text = "\n\n".join(all_findings)
        async with llm_sem:
            report_resp = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a research report writer. Given a research query and "
                            "gathered findings, produce a comprehensive, well-structured "
                            "Markdown report. Include an executive summary, key findings, "
                            "detailed analysis, and references. Make it thorough and insightful."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Research query: {query}\n\n"
                            f"Gathered findings:\n{findings_text}"
                        ),
                    },
                ],
                temperature=0.4,
            )

        report = report_resp.choices[0].message.content

        # Step 5: Save report
        await registry.emit(
            task_id,
            ProgressEvent("progress", "Saving report...", 90),
        )

        storage = BlobStorageService(
            config.AZURE_STORAGE_CONNECTION_STRING,
            config.AZURE_STORAGE_CONTAINER_NAME,
        )
        result_url = await storage.upload_report(task_id, report)

        task_info.status = "completed"
        task_info.result_url = result_url
        task_info.progress = 100

        await registry.emit(
            task_id,
            ProgressEvent(
                "completed",
                "Research complete!",
                100,
                {"result_url": result_url, "report": report},
            ),
        )

    except asyncio.CancelledError:
        task_info.status = "failed"
        task_info.error = "Cancelled by user"
        await registry.emit(
            task_id,
            ProgressEvent("failed", "Research cancelled.", task_info.progress),
        )
    except Exception as e:
        logger.error(f"Research failed for task {task_id}: {e}", exc_info=True)
        task_info.status = "failed"
        task_info.error = str(e)
        await registry.emit(
            task_id,
            ProgressEvent("failed", f"Research failed: {e}", task_info.progress),
        )
