"""
Google Cloud Logging integration - Captures ALL logs including smolagents
"""

import logging
import sys
import os
from typing import Optional, Dict, Any
from contextvars import ContextVar

# Context variable for tracking user/workflow info
log_context: ContextVar[Dict[str, Any]] = ContextVar('log_context', default={})


def set_log_context(
    user_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    project_id: Optional[str] = None,
    **kwargs
):
    """
    Set logging context - all subsequent logs will include this info

    Usage:
        set_log_context(user_id="user_123", workflow_id="wf_456")
    """
    context = {
        "user_id": user_id,
        "workflow_id": workflow_id,
        "project_id": project_id,
    }
    context.update(kwargs)
    log_context.set(context)


def clear_log_context():
    """Clear logging context"""
    log_context.set({})


class ContextFilter(logging.Filter):
    """
    Add context info to all log records
    This ensures ALL logs (including smolagents) have user_id, workflow_id, etc.
    """

    def filter(self, record):
        context = log_context.get({})

        # Add context to log record
        record.user_id = context.get("user_id", "")
        record.workflow_id = context.get("workflow_id", "")
        record.project_id = context.get("project_id", "")

        return True


def setup_cloud_logging():
    """
    Setup Cloud Run compatible logging (JSON to stdout)

    Features:
    1. Outputs structured JSON logs that Cloud Run automatically captures
    2. Captures logs from all libraries (including smolagents)
    3. Automatically adds user_id, workflow_id labels
    """

    environment = os.getenv("ENVIRONMENT", "development")

    if environment == "production":
        # Production: Output JSON to stdout (Cloud Run auto-captures to Cloud Logging)
        setup_json_logging()
    else:
        # Development: Use human-readable console logging
        setup_console_logging()


class JsonFormatter(logging.Formatter):
    """
    Format logs as JSON for Cloud Run
    Cloud Run automatically sends stdout JSON to Cloud Logging
    """

    def format(self, record):
        import json
        from datetime import datetime

        # Build log entry compatible with Cloud Logging
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "severity": record.levelname,
            "message": record.getMessage(),
            "logging.googleapis.com/sourceLocation": {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            },
        }

        # Add labels for filtering
        labels = {}
        if hasattr(record, 'user_id') and record.user_id:
            labels["user_id"] = str(record.user_id)
        if hasattr(record, 'workflow_id') and record.workflow_id:
            labels["workflow_id"] = str(record.workflow_id)
        if hasattr(record, 'project_id') and record.project_id:
            labels["project_id"] = str(record.project_id)

        if labels:
            log_entry["logging.googleapis.com/labels"] = labels

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add logger name
        log_entry["logger"] = record.name

        return json.dumps(log_entry)


def setup_json_logging():
    """Setup JSON logging for production (Cloud Run)"""

    # Create JSON formatter
    json_formatter = JsonFormatter()

    # Create stdout handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(json_formatter)

    # Add context filter
    context_filter = ContextFilter()
    handler.addFilter(context_filter)

    # Configure root logger (captures all library logs)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove existing handlers
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    root_logger.addHandler(handler)

    # Configure smolagents logger
    smolagents_logger = logging.getLogger('smolagents')
    smolagents_logger.setLevel(logging.INFO)

    print("✅ JSON logging initialized for Cloud Run (with smolagents capture)")


def setup_console_logging():
    """Console logging for development environment"""

    # Create formatter
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [user=%(user_id)s] [wf=%(workflow_id)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Add context filter
    context_filter = ContextFilter()
    console_handler.addFilter(context_filter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    root_logger.addHandler(console_handler)

    # Configure smolagents logger
    smolagents_logger = logging.getLogger('smolagents')
    smolagents_logger.setLevel(logging.INFO)

    print("✅ Console logging initialized (with smolagents capture)")


def get_logger(name: str) -> logging.Logger:
    """
    Get logger with context

    Usage:
        logger = get_logger(__name__)
        logger.info("Processing message")  # auto includes user_id, workflow_id
    """
    return logging.getLogger(f"stella.{name}")
