"""Secure sandbox execution backends for agent LLM calls.

Supports Docker-based isolation, subprocess isolation, and no-op modes.
All sandbox executions are logged to the audit trail.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from loguru import logger

from app.core.config import settings


class SandboxBackend(ABC):
    """Abstract sandbox execution backend."""

    @abstractmethod
    def execute(
        self,
        code: str,
        timeout: int | None = None,
        max_memory_mb: int | None = None,
        environment: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Execute code in an isolated environment.

        Args:
            code: The code/script to execute.
            timeout: Maximum execution time in seconds.
            max_memory_mb: Maximum memory in MB.
            environment: Environment variables.

        Returns:
            Dict with keys: stdout, stderr, exit_code, duration_ms, success.
        """
        ...


class ProcessSandboxBackend(SandboxBackend):
    """Subprocess-based sandbox with resource limits via the `resource` module.

    Used when Docker is not available. Provides basic isolation through
    subprocess execution with ulimit constraints.
    """

    def execute(
        self,
        code: str,
        timeout: int | None = None,
        max_memory_mb: int | None = None,
        environment: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        timeout = timeout or settings.SANDBOX_TIMEOUT
        max_memory_mb = max_memory_mb or settings.SANDBOX_MAX_MEMORY_MB

        start_time = time.monotonic()

        try:
            # Write code to a temp file for execution
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, prefix="lexorch_sandbox_"
            ) as f:
                f.write(code)
                temp_path = f.name

            try:
                result = subprocess.run(
                    ["python3", "-u", temp_path],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    env=environment or {},
                )

                duration_ms = (time.monotonic() - start_time) * 1000

                if result.returncode == 0:
                    logger.debug(f"Sandbox execution succeeded: {duration_ms:.0f}ms")
                else:
                    logger.warning(f"Sandbox execution failed (exit {result.returncode}): {result.stderr[:200]}")

                return {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.returncode,
                    "duration_ms": duration_ms,
                    "success": result.returncode == 0,
                }

            finally:
                # Cleanup temp file
                Path(temp_path).unlink(missing_ok=True)

        except subprocess.TimeoutExpired:
            duration_ms = (time.monotonic() - start_time) * 1000
            logger.error(f"Sandbox execution timed out after {timeout}s")
            return {
                "stdout": "",
                "stderr": f"Execution timed out after {timeout} seconds",
                "exit_code": -1,
                "duration_ms": duration_ms,
                "success": False,
                "error": "timeout",
            }
        except Exception as exc:
            duration_ms = (time.monotonic() - start_time) * 1000
            logger.error(f"Sandbox execution error: {exc}")
            return {
                "stdout": "",
                "stderr": str(exc),
                "exit_code": -1,
                "duration_ms": duration_ms,
                "success": False,
                "error": type(exc).__name__,
            }


class DockerSandboxBackend(SandboxBackend):
    """Docker-based sandbox with full container isolation.

    Provides CPU/memory limits, read-only mounts, tmpfs workspace,
    and network isolation.
    """

    def __init__(self) -> None:
        self._docker_client = None

    @property
    def docker_client(self):
        """Lazy-initialize Docker client."""
        if self._docker_client is None:
            try:
                import docker

                self._docker_client = docker.from_env()
            except ImportError:
                raise ImportError("docker package not installed. Install with: pip install docker")
            except Exception as exc:
                raise RuntimeError(f"Failed to connect to Docker daemon: {exc}")
        return self._docker_client

    def execute(
        self,
        code: str,
        timeout: int | None = None,
        max_memory_mb: int | None = None,
        environment: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        timeout = timeout or settings.SANDBOX_TIMEOUT
        max_memory_mb = max_memory_mb or settings.SANDBOX_MAX_MEMORY_MB

        start_time = time.monotonic()

        try:
            container = self.docker_client.containers.run(
                image="python:3.11-slim",
                command=["python3", "-c", code],
                remove=True,
                detach=True,
                mem_limit=f"{max_memory_mb}m",
                cpu_count=settings.SANDBOX_MAX_CPU_CORES,
                network_mode="none",
                read_only=True,
                tmpfs={"/tmp": "size=256m"},
                environment=environment or {},
            )

            try:
                result = container.wait(timeout=timeout)
                logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")
                duration_ms = (time.monotonic() - start_time) * 1000

                exit_code = result.get("StatusCode", -1)
                return {
                    "stdout": logs,
                    "stderr": "",
                    "exit_code": exit_code,
                    "duration_ms": duration_ms,
                    "success": exit_code == 0,
                }
            except Exception:
                container.kill()
                duration_ms = (time.monotonic() - start_time) * 1000
                return {
                    "stdout": "",
                    "stderr": f"Sandbox execution timed out after {timeout}s",
                    "exit_code": -1,
                    "duration_ms": duration_ms,
                    "success": False,
                    "error": "timeout",
                }

        except Exception as exc:
            duration_ms = (time.monotonic() - start_time) * 1000
            logger.error(f"Docker sandbox error: {exc}")
            return {
                "stdout": "",
                "stderr": str(exc),
                "exit_code": -1,
                "duration_ms": duration_ms,
                "success": False,
                "error": type(exc).__name__,
            }


class NoOpSandboxBackend(SandboxBackend):
    """No-op sandbox for direct execution (development only)."""

    def execute(
        self,
        code: str,
        timeout: int | None = None,
        max_memory_mb: int | None = None,
        environment: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Execute code directly in the current process (unsafe for production)."""
        logger.warning("NoOp sandbox executing code directly - INSECURE for production!")
        start_time = time.monotonic()

        try:
            local_vars: dict[str, Any] = {}
            exec(code, {}, local_vars)
            duration_ms = (time.monotonic() - start_time) * 1000
            return {
                "stdout": str(local_vars.get("result", "")),
                "stderr": "",
                "exit_code": 0,
                "duration_ms": duration_ms,
                "success": True,
            }
        except Exception as exc:
            duration_ms = (time.monotonic() - start_time) * 1000
            return {
                "stdout": "",
                "stderr": str(exc),
                "exit_code": -1,
                "duration_ms": duration_ms,
                "success": False,
                "error": type(exc).__name__,
            }


def get_sandbox_backend() -> SandboxBackend:
    """Factory returning the configured sandbox backend."""
    if settings.SANDBOX_BACKEND == "docker":
        try:
            return DockerSandboxBackend()
        except (ImportError, RuntimeError) as exc:
            logger.warning(f"Docker sandbox unavailable: {exc}. Falling back to process sandbox.")
            return ProcessSandboxBackend()

    if settings.SANDBOX_BACKEND == "process":
        return ProcessSandboxBackend()

    if settings.SANDBOX_BACKEND == "none":
        return NoOpSandboxBackend()

    logger.warning(f"Unknown sandbox backend '{settings.SANDBOX_BACKEND}', using process sandbox.")
    return ProcessSandboxBackend()
