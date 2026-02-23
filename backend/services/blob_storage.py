from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from pathlib import Path


class BlobStorageService:
    def __init__(self, connection_string: str, container_name: str) -> None:
        self.connection_string = connection_string
        self.container_name = container_name

    async def upload_report(self, task_id: str, content: str) -> str:
        if not self.connection_string:
            return await self._save_local(task_id, content)

        from azure.storage.blob.aio import BlobServiceClient

        blob_name = f"{task_id}.md"
        async with BlobServiceClient.from_connection_string(
            self.connection_string
        ) as service:
            container = service.get_container_client(self.container_name)
            try:
                await container.create_container()
            except Exception:
                pass
            blob = container.get_blob_client(blob_name)
            await blob.upload_blob(content.encode("utf-8"), overwrite=True)

        return await self.get_report_url(task_id)

    async def get_report_url(self, task_id: str) -> str:
        if not self.connection_string:
            local_path = Path("local_reports") / f"{task_id}.md"
            return str(local_path)

        from azure.storage.blob import generate_blob_sas, BlobSasPermissions
        from azure.storage.blob.aio import BlobServiceClient

        blob_name = f"{task_id}.md"
        async with BlobServiceClient.from_connection_string(
            self.connection_string
        ) as service:
            sas_token = generate_blob_sas(
                account_name=service.account_name,
                container_name=self.container_name,
                blob_name=blob_name,
                account_key=service.credential.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.now(timezone.utc) + timedelta(hours=24),
            )
            return f"{service.url}{self.container_name}/{blob_name}?{sas_token}"

    async def _save_local(self, task_id: str, content: str) -> str:
        local_dir = Path("local_reports")
        local_dir.mkdir(exist_ok=True)
        file_path = local_dir / f"{task_id}.md"
        file_path.write_text(content, encoding="utf-8")
        return str(file_path)
