"""
Mock API responses for integration provider tests.

Based on:
- Documenso OpenAPI: https://openapi.documenso.com/reference
- DigiPoste API: https://developer.laposte.fr/catalog-apis/digiposte@3
"""

from typing import Any, Dict


class DocumensoResponses:
    """Mock responses for Documenso API."""

    @staticmethod
    def user_success() -> Dict[str, Any]:
        """Successful user info response."""
        return {
            "id": "user_123",
            "email": "test@example.com",
            "name": "Test User",
            "createdAt": "2024-01-01T00:00:00Z",
        }

    @staticmethod
    def document_upload_success(doc_id: str = "doc_123") -> Dict[str, Any]:
        """Successful document upload response."""
        return {
            "id": doc_id,
            "title": "Test Document.pdf",
            "status": "DRAFT",
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z",
            "userId": "user_123",
        }

    @staticmethod
    def recipient_add_success(recipient_id: str = "recipient_123") -> Dict[str, Any]:
        """Successful recipient addition response."""
        return {
            "id": recipient_id,
            "email": "signer@example.com",
            "name": "Recipient 1",
            "role": "SIGNER",
            "documentId": "doc_123",
        }

    @staticmethod
    def document_send_success(doc_id: str = "doc_123") -> Dict[str, Any]:
        """Successful document send response."""
        return {
            "id": doc_id,
            "title": "Test Document.pdf",
            "status": "PENDING",
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:01Z",
            "sentAt": "2024-01-01T00:00:01Z",
        }

    @staticmethod
    def document_status(
        doc_id: str = "doc_123",
        status: str = "PENDING",
    ) -> Dict[str, Any]:
        """Document status response with various statuses."""
        base = {
            "id": doc_id,
            "title": "Test Document.pdf",
            "status": status,
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:01Z",
        }

        if status == "COMPLETED":
            base["completedAt"] = "2024-01-01T00:10:00Z"
        elif status == "DECLINED":
            base["declinedAt"] = "2024-01-01T00:05:00Z"
        elif status == "EXPIRED":
            base["expiredAt"] = "2024-01-01T00:15:00Z"

        return base

    @staticmethod
    def error_unauthorized() -> Dict[str, Any]:
        """401 Unauthorized error response."""
        return {
            "error": "Unauthorized",
            "message": "Invalid or expired API key",
            "statusCode": 401,
        }

    @staticmethod
    def error_not_found() -> Dict[str, Any]:
        """404 Not Found error response."""
        return {
            "error": "Not Found",
            "message": "Document not found",
            "statusCode": 404,
        }

    @staticmethod
    def error_server() -> Dict[str, Any]:
        """500 Internal Server Error response."""
        return {
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "statusCode": 500,
        }


class DigiPosteResponses:
    """Mock responses for DigiPoste API."""

    @staticmethod
    def user_success() -> Dict[str, Any]:
        """Successful user info response."""
        return {
            "id": "user_456",
            "email": "test@example.com",
            "firstName": "Test",
            "lastName": "User",
            "status": "ACTIVE",
        }

    @staticmethod
    def token_refresh_success() -> Dict[str, Any]:
        """Successful token refresh response."""
        return {
            "access_token": "new_access_token_xyz",
            "refresh_token": "new_refresh_token_xyz",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

    @staticmethod
    def document_upload_success(doc_id: str = "dp_doc_456") -> Dict[str, Any]:
        """Successful document upload response."""
        return {
            "id": doc_id,
            "title": "Test Document.pdf",
            "status": "RECEIVED",
            "folder": "Paperless",
            "category": "Documents",
            "size": 1024000,
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z",
        }

    @staticmethod
    def document_status(
        doc_id: str = "dp_doc_456",
        status: str = "ARCHIVED",
    ) -> Dict[str, Any]:
        """Document status response with various statuses."""
        return {
            "id": doc_id,
            "title": "Test Document.pdf",
            "status": status,
            "folder": "Paperless",
            "category": "Documents",
            "size": 1024000,
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:01Z",
        }

    @staticmethod
    def error_unauthorized() -> Dict[str, Any]:
        """401 Unauthorized error response."""
        return {
            "error": "unauthorized",
            "error_description": "Invalid or expired access token",
        }

    @staticmethod
    def error_not_found() -> Dict[str, Any]:
        """404 Not Found error response."""
        return {
            "error": "not_found",
            "error_description": "Document not found",
        }

    @staticmethod
    def error_server() -> Dict[str, Any]:
        """500 Internal Server Error response."""
        return {
            "error": "internal_server_error",
            "error_description": "An unexpected error occurred",
        }


def create_mock_response(
    status_code: int,
    json_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create a mock response object for testing.

    Args:
        status_code: HTTP status code
        json_data: JSON response data

    Returns:
        Dictionary mimicking requests.Response attributes
    """
    return {
        "status_code": status_code,
        "json": json_data,
        "text": str(json_data),
    }
