"""
LABOS Sandbox Sync Manager

Handles asynchronous synchronization between local sandbox and GCS.
This ensures data persistence even if the local storage is ephemeral (like Cloud Run).

Sync Strategy:
    - Write-through: Files are written locally first, then queued for GCS sync
    - Read-through: If file not found locally, attempt to fetch from GCS
    - Background sync: A background worker processes the sync queue
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from collections import deque
from threading import Lock
import json

logger = logging.getLogger(__name__)


class SyncTask:
    """Represents a sync task to be processed."""

    def __init__(
        self,
        action: str,  # "upload" or "download"
        local_path: str,
        gcs_path: str,
        user_id: str,
        project_id: str,
        priority: int = 0
    ):
        self.action = action
        self.local_path = local_path
        self.gcs_path = gcs_path
        self.user_id = user_id
        self.project_id = project_id
        self.priority = priority
        self.created_at = datetime.utcnow()
        self.retries = 0
        self.max_retries = 3


class SandboxSyncManager:
    """
    Manages synchronization between local sandbox and GCS.

    Features:
    - Async background sync worker
    - Retry logic for failed uploads
    - Priority queue for important files
    """

    def __init__(self, sandbox_root: Optional[str] = None):
        self.sandbox_root = Path(
            sandbox_root or os.getenv("SANDBOX_ROOT", "./data/sandboxes")
        ).resolve()

        self.gcs_bucket = os.getenv("GCS_SANDBOX_BUCKET", "labos-sandboxes")
        self.sync_enabled = os.getenv("SYNC_TO_GCS", "false").lower() == "true"

        # Sync queue
        self._queue: deque = deque()
        self._queue_lock = Lock()

        # GCS client (lazy init)
        self._gcs_client = None
        self._bucket = None

        # Background worker state
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False

        logger.info(f"SandboxSyncManager initialized: sync_enabled={self.sync_enabled}")

    # ==================== GCS Client ====================

    def _get_gcs_client(self):
        """Lazy initialize GCS client."""
        if self._gcs_client is None:
            try:
                from google.cloud import storage
                self._gcs_client = storage.Client()
                self._bucket = self._gcs_client.bucket(self.gcs_bucket)
                logger.info(f"GCS client initialized for bucket: {self.gcs_bucket}")
            except Exception as e:
                logger.error(f"Failed to initialize GCS client: {e}")
                raise
        return self._gcs_client, self._bucket

    # ==================== Queue Management ====================

    def queue_upload(
        self,
        local_path: str,
        user_id: str,
        project_id: str,
        relative_path: str,
        priority: int = 0
    ):
        """Queue a file for upload to GCS."""
        if not self.sync_enabled:
            return

        gcs_path = f"{user_id}/{project_id}/{relative_path}"

        task = SyncTask(
            action="upload",
            local_path=local_path,
            gcs_path=gcs_path,
            user_id=user_id,
            project_id=project_id,
            priority=priority
        )

        with self._queue_lock:
            self._queue.append(task)

        logger.debug(f"Queued upload: {local_path} -> gs://{self.gcs_bucket}/{gcs_path}")

    def queue_download(
        self,
        user_id: str,
        project_id: str,
        relative_path: str,
        local_path: str,
        priority: int = 10  # Downloads are higher priority
    ):
        """Queue a file for download from GCS."""
        if not self.sync_enabled:
            return

        gcs_path = f"{user_id}/{project_id}/{relative_path}"

        task = SyncTask(
            action="download",
            local_path=local_path,
            gcs_path=gcs_path,
            user_id=user_id,
            project_id=project_id,
            priority=priority
        )

        with self._queue_lock:
            # Insert at front for higher priority
            self._queue.appendleft(task)

        logger.debug(f"Queued download: gs://{self.gcs_bucket}/{gcs_path} -> {local_path}")

    # ==================== Sync Operations ====================

    async def upload_file(self, local_path: str, gcs_path: str) -> bool:
        """Upload a single file to GCS."""
        try:
            _, bucket = self._get_gcs_client()
            blob = bucket.blob(gcs_path)

            # Upload with metadata
            blob.upload_from_filename(
                local_path,
                timeout=300  # 5 minutes for large files
            )

            logger.info(f"Uploaded: {local_path} -> gs://{self.gcs_bucket}/{gcs_path}")
            return True

        except Exception as e:
            logger.error(f"Upload failed: {local_path} -> {gcs_path}: {e}")
            return False

    async def download_file(self, gcs_path: str, local_path: str) -> bool:
        """Download a single file from GCS."""
        try:
            _, bucket = self._get_gcs_client()
            blob = bucket.blob(gcs_path)

            if not blob.exists():
                logger.warning(f"GCS file not found: gs://{self.gcs_bucket}/{gcs_path}")
                return False

            # Ensure local directory exists
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)

            blob.download_to_filename(local_path)
            logger.info(f"Downloaded: gs://{self.gcs_bucket}/{gcs_path} -> {local_path}")
            return True

        except Exception as e:
            logger.error(f"Download failed: {gcs_path} -> {local_path}: {e}")
            return False

    async def ensure_local(
        self,
        user_id: str,
        project_id: str,
        relative_path: str
    ) -> Optional[str]:
        """
        Ensure a file exists locally, downloading from GCS if needed.

        Returns the local path if successful, None otherwise.
        """
        local_path = self.sandbox_root / user_id / project_id / relative_path

        # Already exists locally
        if local_path.exists():
            return str(local_path)

        # Try to download from GCS
        if self.sync_enabled:
            gcs_path = f"{user_id}/{project_id}/{relative_path}"
            success = await self.download_file(gcs_path, str(local_path))
            if success:
                return str(local_path)

        return None

    # ==================== Background Worker ====================

    async def _process_queue(self):
        """Process the sync queue in the background."""
        while self._running:
            task = None

            with self._queue_lock:
                if self._queue:
                    task = self._queue.popleft()

            if task:
                success = False

                if task.action == "upload":
                    success = await self.upload_file(task.local_path, task.gcs_path)
                elif task.action == "download":
                    success = await self.download_file(task.gcs_path, task.local_path)

                # Retry on failure
                if not success and task.retries < task.max_retries:
                    task.retries += 1
                    with self._queue_lock:
                        self._queue.append(task)
                    logger.warning(f"Retrying task ({task.retries}/{task.max_retries}): {task.gcs_path}")

            else:
                # No tasks, wait a bit
                await asyncio.sleep(1)

    def start_worker(self):
        """Start the background sync worker."""
        if not self.sync_enabled:
            logger.info("Sync disabled, not starting worker")
            return

        if self._running:
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._process_queue())
        logger.info("Sync worker started")

    def stop_worker(self):
        """Stop the background sync worker."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            self._worker_task = None
        logger.info("Sync worker stopped")

    # ==================== Bulk Operations ====================

    async def sync_project_to_gcs(self, user_id: str, project_id: str) -> Dict[str, Any]:
        """
        Sync entire project to GCS.

        Returns summary of synced files.
        """
        if not self.sync_enabled:
            return {"synced": False, "reason": "sync_disabled"}

        project_dir = self.sandbox_root / user_id / project_id
        if not project_dir.exists():
            return {"synced": False, "reason": "project_not_found"}

        uploaded = []
        failed = []

        for file_path in project_dir.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith("."):
                relative = file_path.relative_to(project_dir)
                gcs_path = f"{user_id}/{project_id}/{relative}"

                success = await self.upload_file(str(file_path), gcs_path)
                if success:
                    uploaded.append(str(relative))
                else:
                    failed.append(str(relative))

        return {
            "synced": True,
            "uploaded_count": len(uploaded),
            "failed_count": len(failed),
            "uploaded": uploaded,
            "failed": failed
        }

    async def sync_project_from_gcs(self, user_id: str, project_id: str) -> Dict[str, Any]:
        """
        Sync entire project from GCS to local.

        Useful for Cloud Run cold starts.
        """
        if not self.sync_enabled:
            return {"synced": False, "reason": "sync_disabled"}

        try:
            _, bucket = self._get_gcs_client()
            prefix = f"{user_id}/{project_id}/"

            downloaded = []
            failed = []

            blobs = bucket.list_blobs(prefix=prefix)
            for blob in blobs:
                relative = blob.name[len(prefix):]
                local_path = self.sandbox_root / user_id / project_id / relative

                success = await self.download_file(blob.name, str(local_path))
                if success:
                    downloaded.append(relative)
                else:
                    failed.append(relative)

            return {
                "synced": True,
                "downloaded_count": len(downloaded),
                "failed_count": len(failed),
                "downloaded": downloaded,
                "failed": failed
            }

        except Exception as e:
            logger.error(f"Failed to sync project from GCS: {e}")
            return {"synced": False, "reason": str(e)}

    # ==================== Cleanup ====================

    async def delete_from_gcs(self, user_id: str, project_id: str, relative_path: str) -> bool:
        """Delete a file from GCS."""
        if not self.sync_enabled:
            return True

        try:
            _, bucket = self._get_gcs_client()
            gcs_path = f"{user_id}/{project_id}/{relative_path}"
            blob = bucket.blob(gcs_path)

            if blob.exists():
                blob.delete()
                logger.info(f"Deleted from GCS: gs://{self.gcs_bucket}/{gcs_path}")

            return True

        except Exception as e:
            logger.error(f"Failed to delete from GCS: {e}")
            return False

    async def delete_project_from_gcs(self, user_id: str, project_id: str) -> bool:
        """Delete entire project from GCS."""
        if not self.sync_enabled:
            return True

        try:
            _, bucket = self._get_gcs_client()
            prefix = f"{user_id}/{project_id}/"

            blobs = bucket.list_blobs(prefix=prefix)
            for blob in blobs:
                blob.delete()

            logger.info(f"Deleted project from GCS: gs://{self.gcs_bucket}/{prefix}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete project from GCS: {e}")
            return False


# Global singleton
_sync_manager: Optional[SandboxSyncManager] = None


def get_sync_manager() -> SandboxSyncManager:
    """Get the global sync manager instance."""
    global _sync_manager
    if _sync_manager is None:
        _sync_manager = SandboxSyncManager()
    return _sync_manager
