"""
Enhanced Logging Configuration
- Captures all stdout/stderr to daily log files
- Creates per-workflow log files for detailed tracking
- Can be disabled in production via environment variable
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from app.config import DATA_DIR

# Environment-based logging control
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
ENABLE_FILE_LOGGING = os.getenv('ENABLE_FILE_LOGGING', 'true' if ENVIRONMENT != 'production' else 'false').lower() == 'true'

# Workflow log tracking
_workflow_log_files = {}


class OutputCapture:
    """Capture stdout/stderr to file while maintaining terminal output"""
    def __init__(self, log_file, terminal_stream):
        self.log_file = log_file
        self.terminal = terminal_stream

    def write(self, message):
        # Write to terminal
        self.terminal.write(message)
        self.terminal.flush()

        # Write to log file (only if enabled)
        if ENABLE_FILE_LOGGING:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(message)

    def flush(self):
        self.terminal.flush()

    def fileno(self):
        """Return the file descriptor of the underlying terminal"""
        return self.terminal.fileno()

    def isatty(self):
        """Check if the terminal is a TTY"""
        return self.terminal.isatty() if hasattr(self.terminal, 'isatty') else False


class WorkflowLogger:
    """Logger for individual workflow execution tracking"""

    def __init__(self, workflow_id: str, project_id: str = None):
        self.workflow_id = workflow_id
        self.project_id = project_id
        self.log_file = None

        if ENABLE_FILE_LOGGING:
            # Create workflow logs directory
            workflow_log_dir = DATA_DIR / "logs" / "workflows"
            workflow_log_dir.mkdir(parents=True, exist_ok=True)

            # Create log file for this workflow
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_workflow_id = workflow_id.replace('/', '_').replace('\\', '_')[:100]
            self.log_file = workflow_log_dir / f"{timestamp}_{safe_workflow_id}.log"

            # Write header
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write(f"{'='*80}\n")
                f.write(f"WORKFLOW LOG\n")
                f.write(f"{'='*80}\n")
                f.write(f"Workflow ID: {workflow_id}\n")
                if project_id:
                    f.write(f"Project ID:  {project_id}\n")
                f.write(f"Started:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'='*80}\n\n")

            # Track this workflow log
            _workflow_log_files[workflow_id] = self.log_file

            print(f"📝 Created workflow log: {self.log_file}")

    def log(self, message: str, level: str = "INFO"):
        """Log a message to workflow file"""
        if not ENABLE_FILE_LOGGING or not self.log_file:
            return

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        log_line = f"[{timestamp}] [{level:5s}] {message}\n"

        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_line)

    def log_step(self, step_number: int, step_type: str, title: str, description: str = None):
        """Log a workflow step"""
        if not ENABLE_FILE_LOGGING or not self.log_file:
            return

        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'─'*80}\n")
            f.write(f"STEP {step_number}: {step_type}\n")
            f.write(f"{'─'*80}\n")
            f.write(f"Title: {title}\n")
            if description:
                f.write(f"Description: {description}\n")
            f.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'─'*80}\n\n")

    def log_completion(self, status: str = "SUCCESS", duration: float = None):
        """Log workflow completion"""
        if not ENABLE_FILE_LOGGING or not self.log_file:
            return

        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"WORKFLOW COMPLETED\n")
            f.write(f"{'='*80}\n")
            f.write(f"Status:   {status}\n")
            if duration:
                f.write(f"Duration: {duration:.2f} seconds\n")
            f.write(f"Ended:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*80}\n")

        # Clean up tracking
        if self.workflow_id in _workflow_log_files:
            del _workflow_log_files[self.workflow_id]


def setup_logging():
    """Setup enhanced logging with environment control"""

    if not ENABLE_FILE_LOGGING:
        print(f"ℹ️  File logging disabled (environment: {ENVIRONMENT})")
        return None

    # Create logs directory
    log_dir = DATA_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create daily log file
    today = datetime.now().strftime("%Y%m%d")
    log_file = log_dir / f"all_output_{today}.log"

    # Save original streams
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    # Redirect both stdout and stderr to capture
    sys.stdout = OutputCapture(log_file, original_stdout)
    sys.stderr = OutputCapture(log_file, original_stderr)

    print(f"📝 File logging enabled")
    print(f"   Environment: {ENVIRONMENT}")
    print(f"   Daily log: {log_file}")
    print(f"   Workflow logs: {log_dir / 'workflows'}")

    return None


def get_workflow_logger(workflow_id: str, project_id: str = None) -> WorkflowLogger:
    """Get a logger for a specific workflow"""
    return WorkflowLogger(workflow_id, project_id)


def get_workflow_log_path(workflow_id: str) -> Path:
    """Get the log file path for a workflow (if it exists)"""
    return _workflow_log_files.get(workflow_id)