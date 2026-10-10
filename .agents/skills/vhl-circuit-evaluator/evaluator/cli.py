"""
CLI interface for vhl-circuit-evaluator.
Commands: evaluate, status.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .models import EvaluationDecision, EvaluationStatus
from .runner import CircuitRunner


def cmd_evaluate(args) -> int:
    runner = CircuitRunner()
    result = runner.evaluate(
        circuit_file=args.circuit_path,
        worktree_dir=args.worktree,
        timeout_sec=args.timeout,
        kill_on_timeout=args.kill_on_timeout,
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print("==================================================")
        print("          VHL CIRCUIT EVALUATION REPORT           ")
        print("==================================================")
        print(f"Target:       {result.circuit_file}")
        print(f"Decision:     {result.decision.value}")
        print(f"Status:       {result.status.value}")
        print(f"Elapsed Time: {result.elapsed_ms}ms")
        print(f"Timed Out:    {'YES' if result.timed_out else 'NO'}")
        if result.pid:
            print(f"PID:          {result.pid}")
        if result.log_file:
            print(f"Log File:     {result.log_file}")

        if result.status == EvaluationStatus.RUNNING_TIMEOUT_WARNING:
            print("\n⚠ WARNING: The build exceeded the timeout and is still running in background.")
            print(f"PID: {result.pid}. You can wait or terminate using 'kill {result.pid}'.")

        if result.diagnostics:
            print("\n---------------- Diagnostic Errors ----------------")
            for idx, diag in enumerate(result.diagnostics, start=1):
                loc = f" ({diag.file_path}:{diag.line_number})" if diag.file_path else ""
                print(f"{idx}. [{diag.category.value}]{loc}")
                print(f"   {diag.message}")

        if result.partial_logs:
            print("\n---------------- Log Highlights -------------------")
            for line in result.partial_logs[-15:]:
                print(f"  {line}")
        print("==================================================")

    if result.decision == EvaluationDecision.ACCEPT:
        return 0
    elif result.status == EvaluationStatus.RUNNING_TIMEOUT_WARNING:
        return 3
    else:
        return 1


def is_process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except (ProcessLookupError, OSError):
        return False


def cmd_status(args) -> int:
    pid = args.pid
    log_file = Path(args.log_file).resolve() if args.log_file else None

    is_alive = is_process_alive(int(pid)) if pid else False

    tail_lines = []
    if log_file and log_file.is_file():
        try:
            lines = log_file.read_text(encoding="utf-8").splitlines()
            tail_lines = lines[-20:]
        except Exception:
            pass

    status_data = {
        "pid": pid,
        "is_alive": is_alive,
        "log_file": str(log_file) if log_file else None,
        "recent_logs": tail_lines,
    }

    if args.json:
        print(json.dumps(status_data, indent=2))
    else:
        print(f"Process PID {pid}: {'RUNNING' if is_alive else 'TERMINATED'}")
        if tail_lines:
            print("\nTrailing log lines:")
            for l in tail_lines[-10:]:
                print(f"  {l}")

    return 0 if is_alive else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="circuit_evaluator",
        description="VHL Circuit Evaluator: Synchronous tscircuit compiler & DRC evaluation engine with non-terminating timeout warning.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # --- evaluate ---
    p_eval = subparsers.add_parser("evaluate", help="Evaluate a circuit TSX file using tsci build")
    p_eval.add_argument("circuit_path", help="Path to circuit file (e.g. module.tsx or index.circuit.tsx)")
    p_eval.add_argument("--timeout", "-t", type=float, default=60.0, help="Execution timeout in seconds (default: 60s)")
    p_eval.add_argument("--kill-on-timeout", action="store_true", default=False, help="Explicitly terminate process if timeout expires")
    p_eval.add_argument("--worktree", "-w", default=None, help="Working directory for build execution")
    p_eval.add_argument("--json", action="store_true", default=False, help="Output structured JSON")
    p_eval.set_defaults(func=cmd_evaluate)

    # --- status ---
    p_stat = subparsers.add_parser("status", help="Inspect status of an asynchronous or timeout-warning build PID")
    p_stat.add_argument("--pid", type=int, default=None, help="Process ID to inspect")
    p_stat.add_argument("--log-file", default=None, help="Path to eval.log")
    p_stat.add_argument("--json", action="store_true", default=False, help="Output structured JSON")
    p_stat.set_defaults(func=cmd_status)

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
