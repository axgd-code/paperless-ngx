"""
DigiPoste Provider Implementation

DigiPoste is La Poste's digital vault for document archiving.
API Documentation: https://developer.laposte.fr/catalog-apis/digiposte@3
"""

import logging
from typing import Any

import requests
from django.utils import timezone

from documents.interfaces import BaseIntegrationProvider
from documents.interfaces import IntegrationStatus
from documents.interfaces import ProviderCapabilities
from documents.interfaces import ProviderRegistry
from documents.interfaces import PushResult
from documents.interfaces import StatusResult
from documents.models import Document

logger = logging.getLogger("paperless.integrations.digiposte")


class DigiPosteProvider(BaseIntegrationProvider):
    """
    Provider for DigiPoste digital vault platform.

    DigiPoste uses OAuth2 authentication and provides document archiving.
    API Reference: https://developer.laposte.fr/catalog-apis/digiposte@3
    """

    def __init__(self, integration):
        """
        Initialize DigiPoste provider.

        Args:
            integration: Integration model instance with credentials
        """
        super().__init__(integration)
        self.api_url = integration.api_url.rstrip("/")
        credentials = integration.credentials or {}
        self.client_id = credentials.get("client_id", "")
        self.client_secret = credentials.get("client_secret", "")
        self.access_token = credentials.get("access_token", "")
        self.refresh_token = credentials.get("refresh_token", "")
        self.timeout = 30

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for API requests."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def get_capabilities(self) -> ProviderCapabilities:
        """Return DigiPoste capabilities."""
        return ProviderCapabilities(
            produces_remote_document=True,
            supports_status_tracking=True,
            supports_remote_url=True,
            supports_delete=True,
            supports_metadata_only_push=False,
            optional_push_params=("folder", "category", "tags"),
        )

    def _refresh_access_token(self) -> bool:
        """
        Refresh OAuth2 access token using refresh token.

        Returns:
            bool: True if token refreshed successfully
        """
        if not self.refresh_token:
            logger.error("DigiPoste refresh token is missing")
            return False

        try:
            response = requests.post(
                f"{self.api_url}/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            token_data = response.json()

            self.access_token = token_data["access_token"]
            if "refresh_token" in token_data:
                self.refresh_token = token_data["refresh_token"]

            # Update stored credentials
            self.integration.credentials["access_token"] = self.access_token
            self.integration.credentials["refresh_token"] = self.refresh_token
            self.integration.save(update_fields=["credentials"])

            logger.info("DigiPoste access token refreshed")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to refresh DigiPoste token: {e}")
            return False

    def validate_credentials(self) -> bool:
        """
        Validate OAuth2 credentials by making a test request.

        Returns:
            bool: True if credentials are valid
        """
        if not self.access_token:
            logger.error("DigiPoste access token is missing")
            return False

        try:
            # Test with /api/v3/user endpoint
            response = requests.get(
                f"{self.api_url}/api/v3/user",
                headers=self._get_headers(),
                timeout=self.timeout,
            )

            if response.status_code == 401:
                # Try to refresh token
                logger.info("DigiPoste token expired, attempting refresh")
                if self._refresh_access_token():
                    # Retry with new token
                    response = requests.get(
                        f"{self.api_url}/api/v3/user",
                        headers=self._get_headers(),
                        timeout=self.timeout,
                    )
                    return response.status_code == 200
                return False

            return response.status_code == 200

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to validate DigiPoste credentials: {e}")
            return False

    def push_document(
        self,
        document_id: int,
        params: dict[str, Any] | None = None,
    ) -> PushResult:
        """
        Archive a document to DigiPoste.

        Uses the /api/v3/documents endpoint to upload a document.

        Args:
            document_id: ID of the Paperless document
            params: Optional parameters including:
                - folder: Target folder name
                - category: Document category
                - tags: List of tags

        Returns:
            PushResult with remote_id and status

        Raises:
            Exception: If document cannot be archived
        """
        params = params or {}
        folder = params.get("folder", "Paperless")
        category = params.get("category", "Documents")
        tags = params.get("tags", [])

        try:
            # Get document from Paperless
            document = Document.objects.get(pk=document_id)
            logger.info(
                f"Archiving document {document_id} ({document.title}) to DigiPoste",
            )

            # Upload document to DigiPoste
            with document.source_path.open("rb") as f:
                files = {
                    "file": (document.title, f, "application/pdf"),
                }
                data = {
                    "title": document.title,
                    "folder": folder,
                    "category": category,
                }
                if tags:
                    data["tags"] = ",".join(tags)

                response = requests.post(
                    f"{self.api_url}/api/v3/documents",
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                    },
                    files=files,
                    data=data,
                    timeout=self.timeout,
                )

                # Handle token expiration
                if response.status_code == 401:
                    logger.info("DigiPoste token expired, refreshing")
                    if self._refresh_access_token():
                        # Retry with new token
                        f.seek(0)  # Reset file pointer
                        response = requests.post(
                            f"{self.api_url}/api/v3/documents",
                            headers={
                                "Authorization": f"Bearer {self.access_token}",
                            },
                            files={"file": (document.title, f, "application/pdf")},
                            data=data,
                            timeout=self.timeout,
                        )

                response.raise_for_status()
                doc_data = response.json()
                remote_id = str(doc_data["id"])

            logger.info(f"Document archived to DigiPoste with ID: {remote_id}")

            return PushResult(
                success=True,
                remote_id=remote_id,
                status=IntegrationStatus.ARCHIVED,
                message="Document archived to DigiPoste",
                metadata={
                    "folder": folder,
                    "category": category,
                    "tags": tags,
                    "archived_at": timezone.now().isoformat(),
                },
            )

        except Document.DoesNotExist:
            error_msg = f"Document {document_id} not found"
            logger.error(error_msg)
            raise Exception(error_msg)

        except requests.exceptions.HTTPError as e:
            error_msg = (
                f"DigiPoste API error: {e.response.status_code} - {e.response.text}"
            )
            logger.error(error_msg)
            raise Exception(error_msg)

        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to archive document to DigiPoste: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)

        except Exception as e:
            error_msg = f"Unexpected error archiving document to DigiPoste: {e}"
            logger.error(error_msg)
            raise

    def get_status(self, remote_id: str) -> StatusResult:
        """
        Get document status from DigiPoste.

        DigiPoste statuses:
        - RECEIVED: Document successfully archived
        - PROCESSING: Document being processed
        - ARCHIVED: Document archived and available
        - DELETED: Document deleted from vault

        Args:
            remote_id: DigiPoste document ID

        Returns:
            StatusResult with current status

        Raises:
            Exception: If status cannot be retrieved
        """
        try:
            response = requests.get(
                f"{self.api_url}/api/v3/documents/{remote_id}",
                headers=self._get_headers(),
                timeout=self.timeout,
            )

            # Handle token expiration
            if response.status_code == 401 and self._refresh_access_token():
                response = requests.get(
                    f"{self.api_url}/api/v3/documents/{remote_id}",
                    headers=self._get_headers(),
                    timeout=self.timeout,
                )

            response.raise_for_status()
            doc_data = response.json()

            # Map DigiPoste status to IntegrationStatus
            digiposte_status = doc_data.get("status", "UNKNOWN").upper()
            status_mapping = {
                "RECEIVED": IntegrationStatus.ARCHIVED,
                "PROCESSING": IntegrationStatus.PROCESSING,
                "ARCHIVED": IntegrationStatus.ARCHIVED,
                "DELETED": IntegrationStatus.FAILED,
            }

            status = status_mapping.get(
                digiposte_status,
                IntegrationStatus.PENDING,
            )

            logger.info(
                f"DigiPoste document {remote_id} status: {digiposte_status} -> {status}",
            )

            return StatusResult(
                status=status,
                message=f"Document status: {digiposte_status}",
                metadata={
                    "digiposte_status": digiposte_status,
                    "updated_at": doc_data.get("updatedAt"),
                    "size": doc_data.get("size"),
                },
            )

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"DigiPoste document {remote_id} not found")
                return StatusResult(
                    status=IntegrationStatus.FAILED,
                    message="Document not found on DigiPoste",
                    metadata={},
                )
            error_msg = f"DigiPoste API error: {e.response.status_code}"
            logger.error(error_msg)
            raise Exception(error_msg)

        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to get status from DigiPoste: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def get_remote_url(self, remote_id: str) -> str:
        """
        Get URL to view document in DigiPoste portal.

        Args:
            remote_id: DigiPoste document ID

        Returns:
            URL to document in DigiPoste
        """
        # Standard DigiPoste URL format
        return f"{self.api_url}/documents/{remote_id}"

    def delete_remote_document(self, remote_id: str) -> bool:
        """
        Delete document from DigiPoste vault.

        Args:
            remote_id: DigiPoste document ID

        Returns:
            True if successful

        Raises:
            Exception: If deletion fails
        """
        try:
            response = requests.delete(
                f"{self.api_url}/api/v3/documents/{remote_id}",
                headers=self._get_headers(),
                timeout=self.timeout,
            )

            # Handle token expiration
            if response.status_code == 401 and self._refresh_access_token():
                response = requests.delete(
                    f"{self.api_url}/api/v3/documents/{remote_id}",
                    headers=self._get_headers(),
                    timeout=self.timeout,
                )

            response.raise_for_status()

            logger.info(f"DigiPoste document {remote_id} deleted")
            return True

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"DigiPoste document {remote_id} already deleted")
                return True
            error_msg = f"Failed to delete DigiPoste document: {e.response.status_code}"
            logger.error(error_msg)
            raise Exception(error_msg)

        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to delete document from DigiPoste: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)


# Register provider
ProviderRegistry.register("digiposte", DigiPosteProvider)
