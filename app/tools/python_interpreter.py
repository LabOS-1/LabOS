"""
Python execution tool for agents.

This module provides a production-ready tool function `python_interpreter` that executes
arbitrary Python code strings in a controlled environment, captures stdout/stderr,
and optionally returns the value of the last expression evaluated.

It is designed for data analysis, visualization (supports matplotlib with Agg backend),
and file manipulation tasks. The execution working directory is temporarily set to
`/tmp/` so any relative file writes go there by default.

Requirements satisfied:
- Decorated with @tool from smolagents
- Accepts a single string argument `code`
- Uses exec() in a controlled global namespace
- Captures stdout and stderr
- Handles exceptions with clear error messages
- Includes docstrings, type hints, and input validation
"""
from __future__ import annotations

import ast
import builtins
import contextlib
import io
import os
import sys
import traceback
from typing import Any, Dict, Optional

# Ensure matplotlib uses a headless backend if present
os.environ.setdefault("MPLBACKEND", "Agg")

try:
    # The decorator will be available at runtime in the agent environment
    from smolagents import tool
except Exception:  # pragma: no cover - fallback if smolagents is not present during static checks
    def tool(fn):  # type: ignore
        return fn


def _compile_with_last_expr_capture(code: str):
    """Compile code and capture last expression value into __result__ if present.

    If the last top-level statement is an expression, transforms it into an
    assignment to a special variable `__result__`, so we can return it.

    Args:
        code: The Python source code to compile.

    Returns:
        A compiled code object suitable for exec().
    """
    try:
        tree = ast.parse(code, mode="exec")
        if tree.body and isinstance(tree.body[-1], ast.Expr):
            last_expr = tree.body[-1].value
            assign = ast.Assign(targets=[ast.Name(id="__result__", ctx=ast.Store())], value=last_expr)
            tree.body[-1] = assign
            ast.fix_missing_locations(tree)
            return compile(tree, filename="<python_interpreter>", mode="exec")
        return compile(tree, filename="<python_interpreter>", mode="exec")
    except SyntaxError:
        # Fallback to direct compile to surface proper syntax error during exec
        return compile(code, filename="<python_interpreter>", mode="exec")


@tool
def python_interpreter(code: str) -> Dict[str, Any]:
    """Execute Python code and return captured outputs and result.

    The code runs with stdout and stderr redirected and working directory temporarily
    set to /tmp so that relative file writes save under that directory. If the code's
    last top-level statement is an expression, its value will be returned as `result`.
    Otherwise, if a variable named `__result__`, `result`, or `_result` is set in the
    executed environment, that value will be used as the result.

    This tool supports standard Python libraries and plotting with matplotlib using
    the Agg backend in headless environments.

    Args:
        code: Python source code to execute.

    Returns:
        A dictionary with the following keys:
        - ok (bool): True if execution succeeded, False otherwise.
        - stdout (str): Captured standard output.
        - stderr (str): Captured standard error.
        - result (Any, optional): Result value of the last expression or a named
          result variable if present.
        - error (str, optional): Error message when execution fails.
        - traceback (str, optional): Full traceback when execution fails.
    """
    # Input validation
    if not isinstance(code, str):
        return {
            "ok": False,
            "stdout": "",
            "stderr": "",
            "error": "Invalid input: 'code' must be a string",
        }
    if code.strip() == "":
        return {
            "ok": False,
            "stdout": "",
            "stderr": "",
            "error": "Invalid input: 'code' cannot be empty",
        }

    # Prepare execution environment
    glb: Dict[str, Any] = {
        "__name__": "__main__",
        "__builtins__": builtins,
        # Expose a minimal and useful environment; users can import as needed
        "os": os,
        "sys": sys,
    }

    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()

    prev_cwd = os.getcwd()
    # Ensure /tmp exists and chdir so relative writes go there
    tmp_dir = "/tmp"
    try:
        os.makedirs(tmp_dir, exist_ok=True)
    except Exception:
        # If creation somehow fails, continue without chdir
        tmp_dir = prev_cwd

    try:
        os.chdir(tmp_dir)
        compiled = _compile_with_last_expr_capture(code)
        with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
            exec(compiled, glb, glb)
        result: Any = None
        if "__result__" in glb:
            result = glb["__result__"]
        elif "result" in glb:
            result = glb["result"]
        elif "_result" in glb:
            result = glb["_result"]

        return {
            "ok": True,
            "stdout": stdout_buf.getvalue(),
            "stderr": stderr_buf.getvalue(),
            "result": result,
        }
    except Exception as exc:
        return {
            "ok": False,
            "stdout": stdout_buf.getvalue(),
            "stderr": stderr_buf.getvalue(),
            "error": f"{exc.__class__.__name__}: {exc}",
            "traceback": traceback.format_exc(),
        }
    finally:
        try:
            os.chdir(prev_cwd)
        except Exception:
            # If we can't change back, still return captured info
            pass