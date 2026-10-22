class DomainError(ValueError):
    """A business invariant was violated."""


class NotFound(DomainError):
    pass


class StateConflict(DomainError):
    pass
