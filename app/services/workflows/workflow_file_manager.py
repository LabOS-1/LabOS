"""
Workflow File Manager
Handles file management for workflows, including project output directories
and automatic file registration.

This module extracts file management logic from labos_service.py to provide
a clean interface for workflow file operations.
"""

import os
import hashlib
from typing import Optional
from datetime import datetime

from .workflow_events import workflow_event_queue, WorkflowEvent


class WorkflowFileManager:
    """
    Manages files and directories for workflows.

    Responsibilities:
    - Create and manage project output directories
    - Auto-register files created during workflow execution
    - Handle file metadata and visualization detection
    """

    @staticmethod
    def get_project_output_dir(project_id: Optional[str]) -> str:
        """
        Get the output directory for a project.

        Each project has a fixed directory: /tmp/stella_projects/project_{project_id}/
        This is persistent and shared across all workflows in the same project.

        Args:
            project_id: Project identifier

        Returns:
            Path to the project's output directory
        """
        if not project_id:
            # Fallback for workflows without project_id
            return "/tmp/stella_outputs"

        project_dir = f"/tmp/stella_projects/project_{project_id}"

        # Create directory if it doesn't exist
        os.makedirs(project_dir, exist_ok=True)

        return project_dir

    @staticmethod
    async def auto_register_workflow_files(
        workflow_id: str,
        workflow_tmp_dir: str,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> dict:
        """
        Automatically scan and register files created in workflow temp directory.

        This is a fallback mechanism for files that agent forgot to register.

        Args:
            workflow_id: Unique workflow identifier
            workflow_tmp_dir: Path to workflow's temporary directory
            user_id: User ID for file ownership
            project_id: Project ID for file association

        Returns:
            Dictionary with registration statistics:
            - new_files: List of newly registered files
            - skipped_files: List of already-registered files
            - failed_files: List of files that failed to register
        """
        if not os.path.exists(workflow_tmp_dir):
            print(f"📁 No files found in {workflow_tmp_dir}")
            return {"new_files": [], "skipped_files": [], "failed_files": []}

        try:
            from app.tools.core.files import save_agent_file_sync

            # Get list of files in directory
            files = []
            for root, dirs, filenames in os.walk(workflow_tmp_dir):
                for filename in filenames:
                    # Skip system files and Python cache
                    if filename.startswith('.') or filename.endswith('.pyc') or '__pycache__' in root:
                        continue

                    file_path = os.path.join(root, filename)
                    files.append(file_path)

            if not files:
                print(f"📁 No files to auto-register in {workflow_tmp_dir}")
                return {"new_files": [], "skipped_files": [], "failed_files": []}

            # Track registration results
            new_files = []
            skipped_files = []
            failed_files = []

            for file_path in files:
                # Calculate file hash
                try:
                    with open(file_path, 'rb') as f:
                        file_hash = hashlib.md5(f.read()).hexdigest()

                    # Try to register the file
                    # save_agent_file_sync will check if file already exists
                    result = save_agent_file_sync(
                        file_path=file_path,
                        category='agent_output',
                        description=f'Auto-saved: {os.path.basename(file_path)}',
                        user_id=user_id,
                        project_id=project_id
                    )

                    if result and 'file_id' in result:
                        new_files.append({
                            'filename': os.path.basename(file_path),
                            'file_id': result['file_id'],
                            'path': file_path
                        })
                        print(f"📁 Auto-registered file: {os.path.basename(file_path)} (ID: {result['file_id']})")
                    else:
                        skipped_files.append(os.path.basename(file_path))

                except Exception as e:
                    failed_files.append(os.path.basename(file_path))
                    print(f"⚠️ Failed to auto-register {os.path.basename(file_path)}: {e}")

            # Emit workflow event if we registered new files
            if new_files:
                # Check if any files are images and prepare visualization metadata
                visualizations = []
                for file_info in new_files:
                    filename = file_info['filename']
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp')):
                        visualizations.append({
                            "type": "image",
                            "chart_type": "generated",
                            "title": filename.replace('.png', '').replace('_', ' ').title(),
                            "file_id": file_info['file_id'],
                            "filename": filename
                        })
                        print(f"📊 Auto-registered visualization: {filename} (file_id: {file_info['file_id']})")

                # Prepare step metadata
                step_metadata = {'files': new_files}
                if visualizations:
                    step_metadata['visualizations'] = visualizations

                event = WorkflowEvent(
                    workflow_id=workflow_id,
                    event_type="observation",
                    timestamp=datetime.now(),
                    step_number=0,  # Will be handled by workflow service
                    title=f"📁 Auto-registered {len(new_files)} file(s)",
                    description=f"Files: {', '.join([f['filename'] for f in new_files])}",
                    step_metadata=step_metadata
                )
                workflow_event_queue.put(event)
                print(f"📁 Auto-registered {len(new_files)} files for workflow {workflow_id}")

            if skipped_files:
                print(f"✅ Skipped {len(skipped_files)} already-registered files")

            if failed_files:
                print(f"⚠️ Failed to register {len(failed_files)} files")

            return {
                "new_files": new_files,
                "skipped_files": skipped_files,
                "failed_files": failed_files
            }

        except Exception as e:
            print(f"❌ Error in auto-register workflow files: {e}")
            import traceback
            traceback.print_exc()
            return {"new_files": [], "skipped_files": [], "failed_files": []}

    @staticmethod
    def is_visualization_file(filename: str) -> bool:
        """
        Check if a file is a visualization (image file).

        Args:
            filename: Name of the file

        Returns:
            True if file is an image, False otherwise
        """
        return filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'))

    @staticmethod
    def cleanup_project_directory(project_id: str, keep_files: bool = True) -> bool:
        """
        Clean up project directory.

        Args:
            project_id: Project identifier
            keep_files: If True, keep files but clean cache/temp files only

        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            project_dir = WorkflowFileManager.get_project_output_dir(project_id)

            if not os.path.exists(project_dir):
                return True

            if keep_files:
                # Only remove cache/temp files
                for root, dirs, files in os.walk(project_dir):
                    for filename in files:
                        if filename.startswith('.') or filename.endswith('.pyc'):
                            file_path = os.path.join(root, filename)
                            try:
                                os.remove(file_path)
                                print(f"🧹 Removed temp file: {filename}")
                            except Exception as e:
                                print(f"⚠️ Failed to remove {filename}: {e}")

                    # Remove __pycache__ directories
                    if '__pycache__' in dirs:
                        cache_dir = os.path.join(root, '__pycache__')
                        try:
                            import shutil
                            shutil.rmtree(cache_dir)
                            print(f"🧹 Removed __pycache__ directory")
                        except Exception as e:
                            print(f"⚠️ Failed to remove __pycache__: {e}")
            else:
                # Remove entire directory
                import shutil
                shutil.rmtree(project_dir)
                print(f"🧹 Removed project directory: {project_dir}")

            return True

        except Exception as e:
            print(f"❌ Error cleaning up project directory: {e}")
            return False