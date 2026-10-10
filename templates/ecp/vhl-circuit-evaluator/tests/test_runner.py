import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
from evaluator.models import EvaluationDecision, EvaluationStatus, ErrorCategory
from evaluator.runner import CircuitRunner


def test_runner_success(temp_circuit_dir):
    circuit_file = temp_circuit_dir / "test_module.tsx"

    mock_proc = MagicMock()
    mock_proc.communicate.return_value = (
        "Building 1 file(s)...\nCircuit JSON written to dist/test_module/circuit.json\nBuild complete\n",
        ""
    )
    mock_proc.returncode = 0
    mock_proc.pid = 12345

    runner = CircuitRunner(tsci_bin="/fake/tsci")
    with patch("subprocess.Popen", return_value=mock_proc):
        res = runner.evaluate(circuit_file, worktree_dir=temp_circuit_dir)

    assert res.decision == EvaluationDecision.ACCEPT
    assert res.status == EvaluationStatus.SUCCESS
    assert res.timed_out is False
    assert res.metadata["circuit_json_created"] is True
    assert (temp_circuit_dir / "eval_results" / "eval.log").is_file()


def test_runner_failure_with_diagnostics(temp_circuit_dir):
    circuit_file = temp_circuit_dir / "test_module.tsx"

    mock_proc = MagicMock()
    mock_proc.communicate.return_value = (
        "Building test_module.tsx...\nNo footprint specified for component: <chip name=\"U1\" />\nBuild completed with errors\n",
        ""
    )
    mock_proc.returncode = 1
    mock_proc.pid = 12346

    runner = CircuitRunner(tsci_bin="/fake/tsci")
    with patch("subprocess.Popen", return_value=mock_proc):
        res = runner.evaluate(circuit_file, worktree_dir=temp_circuit_dir)

    assert res.decision == EvaluationDecision.REJECT
    assert res.status == EvaluationStatus.ERROR
    assert len(res.diagnostics) >= 1
    assert any(d.category == ErrorCategory.FOOTPRINT_ERROR for d in res.diagnostics)


def test_runner_timeout_without_killing(temp_circuit_dir):
    circuit_file = temp_circuit_dir / "test_module.tsx"

    mock_proc = MagicMock()
    mock_proc.communicate.side_effect = subprocess.TimeoutExpired(
        cmd=["tsci"],
        timeout=0.2,
        output="Generating heavy netlist...\nStill routing...\n"
    )
    mock_proc.pid = 99999

    runner = CircuitRunner(tsci_bin="/fake/tsci")
    with patch("subprocess.Popen", return_value=mock_proc):
        res = runner.evaluate(circuit_file, worktree_dir=temp_circuit_dir, timeout_sec=0.2, kill_on_timeout=False)

    assert res.decision == EvaluationDecision.REJECT
    assert res.status == EvaluationStatus.RUNNING_TIMEOUT_WARNING
    assert res.timed_out is True
    assert res.pid == 99999
    # Verify process kill was NOT called (process is retained)
    mock_proc.kill.assert_not_called()


def test_runner_timeout_with_kill_flag(temp_circuit_dir):
    circuit_file = temp_circuit_dir / "test_module.tsx"

    mock_proc = MagicMock()
    mock_proc.communicate.side_effect = subprocess.TimeoutExpired(
        cmd=["tsci"],
        timeout=0.2,
        output="Compiling...\n"
    )
    mock_proc.pid = 99998
    mock_proc.returncode = -9

    runner = CircuitRunner(tsci_bin="/fake/tsci")
    with patch("subprocess.Popen", return_value=mock_proc):
        res = runner.evaluate(circuit_file, worktree_dir=temp_circuit_dir, timeout_sec=0.2, kill_on_timeout=True)

    assert res.timed_out is True
    mock_proc.kill.assert_called_once()
