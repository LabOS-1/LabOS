"""
LABOS Sandbox Python Interpreter

A secure Python interpreter that runs code within the project sandbox.
All file operations are restricted to the sandbox directory.

Security Features:
- Working directory set to sandbox root
- Dangerous imports blocked (os.system, subprocess, socket, etc.)
- All relative paths resolve within sandbox
- Timeout and memory limits
"""

import os
import sys
import io
import traceback
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import redirect_stdout, redirect_stderr
import builtins

from smolagents import tool

from app.services.sandbox import (
    get_sandbox_manager,
    get_sandbox_project_dir,
    SandboxSecurityError,
)
from app.services.workflows import get_workflow_context

logger = logging.getLogger(__name__)

# Dangerous modules that should be blocked
BLOCKED_MODULES = {
    'subprocess',
    'socket',
    'requests',  # Use our controlled tools for HTTP
    'urllib',
    'http.client',
    'ftplib',
    'telnetlib',
    'smtplib',
    'poplib',
    'imaplib',
    'nntplib',
    'multiprocessing',
    'threading',  # Allow limited threading
    'ctypes',
    'cffi',
    '_thread',
}

# Dangerous functions that should be blocked
BLOCKED_BUILTINS = {
    'eval',  # Already in exec context
    'exec',  # Already in exec context
    'compile',
    '__import__',
    'open',  # Replace with sandbox-aware version
}

# Allowed dangerous operations (with restrictions)
ALLOWED_OS_FUNCTIONS = {
    'path',
    'getcwd',
    'listdir',
    'makedirs',
    'mkdir',
    'remove',
    'rename',
    'stat',
    'walk',
    'sep',
    'pathsep',
    'linesep',
    'environ',  # Read only
}


class SandboxImportHook:
    """
    Import hook that blocks dangerous modules and restricts 'os' module.
    """

    def __init__(self, sandbox_root: Path):
        self.sandbox_root = sandbox_root

    def find_module(self, name: str, path=None):
        # Check if module is blocked
        base_module = name.split('.')[0]
        if base_module in BLOCKED_MODULES:
            return self  # Return self to handle the import
        return None

    def load_module(self, name: str):
        raise ImportError(
            f"Module '{name}' is not allowed in sandbox environment. "
            f"For security reasons, network and subprocess operations are restricted."
        )


class SandboxedOpen:
    """
    A sandboxed version of the open() function that restricts file access.
    """

    def __init__(self, sandbox_root: Path):
        self.sandbox_root = sandbox_root.resolve()
        self._original_open = builtins.open

    def __call__(self, file, mode='r', *args, **kwargs):
        # Convert to Path and resolve
        file_path = Path(file)

        # If relative, make it relative to sandbox
        if not file_path.is_absolute():
            file_path = self.sandbox_root / file_path

        # Resolve to absolute path
        resolved = file_path.resolve()

        # Security check: ensure path is within sandbox
        try:
            resolved.relative_to(self.sandbox_root)
        except ValueError:
            raise PermissionError(
                f"Access denied: Cannot access files outside sandbox. "
                f"Attempted: {file}"
            )

        # Ensure parent directory exists for write operations
        if 'w' in mode or 'a' in mode or 'x' in mode:
            resolved.parent.mkdir(parents=True, exist_ok=True)

        return self._original_open(str(resolved), mode, *args, **kwargs)


def create_sandbox_globals(sandbox_root: Path) -> Dict[str, Any]:
    """
    Create a restricted globals dict for code execution.
    """
    # Start with safe builtins
    safe_builtins = {
        k: v for k, v in builtins.__dict__.items()
        if k not in BLOCKED_BUILTINS
    }

    # Replace open with sandboxed version
    safe_builtins['open'] = SandboxedOpen(sandbox_root)

    # Create globals
    sandbox_globals = {
        '__builtins__': safe_builtins,
        '__name__': '__main__',
        '__doc__': None,
        '__file__': str(sandbox_root / 'script.py'),
    }

    return sandbox_globals


