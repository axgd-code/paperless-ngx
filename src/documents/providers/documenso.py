"""
Documenso Provider Implementation

Documenso is an open-source DocuSign alternative for document signing.
API Documentation: https://openapi.documenso.com/reference
"""

import logging
from typing import Any, Dict, Optional

import requests
from django.utils import timezone

from documents.interfaces import (
    BaseIntegrationProvider,
    IntegrationStatus,
    ProviderRegistry,
    PushResult,
    StatusResult,
)
from documents.models import Document

logger = logging.getLogger("paperless.integrations.documenso")


class DocumensoProvider(BaseIntegrationProvider):
    """
    Provider for Documenso document signing platform.

    Documenso uses API Key authentication and provides document signing workflows.
    API Reference: https://openapi.documenso.com/reference
    """

    def __init__(self, integration):
        """
        Initialize Documenso provider.

        Args:
            integration: Integration model instance with credentials
        """
        super().__init__(integration)
        self.api_url = integration.api_url.rstrip("/")
        credentials = integration.credentials or {}
        self.api_key = credentials.get("api_key", "")
        self.timeout = 30

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def validate_credentials(self) -> bool:
        """
        Validate API credentials by making a test request.

        Returns:
            bool: True if credentials are valid
        """
        if not self.api_key:
            logger.error("Documenso API key is missing")
            return False

        try:
            # Test with /api/v1/user endpoint
            response = requests.get(
                f"{self.api_url}/api/v1/user",
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to validate Documenso credentials: {e}")
            return False

    def push_document(
        self,
        document_id: int,
        params: Optional[Dict[str, Any]] = None,
    ) -> PushResult:
        """
        Send a document to Documenso for signing.

        Uses the /api/v1/documents endpoint to create a document
        and /api/v1/documents/{id}/send to send for signature.

        Args:
            document_id: ID of the Paperless document
            params: Optional parameters including:
                - recipients: List of recipient emails
                - subject: Email subject
                - message: Email message
                - redirect_url: URL to redirect after signing

        Returns:
            PushResult with remote_id and status

        Raises:
            Exception: If document cannot be sent
        """
        params = params or {}
        recipients = params.get("recipients", [])
        subject = params.get("subject", "Document to sign")
        message = params.get("message", "Please sign this document")

        try:
            # Get document from Paperless
            document = Document.objects.get(pk=document_id)
            logger.info(
                f"Sending document {document_id} ({document.title}) to Documenso"
            )

            # Step 1: Upload document to Documenso
            with open(document.source_path, "rb") as f:
                files = {"file": (document.title, f, "application/pdf")}
                upload_response = requests.post(
                    f"{self.api_url}/api/v1/documents",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                    },
                    files=files,
                    data={
                        "title": document.title,
                    },
                    timeout=self.timeout,
                )
                upload_response.raise_for_status()
                doc_data = upload_response.json()
                remote_id = str(doc_data["id"])

            logger.info(f"Document uploaded to Documenso with ID: {remote_id}")

            # Step 2: Add recipients
            for idx, recipient_email in enumerate(recipients):
                recipient_response = requests.post(
                    f"{self.api_url}/api/v1/documents/{remote_id}/recipients",
                    headers=self._get_headers(),
                    json={
                        "email": recipient_email,
                        "name": f"Recipient {idx + 1}",
                        "role": "SIGNER",
                    },
                    timeout=self.timeout,
                )
                recipient_response.raise_for_status()

            # Step 3: Send document for signing
            send_response = requests.post(
                f"{self.api_url}/api/v1/documents/{remote_id}/send",
                headers=self._get_headers(),
                json={
                    "subject": subject,
                    "message": message,
                },
                timeout=self.timeout,
            )
            send_response.raise_for_status()

            logger.info(f"Document {remote_id} sent for signing via Documenso")

            return PushResult(
                success=True,
                remote_id=remote_id,
                status=IntegrationStatus.PENDING,
                message="Document sent for signing",
                metadata={
                    "subject": subject,
                    "recipients_count": len(recipients),
                    "sent_at": timezone.now().isoformat(),
                },
            )

        except Document.DoesNotExist:
            error_msg = f"Document {document_id} not found"
            logger.error(error_msg)
            raise Exception(error_msg)

        except requests.exceptions.HTTPError as e:
            error_msg = f"Documenso API error: {e.response.status_code} - {e.response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)

        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to send document to Documenso: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)

        except Exception as e:
            error_msg = f"Unexpected error sending document to Documenso: {e}"
            logger.error(error_msg)
            raise

    def get_status(self, remote_id: str) -> StatusResult:
        """
        Get signing status from Documenso.

        Documenso statuses:
        - DRAFT: Document is being prepared
        - PENDING: Document sent, awaiting signatures
        - COMPLETED: All signatures collected
        - DECLINED: Signing was declined
        - EXPIRED: Document signing expired

        Args:
            remote_id: Documenso document ID

        Returns:
            StatusResult with current status

        Raises:
            Exception: If status cannot be retrieved
        """
        try:
            response = requests.get(
                f"{self.api_url}/api/v1/documents/{remote_id}",
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            doc_data = response.json()

            # Map Documenso status to IntegrationStatus
            documenso_status = doc_data.get("status", "UNKNOWN").upper()
            status_mapping = {
                "DRAFT": IntegrationStatus.PENDING,
                "PENDING": IntegrationStatus.PROCESSING,
                "COMPLETED": IntegrationStatus.SIGNED,
                "DECLINED": IntegrationStatus.FAILED,
                "EXPIRED": IntegrationStatus.FAILED,
            }

            status = status_mapping.get(
                documenso_status,
                IntegrationStatus.PENDING,
            )

            logger.info(
                f"Documenso document {remote_id} status: {documenso_status} -> {status}"
            )

            return StatusResult(
                status=status,
                message=f"Document status: {documenso_status}",
                metadata={
                    "documenso_status": documenso_status,
                    "updated_at": doc_data.get("updatedAt"),
                    "completed_at": doc_data.get("completedAt"),
                },
            )

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Documenso document {remote_id} not found")
                return StatusResult(
                    status=IntegrationStatus.FAILED,
                    message="Document not found on Documenso",
                    metadata={},
                )
            error_msg = f"Documenso API error: {e.response.status_code}"
            logger.error(error_msg)
            raise Exception(error_msg)

        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to get status from Documenso: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def get_remote_url(self, remote_id: str) -> str:
        """
        Get URL to view document in Documenso console.

        Args:
            remote_id: Documenso document ID

        Returns:
            URL to document in Documenso
        """
        # Standard Documenso URL format
        return f"{self.api_url}/documents/{remote_id}"

    def delete_remote_document(self, remote_id: str) -> bool:
        """
        Delete document from Documenso.

        Args:
            remote_id: Documenso document ID

        Returns:
            True if successful

        Raises:
            Exception: If deletion fails
        """
        try:
            response = requests.delete(
                f"{self.api_url}/api/v1/documents/{remote_id}",
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()

            logger.info(f"Documenso document {remote_id} deleted")
            return True

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Documenso document {remote_id} already deleted")
                return True
            error_msg = f"Failed to delete Documenso document: {e.response.status_code}"
            logger.error(error_msg)
            raise Exception(error_msg)

        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to delete document from Documenso: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)


# Register provider
ProviderRegistry.register("documenso", DocumensoProvider)
