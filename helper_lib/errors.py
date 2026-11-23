"""Expected errors shared by pipeline components."""


class ComponentNotImplemented(NotImplementedError):
    """A teammate-owned component is still a placeholder."""


class ResourceUnavailable(RuntimeError):
    """A configured dataset, index, or local model is unavailable."""
