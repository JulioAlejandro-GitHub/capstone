"""Typed errors raised by the strict model-governance repository."""


class ModelGovernanceError(RuntimeError):
    """Base error for model-governance operations."""


class GovernanceValidationError(ModelGovernanceError, ValueError):
    """A value violates the model-governance domain contract."""


class GovernanceNotFoundError(ModelGovernanceError, LookupError):
    """A required governed entity does not exist."""


class GovernanceConflictError(ModelGovernanceError):
    """A write conflicts with an existing row or database constraint."""


class GovernanceOwnershipError(GovernanceConflictError):
    """Related entities do not share the required owner or lineage."""


class GovernanceStateError(GovernanceConflictError):
    """An entity is not in a state that permits the requested operation."""


class GovernancePersistenceError(ModelGovernanceError):
    """The database operation failed without a more specific classification."""
