class SupervisorError(Exception):
    """Base exception for all Supervisor errors."""
    pass


class AgentNotFoundError(SupervisorError):
    """Raised when an agent is not found in the supervisor registry."""
    pass


class AgentAlreadyExistsError(SupervisorError):
    """Raised when trying to attach an agent that is already registered."""
    pass


class ControllerNotFoundError(SupervisorError):
    """Raised when a requested controller is not found."""
    pass


class ControllerAlreadyExistsError(SupervisorError):
    """Raised when trying to register a controller with a duplicate ID."""
    pass


class ControlClaimError(SupervisorError):
    """Raised when a control claim is invalid or denied."""
    pass


class InvalidSupervisorStateError(SupervisorError):
    """Raised when an action is performed that is invalid in the current supervisor state."""
    pass


class InfrastructureError(SupervisorError):
    """Raised when an infrastructure failure occurs during workflow execution."""
    pass
