"""Script generation exceptions."""


class ScriptGenerationError(Exception):
    """Base exception for script generation operations."""


class ScriptValidationError(ScriptGenerationError):
    """Raised when script validation fails."""


class ScriptSchemaError(ScriptGenerationError):
    """Raised when script JSON schema parsing fails."""


class ScriptEmptyError(ScriptGenerationError):
    """Raised when generated script content is empty."""


class ScriptVersionConflictError(ScriptGenerationError):
    """Raised when script version creation conflicts with existing data."""
