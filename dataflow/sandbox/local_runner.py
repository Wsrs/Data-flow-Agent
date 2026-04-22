"""
LocalSandboxRunner
──────────────────
Runs generated cleaning scripts in an isolated subprocess on the host machine.
Intended for development / CI.  Production should use DockerSandboxRunner.

Path injection:
  The engineer agent always writes code that reads from  /data/input.<ext>
  and writes to /data/output.parquet.  Before execution this runner replaces
  those sentinel paths with the real host-system paths.
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
import time
from pathlib import Path

from dataflow.schemas.execution import ExecutionResult


# Sentinel paths used in generated code
_SENTINEL_OUTPUT = "/data/output.parquet"
_SENTINEL_INPUTS = [
    "/data/input.parquet",
    "/data/input.csv",
    "/data/input.json",
]

_PREAMBLE_TEMPLATE = """\
# ── DataFlow sandbox path injection ──────────────────────────────────────────
import sys as _sys, os as _os
_DATAFLOW_INPUT  = r"{input_path}"
_DATAFLOW_OUTPUT = r"{output_path}"
# ─────────────────────────────────────────────────────────────────────────────
"""


def _patch_code(code: str, input_path: str, output_path: str) -> str:
    """Replace sentinel paths and prepend variable definitions."""
    ext = Path(input_path).suffix  # e.g. ".parquet"
    patched = code

    # Replace quoted sentinel strings (both single and double quote variants)
    for sentinel in _SENTINEL_INPUTS:
        for q in ('"', "'"):
            patched = patched.replace(f"{q}{sentinel}{q}", "_DATAFLOW_INPUT")
    for q in ('"', "'"):
        patched = patched.replace(f"{q}{_SENTINEL_OUTPUT}{q}", "_DATAFLOW_OUTPUT")

    preamble = _PREAMBLE_TEMPLATE.format(
        input_path=input_path.replace("\\", "\\\\"),
        output_path=output_path.replace("\\", "\\\\"),
    )
    return preamble + patched


class LocalSandboxRunner:
    """Subprocess-based sandbox for local execution."""

    async def execute(
        self,
        code: str,
        input_path: str,
        output_path: str,
        timeout: int = 300,
        memory_limit_mb: int = 2048,  # informational only in local mode
    ) -> ExecutionResult:
        # ── Count rows before ─────────────────────────────────────────────────
        rows_before = self._count_rows(input_path)

        # ── Patch code ────────────────────────────────────────────────────────
        patched = _patch_code(code, input_path, output_path)

        # ── Write to temp file ────────────────────────────────────────────────
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(patched)
            script_path = f.name

        start = time.monotonic()
        success = False
        stderr_excerpt: str | None = None

        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                _stdout, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=float(timeout)
                )
                success = proc.returncode == 0
                if stderr_bytes:
                    stderr_excerpt = stderr_bytes.decode("utf-8", errors="replace")[:2000]
            except asyncio.TimeoutError:
                proc.kill()
                stderr_excerpt = f"Execution timed out after {timeout}s"
        except Exception as exc:  # noqa: BLE001
            stderr_excerpt = str(exc)
        finally:
            Path(script_path).unlink(missing_ok=True)

        elapsed = time.monotonic() - start

        # ── Count rows after & flagged records ────────────────────────────────
        rows_after = 0
        flagged_count = 0
        if success:
            rows_after, flagged_count = self._count_rows_and_flagged(output_path, rows_before)

        row_delta = (rows_after - rows_before) / max(rows_before, 1)

        return ExecutionResult(
            script_id="",  # caller fills this in
            success=success,
            rows_before=rows_before,
            rows_after=rows_after,
            row_delta_rate=row_delta,
            execution_time_seconds=round(elapsed, 3),
            stderr_excerpt=stderr_excerpt,
            flagged_record_count=flagged_count,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _count_rows(path: str) -> int:
        try:
            import polars as pl
            p = Path(path)
            if p.suffix == ".parquet":
                return pl.scan_parquet(path).select(pl.len()).collect().item()
            if p.suffix == ".csv":
                return pl.scan_csv(path).select(pl.len()).collect().item()
        except Exception:  # noqa: BLE001
            pass
        return 0

    @staticmethod
    def _count_rows_and_flagged(path: str, fallback: int) -> tuple[int, int]:
        try:
            import polars as pl
            df = pl.read_parquet(path)
            rows = df.height
            flagged = 0
            if "__flagged__" in df.columns:
                flagged = df.filter(pl.col("__flagged__") == True).height  # noqa: E712
            return rows, flagged
        except Exception:  # noqa: BLE001
            return fallback, 0