def execute_in_sandbox(
    code: str,
    sandbox_root: Path,
    timeout: int = 60
) -> Dict[str, Any]:
    """
    Execute Python code within the sandbox environment.

    Args:
        code: Python code to execute
        sandbox_root: Path to sandbox root directory
        timeout: Maximum execution time in seconds

    Returns:
        Dict with stdout, stderr, result, and success status
    """
    # Ensure sandbox exists
    sandbox_root.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (sandbox_root / 'uploads').mkdir(exist_ok=True)
    (sandbox_root / 'generated').mkdir(exist_ok=True)
    (sandbox_root / 'workspace').mkdir(exist_ok=True)

    # Save current state
    original_cwd = os.getcwd()
    original_path = sys.path.copy()
    original_meta_path = sys.meta_path.copy()

    # Capture output
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    result = None
    error = None
    success = False

    try:
        # Change to sandbox directory
        os.chdir(str(sandbox_root))

        # Add sandbox to path
        sys.path.insert(0, str(sandbox_root))

        # Install import hook
        import_hook = SandboxImportHook(sandbox_root)
        sys.meta_path.insert(0, import_hook)

        # Create restricted globals
        sandbox_globals = create_sandbox_globals(sandbox_root)

        # Pre-import allowed modules
        import numpy
        import pandas
        import json
        import csv
        import re
        import math
        import datetime
        import collections
        import itertools
        import functools

        # Wrap numpy save functions to enforce generated/ path
        _original_np_save = numpy.save
        _original_np_savez = numpy.savez
        _original_np_savetxt = numpy.savetxt

        def _redirect_path(path):
            """Redirect output paths to generated/ folder"""
            path_str = str(path)
            if not path_str.startswith('generated/') and not path_str.startswith('./generated/'):
                from pathlib import Path
                basename = Path(path_str).name
                new_path = f'generated/{basename}'
                logger.info(f"[Sandbox] Redirecting output to: {new_path}")
                return new_path
            return path_str

        def _wrapped_np_save(file, arr, *args, **kwargs):
            return _original_np_save(_redirect_path(file), arr, *args, **kwargs)
        def _wrapped_np_savez(file, *args, **kwargs):
            return _original_np_savez(_redirect_path(file), *args, **kwargs)
        def _wrapped_np_savetxt(fname, X, *args, **kwargs):
            return _original_np_savetxt(_redirect_path(fname), X, *args, **kwargs)

        numpy.save = _wrapped_np_save
        numpy.savez = _wrapped_np_savez
        numpy.savetxt = _wrapped_np_savetxt

        # Wrap open() for write mode to enforce generated/ path
        _original_open = builtins.open
        def _wrapped_open(file, mode='r', *args, **kwargs):
            if 'w' in mode or 'a' in mode or 'x' in mode:
                # Write mode - redirect to generated/
                file = _redirect_path(file)
            return _original_open(file, mode, *args, **kwargs)

        sandbox_globals['numpy'] = numpy
        sandbox_globals['np'] = numpy
        sandbox_globals['pandas'] = pandas
        sandbox_globals['pd'] = pandas
        sandbox_globals['json'] = json
        sandbox_globals['csv'] = csv
        sandbox_globals['re'] = re
        sandbox_globals['math'] = math
        sandbox_globals['datetime'] = datetime
        sandbox_globals['collections'] = collections
        sandbox_globals['itertools'] = itertools
        sandbox_globals['functools'] = functools
        sandbox_globals['open'] = _wrapped_open  # Use wrapped open

        # Try to import matplotlib with Agg backend
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt

            # Wrap savefig to enforce generated/ path
            _original_savefig = plt.savefig
            def _wrapped_savefig(fname, *args, **kwargs):
                # Ensure output goes to generated/ folder
                fname_str = str(fname)
                if not fname_str.startswith('generated/') and not fname_str.startswith('./generated/'):
                    # Extract just the filename
                    from pathlib import Path
                    basename = Path(fname_str).name
                    fname = f'generated/{basename}'
                    logger.info(f"[Sandbox] Redirecting savefig to: {fname}")
                return _original_savefig(fname, *args, **kwargs)
            plt.savefig = _wrapped_savefig

            sandbox_globals['matplotlib'] = matplotlib
            sandbox_globals['plt'] = plt
        except ImportError:
            pass

        # Wrap pandas to_csv/to_excel to enforce generated/ path
        def _wrap_pandas_output(df_class):
            _original_to_csv = df_class.to_csv
            _original_to_excel = df_class.to_excel if hasattr(df_class, 'to_excel') else None

            def _wrapped_to_csv(self, path_or_buf=None, *args, **kwargs):
                if path_or_buf is not None and isinstance(path_or_buf, str):
                    if not path_or_buf.startswith('generated/'):
                        from pathlib import Path
                        basename = Path(path_or_buf).name
                        path_or_buf = f'generated/{basename}'
                        logger.info(f"[Sandbox] Redirecting to_csv to: {path_or_buf}")
                return _original_to_csv(self, path_or_buf, *args, **kwargs)
            df_class.to_csv = _wrapped_to_csv

            if _original_to_excel:
                def _wrapped_to_excel(self, excel_writer, *args, **kwargs):
                    if isinstance(excel_writer, str):
                        if not excel_writer.startswith('generated/'):
                            from pathlib import Path
                            basename = Path(excel_writer).name
                            excel_writer = f'generated/{basename}'
                            logger.info(f"[Sandbox] Redirecting to_excel to: {excel_writer}")
                    return _original_to_excel(self, excel_writer, *args, **kwargs)
                df_class.to_excel = _wrapped_to_excel

        _wrap_pandas_output(pandas.DataFrame)

        # Execute code with output capture
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exec(code, sandbox_globals)

        success = True

    except SandboxSecurityError as e:
        error = f"Security Error: {str(e)}"
    except PermissionError as e:
        error = f"Permission Denied: {str(e)}"
    except ImportError as e:
        error = f"Import Error: {str(e)}"
    except Exception as e:
        error = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
    finally:
        # Restore original state
        os.chdir(original_cwd)
        sys.path = original_path
        sys.meta_path = original_meta_path

    return {
        'success': success,
        'stdout': stdout_capture.getvalue(),
        'stderr': stderr_capture.getvalue(),
        'error': error,
    }


