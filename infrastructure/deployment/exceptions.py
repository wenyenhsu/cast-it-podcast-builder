"""Deployment-related exceptions."""


class DeploymentError(Exception):
    """Base class for deployment failures."""


class DeploymentConfigurationError(DeploymentError):
    """Raised when environment configuration is invalid."""
