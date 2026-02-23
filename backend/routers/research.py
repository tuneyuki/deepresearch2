from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import settings
from services.task_registry import registry
from services.research_engine import run_research
from sources.web_source import WebSource

router = APIRouter(prefix="/research", tags=["research"])


class ResearchRequest(BaseModel):
    query: str


class ResearchResponse(BaseModel):
    task_id: str


@router.post("", response_model=ResearchResponse)
async def start_research(request: ResearchRequest):
    task_id = str(uuid.uuid4())
    source = WebSource(api_key=settings.FIRECRAWL_API_KEY)
    coro = run_research(
        query=request.query,
        task_id=task_id,
        registry=registry,
        source=source,
        config=settings,
    )
    registry.create_task(task_id, coro)
    return ResearchResponse(task_id=task_id)


@router.get("/{task_id}")
async def get_task_status(task_id: str):
    task_info = registry.get_task(task_id)
    if not task_info:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "id": task_info.id,
        "status": task_info.status,
        "progress": task_info.progress,
        "messages": task_info.messages,
        "result_url": task_info.result_url,
        "created_at": task_info.created_at.isoformat(),
        "error": task_info.error,
    }


@router.get("/{task_id}/stream")
async def stream_task(task_id: str):
    task_info = registry.get_task(task_id)
    if not task_info:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        async for event in registry.subscribe(task_id):
            data = {
                "event_type": event.event_type,
                "message": event.message,
                "progress": event.progress,
                "data": event.data,
            }
            yield f"data: {json.dumps(data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str):
    task_info = registry.get_task(task_id)
    if not task_info:
        raise HTTPException(status_code=404, detail="Task not found")
    cancelled = registry.cancel_task(task_id)
    if not cancelled:
        raise HTTPException(status_code=400, detail="Task cannot be cancelled")
    return {"status": "cancelled"}
