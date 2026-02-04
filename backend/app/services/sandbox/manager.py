"""
LABOS Sandbox Manager

Provides secure, isolated file storage for each user's projects.
Each user has their own sandbox directory that is completely isolated.

Directory Structure:
    /data/sandboxes/{user_id}/{project_id}/
    ├── uploads/          # User uploaded files
    ├── generated/        # Agent generated files
    ├── workspace/        # Temporary working files
    └── .metadata.json    # Project metadata

Security Features:
    - Path validation to prevent directory traversal attacks
    - User isolation - users can only access their own sandboxes
    - Automatic cleanup of temporary files
"""

import os
import json
import hashlib
import shutil
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from uuid import uuid4
import logging

logger = logging.getLogger(__name__)


class SandboxSecurityError(Exception):
    """Raised when a security violation is detected."""
    pass


class SandboxManager:
    """
    Manages isolated sandbox directories for user projects.

    Thread-safe and supports both sync and async operations.
    """

    # Subdirectory names
    UPLOADS_DIR = "uploads"
    GENERATED_DIR = "generated"
    WORKSPACE_DIR = "workspace"
    TOOLS_DIR = "tools"
    METADATA_FILE = ".metadata.json"
    TOOLS_MANIFEST = "tools_manifest.json"

    # File size limits
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB for local storage

    def __init__(self, root_path: Optional[str] = None):
        """
        Initialize the sandbox manager.

        Args:
            root_path: Root directory for all sandboxes.
                      Defaults to SANDBOX_ROOT env var or ./data/sandboxes
        """
        self.root = Path(
            root_path or
            os.getenv("SANDBOX_ROOT", "./data/sandboxes")
        ).resolve()

        # Whether to sync to GCS
        self.sync_enabled = os.getenv("SYNC_TO_GCS", "false").lower() == "true"
        self.gcs_bucket = os.getenv("GCS_SANDBOX_BUCKET", "labos-sandboxes")

        # Ensure root exists
        self.root.mkdir(parents=True, exist_ok=True)

        logger.info(f"SandboxManager initialized: root={self.root}, sync={self.sync_enabled}")

    # ==================== Path Validation ====================

    def _validate_user_id(self, user_id: str) -> str:
        """Validate and sanitize user ID.

        Supports Auth0 user IDs like 'google-oauth2|105502861078525151574'
        by converting special characters to underscores.
        """
        if not user_id or not isinstance(user_id, str):
            raise SandboxSecurityError("Invalid user_id")

        # Remove any path separators and convert Auth0 pipe character
        sanitized = (user_id
            .replace("/", "_")
            .replace("\\", "_")
            .replace("..", "_")
            .replace("|", "_"))  # Auth0 uses | in user IDs

        # Must be alphanumeric with some allowed characters
        if not all(c.isalnum() or c in "-_@." for c in sanitized):
            raise SandboxSecurityError(f"Invalid characters in user_id: {user_id}")

        return sanitized

    def _validate_project_id(self, project_id: str) -> str:
        """Validate and sanitize project ID."""
        if not project_id or not isinstance(project_id, str):
            raise SandboxSecurityError("Invalid project_id")

        # Remove any path separators
        sanitized = project_id.replace("/", "_").replace("\\", "_").replace("..", "_")

        # Must be alphanumeric with some allowed characters (UUID format)
        if not all(c.isalnum() or c in "-_" for c in sanitized):
            raise SandboxSecurityError(f"Invalid characters in project_id: {project_id}")

        return sanitized

    def _validate_filename(self, filename: str) -> str:
        """Validate and sanitize filename."""
        if not filename or not isinstance(filename, str):
            raise SandboxSecurityError("Invalid filename")

        # Get just the filename, remove any path components
        name = Path(filename).name

        # Remove dangerous characters
        sanitized = name.replace("..", "_").replace("/", "_").replace("\\", "_")

        # Check for hidden files (optional - you might want to allow them)
        if sanitized.startswith(".") and sanitized != self.METADATA_FILE:
            sanitized = "_" + sanitized[1:]

        return sanitized

    def _validate_path_within_sandbox(self, path: Path, sandbox_root: Path) -> Path:
        """
        Ensure a path is within the sandbox directory.

        This is the critical security check to prevent directory traversal.
        """
        try:
            resolved = path.resolve()
            sandbox_resolved = sandbox_root.resolve()

            # Check if the path is within the sandbox
            resolved.relative_to(sandbox_resolved)
            return resolved
        except ValueError:
            raise SandboxSecurityError(
                f"Path traversal detected: {path} is outside sandbox {sandbox_root}"
            )

    # ==================== Directory Management ====================

    def get_user_sandbox(self, user_id: str) -> Path:
        """Get the root sandbox directory for a user."""
        safe_user_id = self._validate_user_id(user_id)
        return self.root / safe_user_id

    def get_project_sandbox(self, user_id: str, project_id: str) -> Path:
        """Get the sandbox directory for a specific project."""
        safe_user_id = self._validate_user_id(user_id)
        safe_project_id = self._validate_project_id(project_id)
        return self.root / safe_user_id / safe_project_id

    def ensure_project_sandbox(self, user_id: str, project_id: str) -> Path:
        """
        Ensure a project sandbox exists with all subdirectories.

        Returns the project sandbox path.
        """
        project_dir = self.get_project_sandbox(user_id, project_id)

        # Create subdirectories
        (project_dir / self.UPLOADS_DIR).mkdir(parents=True, exist_ok=True)
        (project_dir / self.GENERATED_DIR).mkdir(parents=True, exist_ok=True)
        (project_dir / self.WORKSPACE_DIR).mkdir(parents=True, exist_ok=True)
        (project_dir / self.TOOLS_DIR).mkdir(parents=True, exist_ok=True)

        # Create metadata file if not exists
        metadata_path = project_dir / self.METADATA_FILE
        if not metadata_path.exists():
            self._write_metadata(project_dir, {
                "user_id": user_id,
                "project_id": project_id,
                "created_at": datetime.utcnow().isoformat(),
                "files": []
            })

        return project_dir

    # ==================== File Operations ====================

    def save_file(
        self,
        user_id: str,
        project_id: str,
        filename: str,
        content: bytes,
        category: str = "generated",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Save a file to the project sandbox.

        Args:
            user_id: User ID
            project_id: Project ID
            filename: Original filename
            content: File content as bytes
            category: "uploads", "generated", or "workspace"
            metadata: Optional metadata to store

        Returns:
            Dict with file_id, local_path, and other info
        """
        # Validate inputs
        safe_filename = self._validate_filename(filename)

        # Determine target directory
        if category == "uploads":
            subdir = self.UPLOADS_DIR
        elif category == "workspace":
            subdir = self.WORKSPACE_DIR
        else:
            subdir = self.GENERATED_DIR

        # Ensure sandbox exists
        project_dir = self.ensure_project_sandbox(user_id, project_id)
        target_dir = project_dir / subdir

        # Generate unique filename to avoid collisions
        file_id = uuid4().hex[:12]
        name, ext = os.path.splitext(safe_filename)
        unique_filename = f"{name}_{file_id}{ext}"

        # Final path
        file_path = target_dir / unique_filename

        # Validate path is within sandbox (defense in depth)
        self._validate_path_within_sandbox(file_path, project_dir)

        # Check file size
        if len(content) > self.MAX_FILE_SIZE:
            raise SandboxSecurityError(
                f"File too large: {len(content)} bytes (max {self.MAX_FILE_SIZE})"
            )

        # Write file
        file_path.write_bytes(content)

        # Calculate hash
        file_hash = hashlib.sha256(content).hexdigest()

        # Update metadata
        file_info = {
            "file_id": file_id,
            "filename": unique_filename,
            "original_filename": safe_filename,
            "category": category,
            "size": len(content),
            "hash": file_hash,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }

        self._add_file_to_metadata(project_dir, file_info)

        logger.info(f"Saved file: {file_path} ({len(content)} bytes)")

        # Return info
        return {
            "success": True,
            "file_id": file_id,
            "filename": unique_filename,
            "original_filename": safe_filename,
            "local_path": str(file_path),
            "relative_path": f"{subdir}/{unique_filename}",
            "size": len(content),
            "hash": file_hash,
            "gcs_uri": f"gs://{self.gcs_bucket}/{user_id}/{project_id}/{subdir}/{unique_filename}" if self.sync_enabled else None
        }

    def read_file(
        self,
        user_id: str,
        project_id: str,
        filename: str,
        category: Optional[str] = None
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Read a file from the project sandbox.

        Args:
            user_id: User ID
            project_id: Project ID
            filename: Filename to read
            category: Optional category hint ("uploads", "generated", "workspace")

        Returns:
            Tuple of (content bytes, file metadata)
        """
        project_dir = self.get_project_sandbox(user_id, project_id)

        # Search for the file
        if category:
            search_dirs = [project_dir / category]
        else:
            search_dirs = [
                project_dir / self.UPLOADS_DIR,
                project_dir / self.GENERATED_DIR,
                project_dir / self.WORKSPACE_DIR,
                project_dir,  # Fallback: check project root for legacy files
            ]

        safe_filename = self._validate_filename(filename)

        for search_dir in search_dirs:
            # Try exact match first
            file_path = search_dir / safe_filename
            if file_path.exists():
                self._validate_path_within_sandbox(file_path, project_dir)
                content = file_path.read_bytes()
                return content, {
                    "filename": safe_filename,
                    "path": str(file_path),
                    "size": len(content),
                    "category": search_dir.name
                }

            # Try pattern match (for files with UUID suffix)
            for f in search_dir.glob(f"*"):
                if f.name == safe_filename or f.name.startswith(safe_filename.rsplit(".", 1)[0]):
                    self._validate_path_within_sandbox(f, project_dir)
                    content = f.read_bytes()
                    return content, {
                        "filename": f.name,
                        "path": str(f),
                        "size": len(content),
                        "category": search_dir.name
                    }

        raise FileNotFoundError(f"File not found: {filename}")

    def read_file_by_path(
        self,
        user_id: str,
        project_id: str,
        relative_path: str
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Read a file using its relative path within the sandbox.

        Args:
            user_id: User ID
            project_id: Project ID
            relative_path: Path relative to project sandbox (e.g., "generated/chart.png")

        Returns:
            Tuple of (content bytes, file metadata)
        """
        project_dir = self.get_project_sandbox(user_id, project_id)
        file_path = project_dir / relative_path

        # Critical security check
        self._validate_path_within_sandbox(file_path, project_dir)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {relative_path}")

        content = file_path.read_bytes()
        return content, {
            "filename": file_path.name,
            "path": str(file_path),
            "relative_path": relative_path,
            "size": len(content)
        }

    def list_files(
        self,
        user_id: str,
        project_id: str,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all files in a project sandbox.

        Args:
            user_id: User ID
            project_id: Project ID
            category: Optional filter by category

        Returns:
            List of file info dicts
        """
        project_dir = self.get_project_sandbox(user_id, project_id)

        if not project_dir.exists():
            return []

        files = []

        if category:
            search_dirs = [(category, project_dir / category)]
        else:
            search_dirs = [
                (self.UPLOADS_DIR, project_dir / self.UPLOADS_DIR),
                (self.GENERATED_DIR, project_dir / self.GENERATED_DIR),
                (self.WORKSPACE_DIR, project_dir / self.WORKSPACE_DIR),
            ]

        for cat, search_dir in search_dirs:
            if not search_dir.exists():
                continue

            for f in search_dir.iterdir():
                if f.is_file() and not f.name.startswith("."):
                    files.append({
                        "filename": f.name,
                        "category": cat,
                        "relative_path": f"{cat}/{f.name}",
                        "size": f.stat().st_size,
                        "modified_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                    })

        # Fallback: check project root for legacy files (saved without category)
        for f in project_dir.iterdir():
            if f.is_file() and not f.name.startswith("."):
                files.append({
                    "filename": f.name,
                    "category": "legacy",
                    "relative_path": f.name,
                    "size": f.stat().st_size,
                    "modified_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                })

        return sorted(files, key=lambda x: x.get("modified_at", ""), reverse=True)

    def delete_file(
        self,
        user_id: str,
        project_id: str,
        filename: str,
        category: Optional[str] = None
    ) -> bool:
        """
        Delete a file from the project sandbox.

        Returns True if file was deleted.
        """
        project_dir = self.get_project_sandbox(user_id, project_id)

        if category:
            search_dirs = [project_dir / category]
        else:
            search_dirs = [
                project_dir / self.UPLOADS_DIR,
                project_dir / self.GENERATED_DIR,
                project_dir / self.WORKSPACE_DIR,
            ]

        safe_filename = self._validate_filename(filename)

        for search_dir in search_dirs:
            file_path = search_dir / safe_filename
            if file_path.exists():
                self._validate_path_within_sandbox(file_path, project_dir)
                file_path.unlink()
                self._remove_file_from_metadata(project_dir, safe_filename)
                logger.info(f"Deleted file: {file_path}")
                return True

        return False

    # ==================== Metadata Management ====================

    def _read_metadata(self, project_dir: Path) -> Dict[str, Any]:
        """Read project metadata."""
        metadata_path = project_dir / self.METADATA_FILE
        if metadata_path.exists():
            return json.loads(metadata_path.read_text())
        return {"files": []}

    def _write_metadata(self, project_dir: Path, metadata: Dict[str, Any]):
        """Write project metadata."""
        metadata_path = project_dir / self.METADATA_FILE
        metadata_path.write_text(json.dumps(metadata, indent=2))

    def _add_file_to_metadata(self, project_dir: Path, file_info: Dict[str, Any]):
        """Add a file to project metadata."""
        metadata = self._read_metadata(project_dir)
        metadata["files"].append(file_info)
        metadata["updated_at"] = datetime.utcnow().isoformat()
        self._write_metadata(project_dir, metadata)

    def _remove_file_from_metadata(self, project_dir: Path, filename: str):
        """Remove a file from project metadata."""
        metadata = self._read_metadata(project_dir)
        metadata["files"] = [
            f for f in metadata.get("files", [])
            if f.get("filename") != filename
        ]
        metadata["updated_at"] = datetime.utcnow().isoformat()
        self._write_metadata(project_dir, metadata)

    # ==================== Tool Management ====================

    def _read_tools_manifest(self, project_dir: Path) -> Dict[str, Any]:
        """Read tools_manifest.json, returning default structure if not present."""
        manifest_path = project_dir / self.TOOLS_DIR / self.TOOLS_MANIFEST
        if manifest_path.exists():
            return json.loads(manifest_path.read_text())
        return {"version": "1.0", "tools": []}

    def _write_tools_manifest(self, project_dir: Path, manifest: Dict[str, Any]):
        """Write tools_manifest.json."""
        tools_dir = project_dir / self.TOOLS_DIR
        tools_dir.mkdir(parents=True, exist_ok=True)
        manifest["updated_at"] = datetime.utcnow().isoformat()
        manifest_path = tools_dir / self.TOOLS_MANIFEST
        manifest_path.write_text(json.dumps(manifest, indent=2))

    def save_tool_file(
        self,
        user_id: str,
        project_id: str,
        tool_name: str,
        tool_code: str,
        description: str,
        category: str = "custom",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Save a tool .py file and update tools_manifest.json.

        Args:
            user_id: User ID
            project_id: Project ID
            tool_name: Tool function name (must be valid Python identifier)
            tool_code: Complete Python source code
            description: Tool description
            category: Tool category
            metadata: Optional extra metadata

        Returns:
            Dict with tool_name, filename, local_path, etc.
        """
        # Validate tool_name is a valid Python identifier
        if not tool_name.isidentifier():
            raise SandboxSecurityError(f"Invalid tool name (not a valid Python identifier): {tool_name}")

        project_dir = self.ensure_project_sandbox(user_id, project_id)
        tools_dir = project_dir / self.TOOLS_DIR

        filename = f"{tool_name}.py"
        file_path = tools_dir / filename
        self._validate_path_within_sandbox(file_path, project_dir)

        # Write the .py file
        file_path.write_text(tool_code, encoding="utf-8")

        # Compute hash
        code_hash = hashlib.sha256(tool_code.encode("utf-8")).hexdigest()

        # Update manifest
        manifest = self._read_tools_manifest(project_dir)
        # Remove existing entry with same name (update case)
        manifest["tools"] = [t for t in manifest["tools"] if t["name"] != tool_name]
        manifest["tools"].append({
            "name": tool_name,
            "filename": filename,
            "description": description,
            "category": category,
            "created_at": datetime.utcnow().isoformat(),
            "created_by_agent": "tool_creation_agent",
            "code_hash": code_hash,
            "status": "active",
            "metadata": metadata or {}
        })
        self._write_tools_manifest(project_dir, manifest)

        logger.info(f"Saved tool file: {file_path}")

        return {
            "tool_name": tool_name,
            "filename": filename,
            "local_path": str(file_path),
            "relative_path": f"{self.TOOLS_DIR}/{filename}",
            "code_hash": code_hash,
        }

    def list_tools(
        self,
        user_id: str,
        project_id: str,
        status: str = "active"
    ) -> List[Dict[str, Any]]:
        """Read tools_manifest.json and return tool entries filtered by status."""
        project_dir = self.get_project_sandbox(user_id, project_id)
        manifest = self._read_tools_manifest(project_dir)
        if status:
            return [t for t in manifest.get("tools", []) if t.get("status") == status]
        return manifest.get("tools", [])

    def read_tool_code(
        self,
        user_id: str,
        project_id: str,
        tool_name: str
    ) -> str:
        """Read raw Python source from tools/{tool_name}.py."""
        project_dir = self.get_project_sandbox(user_id, project_id)
        file_path = project_dir / self.TOOLS_DIR / f"{tool_name}.py"
        self._validate_path_within_sandbox(file_path, project_dir)

        if not file_path.exists():
            raise FileNotFoundError(f"Tool not found: {tool_name}")

        return file_path.read_text(encoding="utf-8")

    def delete_tool_file(
        self,
        user_id: str,
        project_id: str,
        tool_name: str
    ) -> bool:
        """Remove .py file and update manifest status to 'deleted'."""
        project_dir = self.get_project_sandbox(user_id, project_id)
        file_path = project_dir / self.TOOLS_DIR / f"{tool_name}.py"

        # Remove the file if it exists
        deleted = False
        if file_path.exists():
            self._validate_path_within_sandbox(file_path, project_dir)
            file_path.unlink()
            deleted = True

        # Update manifest
        manifest = self._read_tools_manifest(project_dir)
        manifest["tools"] = [t for t in manifest["tools"] if t["name"] != tool_name]
        self._write_tools_manifest(project_dir, manifest)

        if deleted:
            logger.info(f"Deleted tool: {tool_name} from {project_dir}")

        return deleted

    # ==================== Cleanup ====================

    def cleanup_workspace(self, user_id: str, project_id: str):
        """Clean up temporary workspace files."""
        project_dir = self.get_project_sandbox(user_id, project_id)
        workspace_dir = project_dir / self.WORKSPACE_DIR

        if workspace_dir.exists():
            for f in workspace_dir.iterdir():
                if f.is_file():
                    f.unlink()
            logger.info(f"Cleaned workspace: {workspace_dir}")

    def delete_project_sandbox(self, user_id: str, project_id: str):
        """Delete entire project sandbox (use with caution)."""
        project_dir = self.get_project_sandbox(user_id, project_id)

        if project_dir.exists():
            shutil.rmtree(project_dir)
            logger.warning(f"Deleted project sandbox: {project_dir}")

    # ==================== Utility ====================

    def get_sandbox_stats(self, user_id: str) -> Dict[str, Any]:
        """Get storage statistics for a user."""
        user_dir = self.get_user_sandbox(user_id)

        if not user_dir.exists():
            return {"total_size": 0, "project_count": 0, "file_count": 0}

        total_size = 0
        file_count = 0
        project_count = 0

        for project_dir in user_dir.iterdir():
            if project_dir.is_dir():
                project_count += 1
                for f in project_dir.rglob("*"):
                    if f.is_file():
                        total_size += f.stat().st_size
                        file_count += 1

        return {
            "total_size": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "project_count": project_count,
            "file_count": file_count
        }


# Global singleton instance
_sandbox_manager: Optional[SandboxManager] = None


def get_sandbox_manager() -> SandboxManager:
    """Get the global sandbox manager instance."""
    global _sandbox_manager
    if _sandbox_manager is None:
        _sandbox_manager = SandboxManager()
    return _sandbox_manager
