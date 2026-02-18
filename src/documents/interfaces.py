"""
Abstract interfaces for third-party integration providers.

This module defines the base interface that all integration providers must implement,
following the Open/Closed Principle for extensibility.
"""

from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class IntegrationStatus(str, Enum):
    """Standard status codes for integration operations."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    SIGNED = "signed"
    ARCHIVED = "archived"
    FAILED = "failed"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class PushResult:
    """Result of pushing a document to a provider."""

    success: bool
    remote_id: str | None = None
    remote_url: str | None = None
    status: IntegrationStatus = IntegrationStatus.PENDING
    message: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class StatusResult:
    """Result of checking status on a provider."""

    status: IntegrationStatus
    updated_at: datetime
    message: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class ProviderCapabilities:
    """Describes optional capabilities of an integration provider."""

    produces_remote_document: bool = True
    supports_status_tracking: bool = True
    supports_remote_url: bool = True
    supports_delete: bool = False
    supports_metadata_only_push: bool = False
    required_push_params: tuple[str, ...] = ()
    optional_push_params: tuple[str, ...] = ()


class BaseIntegrationProvider(ABC):
    """
    Abstract base class for all integration providers.

    All providers must implement these methods to ensure consistent behavior
    across different platforms (DocuSeal, Documenso, Digiposte, etc.).

    Attributes:
        integration: The Integration model instance containing configuration
    """

    def __init__(self, integration: Any):
        """
        Initialize the provider with an integration configuration.

        Args:
            integration: Integration model instance with api_url, credentials, etc.
        """
        self.integration = integration
        self.api_url = integration.api_url
        self.credentials = integration.credentials or {}

    @abstractmethod
    def push_document(
        self,
        document_id: int,
        params: dict[str, Any] | None = None,
    ) -> PushResult:
        """
        Push a document to the external platform.

        Args:
            document_id: ID of the Paperless document to push
            params: Optional provider-specific parameters
                    (e.g., recipients for signature, folder for storage)

        Returns:
            PushResult with remote_id, remote_url, and initial status

        Raises:
            ConnectionError: If unable to connect to the provider API
            ValueError: If document or parameters are invalid
            Exception: For other provider-specific errors
        """

    @abstractmethod
    def get_status(self, remote_id: str) -> StatusResult:
        """
        Get the current status of a document on the external platform.

        Args:
            remote_id: The remote identifier returned by push_document()

        Returns:
            StatusResult with current status and timestamp

        Raises:
            ConnectionError: If unable to connect to the provider API
            ValueError: If remote_id is invalid or document not found
        """

    @abstractmethod
    def get_remote_url(self, remote_id: str) -> str | None:
        """
        Get the direct URL to access the document on the external platform.

        Args:
            remote_id: The remote identifier returned by push_document()

        Returns:
            URL string or None if not available

        Raises:
            ValueError: If remote_id is invalid
        """

    def delete_remote_document(self, remote_id: str) -> bool:
        """
        Delete the document from the external platform (optional).

        This method is optional and may not be supported by all providers.
        Default implementation returns False.

        Args:
            remote_id: The remote identifier returned by push_document()

        Returns:
            True if deletion was successful, False if not supported or failed
        """
        return False

    def validate_credentials(self) -> bool:
        """
        Validate that the credentials are correct and can connect to the API.

        Returns:
            True if credentials are valid, False otherwise
        """
        try:
            # Default implementation - providers should override for real validation
            return bool(self.api_url and self.credentials)
        except Exception:
            return False

    def get_provider_name(self) -> str:
        """
        Get a human-readable name for this provider.

        Returns:
            Provider name string
        """
        return self.__class__.__name__.replace("Provider", "")

    def get_capabilities(self) -> ProviderCapabilities:
        """
        Return provider capabilities used by orchestration tasks.

        Providers can override this method to expose support for
        metadata-only pushes, status tracking availability, and
        expected push parameters.
        """
        return ProviderCapabilities()


class ProviderRegistry:
    """
    Registry for dynamically registering and retrieving integration providers.

    This allows adding new providers without modifying existing code.
    """

    _providers: dict[str, type[BaseIntegrationProvider]] = {}

    @classmethod
    def register(
        cls,
        provider_type: str,
        provider_class: type[BaseIntegrationProvider],
    ):
        """
        Register a provider class for a given type.

        Args:
            provider_type: String identifier (e.g., "docuseal", "documenso")
            provider_class: Provider class that extends BaseIntegrationProvider
        """
        if not issubclass(provider_class, BaseIntegrationProvider):
            raise TypeError(f"{provider_class} must extend BaseIntegrationProvider")
        cls._providers[provider_type.lower()] = provider_class

    @classmethod
    def get_provider(cls, provider_type: str) -> type[BaseIntegrationProvider] | None:
        """
        Get a provider class by type.

        Args:
            provider_type: String identifier

        Returns:
            Provider class or None if not found
        """
        return cls._providers.get(provider_type.lower())

    @classmethod
    def create_provider(
        cls,
        provider_type: str,
        integration: Any,
    ) -> BaseIntegrationProvider | None:
        """
        Create a provider instance for the given integration.

        Args:
            provider_type: String identifier
            integration: Integration model instance

        Returns:
            Provider instance or None if type not found
        """
        provider_class = cls.get_provider(provider_type)
        if provider_class:
            return provider_class(integration)
        return None

    @classmethod
    def list_providers(cls) -> list[str]:
        """
        List all registered provider types.

        Returns:
            List of provider type strings
        """
        return list(cls._providers.keys())
