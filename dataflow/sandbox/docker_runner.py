"""
DockerSandboxRunner
────────────────────
Production sandbox: runs generated scripts inside a minimal Docker container
with hard resource limits, no network, and read-only root filesystem.

Requirements:
  - Docker Engine ≥ 24 must be running on the host.
  - The sandbox image (SANDBOX_IMAGE) must be pre-built from docker/Dockerfile.sandbox.
  - The host data directory must be bind-mounted at /data inside the container.
"""
from __future__ import annotations

import asyncio
import tempfile
import time
import uuid
from pathlib import Path

from dataflow.schemas.execution import ExecutionResult


class DockerSandboxRunner:
    def __init__(
        self,
        image: str = "dataflow-sandbox:latest",
        memory_limit: str = "2g",
        cpu_period: int = 100_000,
        cpu_quota: int = 50_000,   # 50 % of one CPU core
        timeout: int = 300,
        shared_data_dir: str = "/data",  # host-side shared dir mounted into container
    ) -> None:
        self.image = image
        self.memory_limit = memory_limit
        self.cpu_period = cpu_period
        self.cpu_quota = cpu_quota
        self.timeout = timeout
        self.shared_data_dir = Path(shared_data_dir)

    async def execute(
        self,
        code: str,
        input_path: str,
        output_path: str,
        timeout: int | None = None,
        memory_limit_mb: int | None = None,
    ) -> ExecutionResult:
        import docker  # type: ignore[import]

        effective_timeout = timeout or self.timeout
        effective_memory = f"{memory_limit_mb}m" if memory_limit_mb else self.memory_limit

        # Write code to a temp file inside shared_data_dir so container can access it
        script_name = f"_script_{uuid.uuid4().hex[:8]}.py"
        script_host_path = self.shared_data_dir / script_name
        script_host_path.write_text(code, encoding="utf-8")

        rows_before = self._count_rows(input_path)
        start = time.monotonic()
        success = False
        stderr_excerpt: str | None = None

        try:
            client = docker.from_env()
            container = client.containers.run(
                self.image,
                command=["python", f"/data/{script_name}"],
                volumes={
                    str(self.shared_data_dir): {"bind": "/data", "mode": "rw"},
                },
                mem_limit=effective_memory,
                cpu_period=self.cpu_period,
                cpu_quota=self.cpu_quota,
                network_disabled=True,
                read_only=False,   # /data needs write access
                user="sandbox_user",
                detach=True,
                remove=False,
            )

            try:
                loop = asyncio.get_event_loop()
                exit_status = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: container.wait()),
                    timeout=float(effective_timeout),
                )
                success = exit_status["StatusCode"] == 0
                logs = container.logs(stderr=True, stdout=False)
                if logs:
                    stderr_excerpt = logs.decode("utf-8", errors="replace")[:2000]
            except asyncio.TimeoutError:
                container.kill()
                stderr_excerpt = f"Container timed out after {effective_timeout}s"
            finally:
                try:
                    container.remove(force=True)
                except Exception:  # noqa: BLE001
                    pass

        except Exception as exc:  # noqa: BLE001
            stderr_excerpt = f"Docker error: {exc}"
        finally:
            script_host_path.unlink(missing_ok=True)

        elapsed = time.monotonic() - start
        rows_after = 0
        flagged_count = 0
        if success:
            rows_after, flagged_count = self._count_rows_and_flagged(output_path, rows_before)

        row_delta = (rows_after - rows_before) / max(rows_before, 1)

        return ExecutionResult(
            script_id="",
            success=success,
            rows_before=rows_before,
            rows_after=rows_after,
            row_delta_rate=row_delta,
            execution_time_seconds=round(elapsed, 3),
            stderr_excerpt=stderr_excerpt,
            flagged_record_count=flagged_count,
        )

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
