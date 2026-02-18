"""
DocuSeal provider implementation for document signature workflows.

DocuSeal is an open-source document signing platform that can be self-hosted
or used via their cloud service.

API Documentation: https://www.docuseal.co/docs/api
"""

import logging
from datetime import datetime
from typing import Any

import requests

from documents.interfaces import BaseIntegrationProvider
from documents.interfaces import IntegrationStatus
from documents.interfaces import ProviderCapabilities
from documents.interfaces import ProviderRegistry
from documents.interfaces import PushResult
from documents.interfaces import StatusResult
from documents.models import Document

logger = logging.getLogger("paperless.integrations.docuseal")


class DocuSealProvider(BaseIntegrationProvider):
    """
    Provider for DocuSeal signature platform.

    Features:
    - Upload documents for signature
    - Track signature status
    - Get signed document URL
    - Support for multiple signers

    Required credentials:
        - api_key: DocuSeal API key

    Optional parameters for push_document:
        - recipients: List of email addresses for signers
        - subject: Email subject for signature request
        - message: Email message for signature request
    """

    def __init__(self, integration: Any):
        super().__init__(integration)
        self.api_key = self.credentials.get("api_key")
        if not self.api_key:
            raise ValueError("DocuSeal provider requires 'api_key' in credentials")

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers with authentication."""
        return {
            "X-Auth-Token": self.api_key,
            "Content-Type": "application/json",
        }

    def get_capabilities(self) -> ProviderCapabilities:
        """Return DocuSeal capabilities."""
        return ProviderCapabilities(
            produces_remote_document=True,
            supports_status_tracking=True,
            supports_remote_url=True,
            supports_delete=True,
            supports_metadata_only_push=False,
            required_push_params=("recipients",),
            optional_push_params=("subject", "message", "template_id"),
        )

    def _handle_response(self, response: requests.Response) -> dict[str, Any]:
        """Handle API response and extract data."""
        try:
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            logger.error(
                f"DocuSeal API error: {e.response.status_code} - {e.response.text}",
            )
            raise ConnectionError(
                f"DocuSeal API returned {e.response.status_code}: {e.response.text}",
            )
        except ValueError:
            logger.error(f"Invalid JSON response from DocuSeal: {response.text}")
            raise ValueError("Invalid response from DocuSeal API")

    def push_document(
        self,
        document_id: int,
        params: dict[str, Any] | None = None,
    ) -> PushResult:
        """
        Upload a document to DocuSeal for signature.

        Args:
            document_id: Paperless document ID
            params: Optional parameters:
                - recipients: List of email addresses (required)
                - subject: Email subject (default: "Please sign this document")
                - message: Email message (optional)
                - template_id: DocuSeal template ID (optional)

        Returns:
            PushResult with submission ID and URL
        """
        try:
            # Get the document from Paperless
            document = Document.objects.get(pk=document_id)

            # Get recipients from params
            recipients = params.get("recipients", []) if params else []
            if not recipients:
                raise ValueError("DocuSeal requires at least one recipient email")

            # Prepare document file
            document_path = document.source_path
            if not document_path.exists():
                raise ValueError(f"Document file not found: {document_path}")

            # Prepare submission data
            submission_data = {
                "template": {
                    "name": document.title or f"Document_{document.pk}",
                    "documents": [],
                },
                "submissions": [
                    {
                        "email": email,
                        "role": "signer",
                    }
                    for email in recipients
                ],
                "send_email": True,
                "subject": params.get("subject", "Please sign this document")
                if params
                else "Please sign this document",
            }

            if params and params.get("message"):
                submission_data["message"] = params["message"]

            # Upload document file
            with document_path.open("rb") as f:
                files = {
                    "file": (
                        document_path.name,
                        f,
                        document.mime_type or "application/pdf",
                    ),
                }

                # Use DocuSeal API to create submission
                url = f"{self.api_url.rstrip('/')}/api/submissions"
                response = requests.post(
                    url,
                    headers=self._get_headers(),
                    data={"data": str(submission_data).replace("'", '"')},
                    files=files,
                    timeout=30,
                )

            result_data = self._handle_response(response)

            # Extract submission details
            submission_id = result_data.get("id") or result_data.get("submission_id")
            if not submission_id:
                raise ValueError("DocuSeal did not return a submission ID")

            remote_url = result_data.get("url") or f"{self.api_url}/s/{submission_id}"

            logger.info(
                f"Document {document_id} successfully sent to DocuSeal: {submission_id}",
            )

            return PushResult(
                success=True,
                remote_id=str(submission_id),
                remote_url=remote_url,
                status=IntegrationStatus.PENDING,
                message="Document sent for signature",
                metadata={
                    "recipients": recipients,
                    "submission_data": result_data,
                },
            )

        except Document.DoesNotExist:
            logger.error(f"Document {document_id} not found")
            return PushResult(
                success=False,
                message=f"Document {document_id} not found",
            )
        except Exception as e:
            logger.exception(f"Error pushing document {document_id} to DocuSeal: {e!s}")
            return PushResult(
                success=False,
                message=f"Error: {e!s}",
            )

    def get_status(self, remote_id: str) -> StatusResult:
        """
        Get the signature status of a DocuSeal submission.

        Args:
            remote_id: DocuSeal submission ID

        Returns:
            StatusResult with current signature status
        """
        try:
            url = f"{self.api_url.rstrip('/')}/api/submissions/{remote_id}"
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=10,
            )

            data = self._handle_response(response)

            # Map DocuSeal status to our standard status
            docuseal_status = data.get("status", "pending").lower()
            status_mapping = {
                "pending": IntegrationStatus.PENDING,
                "sent": IntegrationStatus.PENDING,
                "opened": IntegrationStatus.PROCESSING,
                "completed": IntegrationStatus.SIGNED,
                "signed": IntegrationStatus.SIGNED,
                "declined": IntegrationStatus.REJECTED,
                "expired": IntegrationStatus.EXPIRED,
            }

            status = status_mapping.get(docuseal_status, IntegrationStatus.PENDING)

            # Get timestamp
            updated_at_str = data.get("updated_at") or data.get("created_at")
            updated_at = (
                datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                if updated_at_str
                else datetime.now()
            )

            return StatusResult(
                status=status,
                updated_at=updated_at,
                message=f"DocuSeal status: {docuseal_status}",
                metadata=data,
            )

        except Exception as e:
            logger.error(
                f"Error getting status for DocuSeal submission {remote_id}: {e!s}",
            )
            return StatusResult(
                status=IntegrationStatus.FAILED,
                updated_at=datetime.now(),
                message=f"Error: {e!s}",
            )

    def get_remote_url(self, remote_id: str) -> str | None:
        """
        Get the URL to view the DocuSeal submission.

        Args:
            remote_id: DocuSeal submission ID

        Returns:
            URL to the submission page
        """
        try:
            # Try to get the actual URL from the API
            url = f"{self.api_url.rstrip('/')}/api/submissions/{remote_id}"
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=10,
            )

            data = self._handle_response(response)
            return data.get("url") or f"{self.api_url}/s/{remote_id}"

        except Exception as e:
            logger.warning(f"Could not fetch URL from API, using default: {e!s}")
            # Fallback to constructed URL
            return f"{self.api_url.rstrip('/')}/s/{remote_id}"

    def delete_remote_document(self, remote_id: str) -> bool:
        """
        Archive/delete a DocuSeal submission.

        Args:
            remote_id: DocuSeal submission ID

        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.api_url.rstrip('/')}/api/submissions/{remote_id}"
            response = requests.delete(
                url,
                headers=self._get_headers(),
                timeout=10,
            )

            response.raise_for_status()
            logger.info(f"DocuSeal submission {remote_id} deleted successfully")
            return True

        except Exception as e:
            logger.error(f"Error deleting DocuSeal submission {remote_id}: {e!s}")
            return False

    def validate_credentials(self) -> bool:
        """
        Validate DocuSeal API credentials.

        Returns:
            True if credentials are valid
        """
        try:
            # Try to list submissions to validate API key
            url = f"{self.api_url.rstrip('/')}/api/submissions"
            response = requests.get(
                url,
                headers=self._get_headers(),
                params={"limit": 1},
                timeout=10,
            )

            response.raise_for_status()
            return True

        except Exception as e:
            logger.error(f"DocuSeal credential validation failed: {e!s}")
            return False


# Register the DocuSeal provider
ProviderRegistry.register("docuseal", DocuSealProvider)