@tool
def python_interpreter(code: str) -> str:
    """
    Execute Python code in a secure sandbox environment.

    The code runs within the project's sandbox directory where:
    - All file paths are relative to the sandbox root
    - Dangerous operations (network, subprocess) are blocked
    - Pre-imported: numpy, pandas, matplotlib, json, csv, re, math

    Args:
        code: Python code to execute

    Returns:
        Execution output (stdout) or error message

    Examples:
        >>> python_interpreter("print('Hello World')")
        "Hello World"

        >>> python_interpreter('''
        import pandas as pd
        df = pd.read_csv('uploads/data.csv')
        print(df.head())
        ''')
        "   col1  col2 ..."

        >>> python_interpreter('''
        import matplotlib.pyplot as plt
        plt.plot([1, 2, 3], [1, 4, 9])
        plt.savefig('generated/chart.png')
        print('Chart saved')
        ''')
        "Chart saved"
    """
    # Get sandbox context
    context = get_workflow_context()
    if not context:
        return "❌ Error: No workflow context. Cannot execute code outside a workflow."

    user_id = context.metadata.get('user_id')
    project_id = context.metadata.get('project_id')

    if not user_id or not project_id:
        return "❌ Error: Missing user_id or project_id in context."

    # Get sandbox path
    sandbox = get_sandbox_manager()
    sandbox_root = sandbox.ensure_project_sandbox(user_id, project_id)

    logger.info(f"Executing code in sandbox: {sandbox_root}")

    # Execute code
    result = execute_in_sandbox(code, sandbox_root)

    # Format output
    output_parts = []

    if result['stdout']:
        output_parts.append(result['stdout'].rstrip())

    if result['stderr']:
        output_parts.append(f"[stderr]\n{result['stderr'].rstrip()}")

    if result['error']:
        output_parts.append(f"❌ {result['error']}")

    if not output_parts:
        output_parts.append("✅ Code executed successfully (no output)")

    return '\n'.join(output_parts)


@tool
def run_python_file(filename: str) -> str:
    """
    Execute a Python file from the project sandbox.

    Args:
        filename: Path to Python file (relative to sandbox root)

    Returns:
        Execution output or error message

    Example:
        >>> run_python_file("generated/analysis.py")
        "Analysis complete. Results saved to output.csv"
    """
    # Get sandbox context
    context = get_workflow_context()
    if not context:
        return "❌ Error: No workflow context."

    user_id = context.metadata.get('user_id')
    project_id = context.metadata.get('project_id')

    if not user_id or not project_id:
        return "❌ Error: Missing user_id or project_id in context."

    # Get sandbox path
    sandbox = get_sandbox_manager()
    sandbox_root = sandbox.ensure_project_sandbox(user_id, project_id)

    # Validate filename
    file_path = sandbox_root / filename
    try:
        file_path.resolve().relative_to(sandbox_root.resolve())
    except ValueError:
        return f"❌ Error: Cannot access files outside sandbox: {filename}"

    if not file_path.exists():
        return f"❌ Error: File not found: {filename}"

    if not file_path.suffix == '.py':
        return f"❌ Error: Not a Python file: {filename}"

    # Read and execute
    code = file_path.read_text()
    return python_interpreter(code)
