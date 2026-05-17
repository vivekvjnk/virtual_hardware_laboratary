import pytest

from fixtures.replay_snapshot_test_llm.replay_callback import ObservationDriftCallback
from fixtures.replay_snapshot_test_llm.replay_llm import ReplayLLM
from fixtures.replay_snapshot_test_llm.snapshot import SnapshotLoader


@pytest.fixture
def snapshot_loader():
    """Fixture that returns the SnapshotLoader class."""
    return SnapshotLoader


@pytest.fixture
def replay_llm():
    """Fixture that returns the ReplayLLM class."""
    return ReplayLLM


@pytest.fixture
def observation_drift_callback():
    """Fixture that returns the ObservationDriftCallback class."""
    return ObservationDriftCallback
