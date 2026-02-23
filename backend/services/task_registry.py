from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import AsyncGenerator


@dataclass
class ProgressEvent:
    event_type: str
    message: str
    progress: int
    data: dict = field(default_factory=dict)


@dataclass
class TaskInfo:
    id: str
    status: str = "pending"
    progress: int = 0
    messages: list[dict] = field(default_factory=list)
    result_url: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None


class TaskRegistry:
    def __init__(self) -> None:
        self.tasks: dict[str, TaskInfo] = {}
        self._queues: dict[str, list[asyncio.Queue]] = {}
        self._async_tasks: dict[str, asyncio.Task] = {}

    def create_task(self, task_id: str, coroutine) -> TaskInfo:
        info = TaskInfo(id=task_id)
        self.tasks[task_id] = info
        self._queues[task_id] = []
        async_task = asyncio.create_task(coroutine)
        self._async_tasks[task_id] = async_task
        return info

    def get_task(self, task_id: str) -> TaskInfo | None:
        return self.tasks.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        async_task = self._async_tasks.get(task_id)
        if async_task and not async_task.done():
            async_task.cancel()
            task_info = self.tasks.get(task_id)
            if task_info:
                task_info.status = "failed"
                task_info.error = "Cancelled by user"
            return True
        return False

    async def emit(self, task_id: str, event: ProgressEvent) -> None:
        task_info = self.tasks.get(task_id)
        if task_info:
            task_info.progress = event.progress
            task_info.messages.append(
                {"role": "assistant", "content": event.message}
            )
        queues = self._queues.get(task_id, [])
        for q in queues:
            await q.put(event)

    async def subscribe(self, task_id: str) -> AsyncGenerator[ProgressEvent, None]:
        q: asyncio.Queue[ProgressEvent | None] = asyncio.Queue()
        self._queues.setdefault(task_id, []).append(q)
        try:
            while True:
                event = await q.get()
                if event is None:
                    break
                yield event
                if event.event_type in ("completed", "failed"):
                    break
        finally:
            queues = self._queues.get(task_id, [])
            if q in queues:
                queues.remove(q)


registry = TaskRegistry()
