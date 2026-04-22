import os

from dataflow.sandbox.local_runner import LocalSandboxRunner
from dataflow.sandbox.docker_runner import DockerSandboxRunner


def get_sandbox():
    """Return the appropriate sandbox runner based on SANDBOX_MODE env var."""
    mode = os.getenv("SANDBOX_MODE", "local").lower()
    if mode == "docker":
        return DockerSandboxRunner(
            image=os.getenv("SANDBOX_IMAGE", "dataflow-sandbox:latest"),
            memory_limit=f"{os.getenv('SANDBOX_MEMORY_MB', '2048')}m",
            timeout=int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "300")),
        )
    return LocalSandboxRunner()


__all__ = ["LocalSandboxRunner", "DockerSandboxRunner", "get_sandbox"]
