import pytest

from vhl_common.llm.replay_callback import ObservationDriftCallback
from vhl_common.llm.replay_llm import ReplayLLM
from vhl_common.llm.snapshot import SnapshotLoader


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
