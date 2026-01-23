"""
Observer Agent Package

This package contains the Observer agent implementation for the VHL ANA-D control architecture.
The Observer agent is strictly observational and classifies validation results and design intent compliance.
"""

from ana.observer.observer_agent import ObserverAgent
from ana.observer.observer_system_prompt import ObserverMode, build_observer_system_prompt
from ana.observer.observer_tool import CommitObservationTool, create_commit_observation_tool

__all__ = [
    "ObserverAgent",
    "ObserverMode",
    "build_observer_system_prompt",
    "CommitObservationTool",
    "create_commit_observation_tool",
]
