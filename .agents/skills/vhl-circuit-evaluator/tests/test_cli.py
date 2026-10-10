import json
from unittest.mock import patch, MagicMock
from evaluator.cli import main
from evaluator.models import EvaluationDecision, EvaluationResult, EvaluationStatus


def test_cli_evaluate_accept(temp_circuit_dir, capsys):
    mock_res = EvaluationResult(
        decision=EvaluationDecision.ACCEPT,
        status=EvaluationStatus.SUCCESS,
        circuit_file="test_module.tsx",
        elapsed_ms=500,
        exit_code=0,
        timed_out=False,
    )

    with patch("evaluator.runner.CircuitRunner.evaluate", return_value=mock_res):
        code = main(["evaluate", str(temp_circuit_dir / "test_module.tsx"), "--json"])

    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["decision"] == "ACCEPT"
    assert data["status"] == "Success"


def test_cli_evaluate_timeout_warning(temp_circuit_dir, capsys):
    mock_res = EvaluationResult(
        decision=EvaluationDecision.REJECT,
        status=EvaluationStatus.RUNNING_TIMEOUT_WARNING,
        circuit_file="test_module.tsx",
        elapsed_ms=60000,
        exit_code=None,
        timed_out=True,
        pid=5555,
    )

    with patch("evaluator.runner.CircuitRunner.evaluate", return_value=mock_res):
        code = main(["evaluate", str(temp_circuit_dir / "test_module.tsx"), "--json"])

    assert code == 3
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["status"] == "RUNNING_TIMEOUT_WARNING"
    assert data["pid"] == 5555


def test_cli_status(capsys):
    # Test checking status for PID 1 (init / launchd on unix is always alive)
    code = main(["status", "--pid", "1", "--json"])
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["is_alive"] is True
    assert data["pid"] == 1
