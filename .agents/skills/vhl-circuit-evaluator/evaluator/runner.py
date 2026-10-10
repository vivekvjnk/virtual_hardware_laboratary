"""
Runner module: Spawns tsci build, monitors progress, handles configurable timeout
without unilateral termination, strips ANSI logs, and extracts structured diagnostics.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional

from .models import (
    DiagnosticError,
    EvaluationDecision,
    EvaluationResult,
    EvaluationStatus,
)
from .sanitizer import sanitize_lines
from .taxonomy import ErrorTaxonomy


def _find_tsci() -> str:
    path = shutil.which("tsci")
    if path:
        return path
    for candidate in [
        "/opt/homebrew/bin/tsci",
        "/usr/local/bin/tsci",
        "/usr/bin/tsci",
    ]:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return "tsci"


class CircuitRunner:
    """Executes tsci build and manages process observation."""

    def __init__(self, taxonomy: Optional[ErrorTaxonomy] = None, tsci_bin: Optional[str] = None):
        self.taxonomy = taxonomy or ErrorTaxonomy()
        self.tsci_bin = tsci_bin or _find_tsci()

    def evaluate(
        self,
        circuit_file: str | Path,
        worktree_dir: Optional[str | Path] = None,
        timeout_sec: float = 60.0,
        kill_on_timeout: bool = False,
    ) -> EvaluationResult:
        """
        Executes 'tsci build <circuit_file>' in worktree_dir.
        If timeout expires without kill_on_timeout, returns RUNNING_TIMEOUT_WARNING
        retaining the running process PID and partial output.
        """
        circuit_path = Path(circuit_file)
        cwd = Path(worktree_dir or os.getcwd()).resolve()

        # If circuit_file is relative, resolve against cwd
        target_circuit = circuit_path if circuit_path.is_absolute() else (cwd / circuit_path).resolve()
        circuit_filename = target_circuit.name
        exec_dir = target_circuit.parent if target_circuit.is_file() else cwd

        results_dir = exec_dir / "eval_results"
        results_dir.mkdir(parents=True, exist_ok=True)
        log_file_path = results_dir / "eval.log"

        cmd = [self.tsci_bin, "build", circuit_filename]
        start_time = time.time()

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(exec_dir),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env={
                    **os.environ,
                    "CI": "true",
                    "FORCE_COLOR": "0",
                    "PYTHONUNBUFFERED": "1",
                },
            )
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            return EvaluationResult(
                decision=EvaluationDecision.REJECT,
                status=EvaluationStatus.ERROR,
                circuit_file=str(target_circuit),
                elapsed_ms=elapsed_ms,
                exit_code=-1,
                timed_out=False,
                metadata={"error": f"Failed to spawn tsci: {e}"},
            )

        captured_output = ""
        is_timed_out = False

        try:
            stdout, _ = proc.communicate(timeout=timeout_sec)
            captured_output = stdout or ""
        except subprocess.TimeoutExpired as e:
            is_timed_out = True
            captured_output = e.stdout or e.output or ""
            if isinstance(captured_output, bytes):
                captured_output = captured_output.decode("utf-8", errors="replace")

            if kill_on_timeout:
                proc.kill()
                proc.wait()

        elapsed_ms = int((time.time() - start_time) * 1000)
        clean_logs = sanitize_lines(captured_output.splitlines())

        # Write sanitized log to eval_results/eval.log
        try:
            log_file_path.write_text("\n".join(clean_logs), encoding="utf-8")
        except Exception as ex:
            clean_logs.append(f"[evaluator] Failed to write log file: {ex}")

        # If timed out and process was not killed: return RUNNING_TIMEOUT_WARNING
        if is_timed_out and not kill_on_timeout:
            return EvaluationResult(
                decision=EvaluationDecision.REJECT,
                status=EvaluationStatus.RUNNING_TIMEOUT_WARNING,
                circuit_file=str(target_circuit),
                elapsed_ms=elapsed_ms,
                exit_code=None,
                timed_out=True,
                pid=proc.pid,
                partial_logs=clean_logs[-30:],
                log_file=str(log_file_path),
                metadata={
                    "warning": f"Process exceeded {timeout_sec}s timeout and is still running with PID {proc.pid}. You may extend wait or terminate."
                },
            )

        # Classify diagnostics
        diagnostics = self.taxonomy.classify_logs(clean_logs)

        # Build metadata
        has_circuit_json = any("Circuit JSON written to" in l or "circuit.json" in l for l in clean_logs)
        has_success_message = any("Build complete" in l or "1 passed" in l or "✓ Done" in l for l in clean_logs)
        has_build_error = any("Build failed with" in l or "Build completed with errors" in l for l in clean_logs) or (proc.returncode != 0)

        metadata: Dict[str, Any] = {
            "circuit_json_created": has_circuit_json,
            "success_message": has_success_message,
            "error_count": len(diagnostics),
            "command": " ".join(cmd),
            "cwd": str(exec_dir),
        }

        if proc.returncode == 0 and has_circuit_json and not has_build_error:
            decision = EvaluationDecision.ACCEPT
            status = EvaluationStatus.SUCCESS
        else:
            decision = EvaluationDecision.REJECT
            status = EvaluationStatus.ERROR

        return EvaluationResult(
            decision=decision,
            status=status,
            circuit_file=str(target_circuit),
            elapsed_ms=elapsed_ms,
            exit_code=proc.returncode,
            timed_out=is_timed_out,
            diagnostics=diagnostics,
            metadata=metadata,
            log_file=str(log_file_path),
            partial_logs=clean_logs[-25:],
            pid=proc.pid,
        )
