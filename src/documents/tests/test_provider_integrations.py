"""
Comprehensive tests for integration providers.

Tests for Documenso and DigiPoste providers using the Provider Pattern.
Uses mocked HTTP responses to avoid real API calls.
"""

import json
from unittest import mock

import pytest
import responses
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from documents.interfaces import IntegrationStatus, ProviderRegistry
from documents.models import (
    Document,
    DocumentIntegrationMetadata,
    Integration,
)
from documents.providers.digiposte import DigiPosteProvider
from documents.providers.documenso import DocumensoProvider
from documents.tests.mocks.provider_responses import (
    DigiPosteResponses,
    DocumensoResponses,
)


class TestDocumensoProvider(TestCase):
    """Test suite for DocumensoProvider."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(username="testuser")

        # Create Documenso integration
        self.integration = Integration.objects.create(
            name="Test Documenso",
            provider_type="documenso",
            api_url="https://api.documenso.com",
            credentials={
                "api_key": "test_api_key_123",
            },
            is_active=True,
            owner=self.user,
        )

        # Create test document
        self.document = Document.objects.create(
            title="Test Document.pdf",
            content="Test content",
            mime_type="application/pdf",
            owner=self.user,
        )

        # Provider instance
        self.provider = DocumensoProvider(self.integration)

    @responses.activate
    def test_validate_credentials_success(self):
        """Test successful credential validation."""
        responses.add(
            responses.GET,
            "https://api.documenso.com/api/v1/user",
            json=DocumensoResponses.user_success(),
            status=200,
        )

        result = self.provider.validate_credentials()
        self.assertTrue(result)

    @responses.activate
    def test_validate_credentials_failure(self):
        """Test failed credential validation."""
        responses.add(
            responses.GET,
            "https://api.documenso.com/api/v1/user",
            json=DocumensoResponses.error_unauthorized(),
            status=401,
        )

        result = self.provider.validate_credentials()
        self.assertFalse(result)

    def test_validate_credentials_missing_api_key(self):
        """Test validation with missing API key."""
        self.integration.credentials = {}
        self.integration.save()
        self.provider = DocumensoProvider(self.integration)

        result = self.provider.validate_credentials()
        self.assertFalse(result)

    @responses.activate
    @mock.patch("documents.providers.documenso.open", create=True)
    def test_push_document_success(self, mock_open):
        """Test successful document push."""
        # Mock file operations
        mock_file = mock.MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock API responses
        responses.add(
            responses.POST,
            "https://api.documenso.com/api/v1/documents",
            json=DocumensoResponses.document_upload_success(),
            status=200,
        )

        responses.add(
            responses.POST,
            "https://api.documenso.com/api/v1/documents/doc_123/recipients",
            json=DocumensoResponses.recipient_add_success(),
            status=200,
        )

        responses.add(
            responses.POST,
            "https://api.documenso.com/api/v1/documents/doc_123/send",
            json=DocumensoResponses.document_send_success(),
            status=200,
        )

        # Execute
        result = self.provider.push_document(
            self.document.id,
            params={
                "recipients": ["signer@example.com"],
                "subject": "Please sign",
                "message": "Test message",
            },
        )

        # Assertions
        self.assertTrue(result.success)
        self.assertEqual(result.remote_id, "doc_123")
        self.assertEqual(result.status, IntegrationStatus.PENDING)
        self.assertIn("sent_at", result.metadata)

    @responses.activate
    @mock.patch("documents.providers.documenso.open", create=True)
    def test_push_document_upload_error(self, mock_open):
        """Test document push with upload error."""
        mock_file = mock.MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        responses.add(
            responses.POST,
            "https://api.documenso.com/api/v1/documents",
            json=DocumensoResponses.error_unauthorized(),
            status=401,
        )

        with self.assertRaises(Exception) as context:
            self.provider.push_document(self.document.id)

        self.assertIn("401", str(context.exception))

    def test_push_document_not_found(self):
        """Test push with non-existent document."""
        with self.assertRaises(Exception) as context:
            self.provider.push_document(99999)

        self.assertIn("not found", str(context.exception))

    @responses.activate
    def test_get_status_pending(self):
        """Test get status for pending document."""
        responses.add(
            responses.GET,
            "https://api.documenso.com/api/v1/documents/doc_123",
            json=DocumensoResponses.document_status(status="PENDING"),
            status=200,
        )

        result = self.provider.get_status("doc_123")

        self.assertEqual(result.status, IntegrationStatus.PROCESSING)
        self.assertIn("PENDING", result.message)
        self.assertEqual(result.metadata["documenso_status"], "PENDING")

    @responses.activate
    def test_get_status_completed(self):
        """Test get status for completed document."""
        responses.add(
            responses.GET,
            "https://api.documenso.com/api/v1/documents/doc_123",
            json=DocumensoResponses.document_status(status="COMPLETED"),
            status=200,
        )

        result = self.provider.get_status("doc_123")

        self.assertEqual(result.status, IntegrationStatus.SIGNED)
        self.assertIn("COMPLETED", result.message)
        self.assertIn("completedAt", result.metadata)

    @responses.activate
    def test_get_status_not_found(self):
        """Test get status for non-existent document."""
        responses.add(
            responses.GET,
            "https://api.documenso.com/api/v1/documents/doc_999",
            json=DocumensoResponses.error_not_found(),
            status=404,
        )

        result = self.provider.get_status("doc_999")

        self.assertEqual(result.status, IntegrationStatus.FAILED)
        self.assertIn("not found", result.message)

    def test_get_remote_url(self):
        """Test getting remote URL."""
        url = self.provider.get_remote_url("doc_123")
        self.assertEqual(url, "https://api.documenso.com/documents/doc_123")

    @responses.activate
    def test_delete_remote_document_success(self):
        """Test successful document deletion."""
        responses.add(
            responses.DELETE,
            "https://api.documenso.com/api/v1/documents/doc_123",
            status=204,
        )

        result = self.provider.delete_remote_document("doc_123")
        self.assertTrue(result)

    @responses.activate
    def test_delete_remote_document_already_deleted(self):
        """Test deleting already deleted document."""
        responses.add(
            responses.DELETE,
            "https://api.documenso.com/api/v1/documents/doc_123",
            json=DocumensoResponses.error_not_found(),
            status=404,
        )

        result = self.provider.delete_remote_document("doc_123")
        self.assertTrue(result)  # Should return True even if already deleted


class TestDigiPosteProvider(TestCase):
    """Test suite for DigiPosteProvider."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(username="testuser")

        # Create DigiPoste integration
        self.integration = Integration.objects.create(
            name="Test DigiPoste",
            provider_type="digiposte",
            api_url="https://api.laposte.fr/digiposte",
            credentials={
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "access_token": "test_access_token",
                "refresh_token": "test_refresh_token",
            },
            is_active=True,
            owner=self.user,
        )

        # Create test document
        self.document = Document.objects.create(
            title="Test Document.pdf",
            content="Test content",
            mime_type="application/pdf",
            owner=self.user,
        )

        # Provider instance
        self.provider = DigiPosteProvider(self.integration)

    @responses.activate
    def test_validate_credentials_success(self):
        """Test successful credential validation."""
        responses.add(
            responses.GET,
            "https://api.laposte.fr/digiposte/api/v3/user",
            json=DigiPosteResponses.user_success(),
            status=200,
        )

        result = self.provider.validate_credentials()
        self.assertTrue(result)

    @responses.activate
    def test_validate_credentials_with_refresh(self):
        """Test credential validation with token refresh."""
        # First call fails with 401
        responses.add(
            responses.GET,
            "https://api.laposte.fr/digiposte/api/v3/user",
            json=DigiPosteResponses.error_unauthorized(),
            status=401,
        )

        # Token refresh succeeds
        responses.add(
            responses.POST,
            "https://api.laposte.fr/digiposte/oauth/token",
            json=DigiPosteResponses.token_refresh_success(),
            status=200,
        )

        # Retry succeeds with new token
        responses.add(
            responses.GET,
            "https://api.laposte.fr/digiposte/api/v3/user",
            json=DigiPosteResponses.user_success(),
            status=200,
        )

        result = self.provider.validate_credentials()
        self.assertTrue(result)

        # Check that token was updated
        self.integration.refresh_from_db()
        self.assertEqual(
            self.integration.credentials["access_token"],
            "new_access_token_xyz",
        )

    @responses.activate
    @mock.patch("documents.providers.digiposte.open", create=True)
    def test_push_document_success(self, mock_open):
        """Test successful document archiving."""
        mock_file = mock.MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        responses.add(
            responses.POST,
            "https://api.laposte.fr/digiposte/api/v3/documents",
            json=DigiPosteResponses.document_upload_success(),
            status=200,
        )

        result = self.provider.push_document(
            self.document.id,
            params={
                "folder": "Paperless",
                "category": "Documents",
                "tags": ["important", "tax"],
            },
        )

        self.assertTrue(result.success)
        self.assertEqual(result.remote_id, "dp_doc_456")
        self.assertEqual(result.status, IntegrationStatus.ARCHIVED)
        self.assertEqual(result.metadata["folder"], "Paperless")
        self.assertEqual(result.metadata["tags"], ["important", "tax"])

    @responses.activate
    @mock.patch("documents.providers.digiposte.open", create=True)
    def test_push_document_with_token_refresh(self, mock_open):
        """Test document push with automatic token refresh."""
        mock_file = mock.MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # First upload fails with 401
        responses.add(
            responses.POST,
            "https://api.laposte.fr/digiposte/api/v3/documents",
            json=DigiPosteResponses.error_unauthorized(),
            status=401,
        )

        # Token refresh succeeds
        responses.add(
            responses.POST,
            "https://api.laposte.fr/digiposte/oauth/token",
            json=DigiPosteResponses.token_refresh_success(),
            status=200,
        )

        # Retry succeeds
        responses.add(
            responses.POST,
            "https://api.laposte.fr/digiposte/api/v3/documents",
            json=DigiPosteResponses.document_upload_success(),
            status=200,
        )

        result = self.provider.push_document(self.document.id)

        self.assertTrue(result.success)
        self.assertEqual(result.remote_id, "dp_doc_456")

    @responses.activate
    def test_get_status_archived(self):
        """Test get status for archived document."""
        responses.add(
            responses.GET,
            "https://api.laposte.fr/digiposte/api/v3/documents/dp_doc_456",
            json=DigiPosteResponses.document_status(status="ARCHIVED"),
            status=200,
        )

        result = self.provider.get_status("dp_doc_456")

        self.assertEqual(result.status, IntegrationStatus.ARCHIVED)
        self.assertIn("ARCHIVED", result.message)
        self.assertEqual(result.metadata["digiposte_status"], "ARCHIVED")

    @responses.activate
    def test_get_status_processing(self):
        """Test get status for processing document."""
        responses.add(
            responses.GET,
            "https://api.laposte.fr/digiposte/api/v3/documents/dp_doc_456",
            json=DigiPosteResponses.document_status(status="PROCESSING"),
            status=200,
        )

        result = self.provider.get_status("dp_doc_456")

        self.assertEqual(result.status, IntegrationStatus.PROCESSING)

    def test_get_remote_url(self):
        """Test getting remote URL."""
        url = self.provider.get_remote_url("dp_doc_456")
        self.assertEqual(
            url,
            "https://api.laposte.fr/digiposte/documents/dp_doc_456",
        )

    @responses.activate
    def test_delete_remote_document_success(self):
        """Test successful document deletion."""
        responses.add(
            responses.DELETE,
            "https://api.laposte.fr/digiposte/api/v3/documents/dp_doc_456",
            status=204,
        )

        result = self.provider.delete_remote_document("dp_doc_456")
        self.assertTrue(result)


class TestProviderRegistry(TestCase):
    """Test suite for ProviderRegistry and common provider functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(username="testuser")

    def test_registry_has_providers(self):
        """Test that providers are registered."""
        self.assertIn("documenso", ProviderRegistry._providers)
        self.assertIn("digiposte", ProviderRegistry._providers)
        self.assertIn("docuseal", ProviderRegistry._providers)

    def test_create_documenso_provider(self):
        """Test creating Documenso provider via registry."""
        integration = Integration.objects.create(
            name="Test Documenso",
            provider_type="documenso",
            api_url="https://api.documenso.com",
            credentials={"api_key": "test"},
            is_active=True,
            owner=self.user,
        )

        provider = ProviderRegistry.create_provider("documenso", integration)
        self.assertIsInstance(provider, DocumensoProvider)

    def test_create_digiposte_provider(self):
        """Test creating DigiPoste provider via registry."""
        integration = Integration.objects.create(
            name="Test DigiPoste",
            provider_type="digiposte",
            api_url="https://api.laposte.fr/digiposte",
            credentials={"access_token": "test"},
            is_active=True,
            owner=self.user,
        )

        provider = ProviderRegistry.create_provider("digiposte", integration)
        self.assertIsInstance(provider, DigiPosteProvider)

    def test_create_unknown_provider(self):
        """Test creating unknown provider raises error."""
        integration = Integration.objects.create(
            name="Test Unknown",
            provider_type="unknown",
            api_url="https://example.com",
            is_active=True,
            owner=self.user,
        )

        with self.assertRaises(ValueError):
            ProviderRegistry.create_provider("unknown", integration)


class TestDocumentIntegrationMetadata(TestCase):
    """Test suite for DocumentIntegrationMetadata model."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(username="testuser")

        self.integration = Integration.objects.create(
            name="Test Integration",
            provider_type="documenso",
            api_url="https://api.example.com",
            is_active=True,
            owner=self.user,
        )

        self.document = Document.objects.create(
            title="Test Document.pdf",
            content="Test content",
            mime_type="application/pdf",
            owner=self.user,
        )

    def test_create_metadata(self):
        """Test creating document integration metadata."""
        metadata = DocumentIntegrationMetadata.objects.create(
            document=self.document,
            integration=self.integration,
            remote_id="remote_123",
            status=IntegrationStatus.PENDING.value,
            remote_url="https://example.com/doc/123",
            metadata={"test": "value"},
        )

        self.assertEqual(metadata.document, self.document)
        self.assertEqual(metadata.integration, self.integration)
        self.assertEqual(metadata.remote_id, "remote_123")
        self.assertEqual(metadata.status, IntegrationStatus.PENDING.value)

    def test_unique_constraint(self):
        """Test that document+integration must be unique."""
        DocumentIntegrationMetadata.objects.create(
            document=self.document,
            integration=self.integration,
            remote_id="remote_123",
            status=IntegrationStatus.PENDING.value,
        )

        # Try to create duplicate
        with self.assertRaises(Exception):
            DocumentIntegrationMetadata.objects.create(
                document=self.document,
                integration=self.integration,
                remote_id="remote_456",
                status=IntegrationStatus.PENDING.value,
            )

    def test_update_status(self):
        """Test updating metadata status."""
        metadata = DocumentIntegrationMetadata.objects.create(
            document=self.document,
            integration=self.integration,
            remote_id="remote_123",
            status=IntegrationStatus.PENDING.value,
        )

        metadata.status = IntegrationStatus.SIGNED.value
        metadata.save()

        metadata.refresh_from_db()
        self.assertEqual(metadata.status, IntegrationStatus.SIGNED.value)


class TestFeatureToggle(TestCase):
    """Test suite for feature toggle (is_active) functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(username="testuser")

        self.document = Document.objects.create(
            title="Test Document.pdf",
            content="Test content",
            mime_type="application/pdf",
            owner=self.user,
        )

    def test_inactive_integration(self):
        """Test that inactive integrations should not be used."""
        integration = Integration.objects.create(
            name="Inactive Integration",
            provider_type="documenso",
            api_url="https://api.example.com",
            credentials={"api_key": "test"},
            is_active=False,  # Inactive
            owner=self.user,
        )

        # In real usage, the application should check is_active before
        # calling the provider. This test verifies the model state.
        self.assertFalse(integration.is_active)

    def test_active_integration(self):
        """Test that active integrations can be used."""
        integration = Integration.objects.create(
            name="Active Integration",
            provider_type="documenso",
            api_url="https://api.example.com",
            credentials={"api_key": "test"},
            is_active=True,  # Active
            owner=self.user,
        )

        self.assertTrue(integration.is_active)
        provider = ProviderRegistry.create_provider("documenso", integration)
        self.assertIsNotNone(provider)


class TestProviderErrorHandling(TestCase):
    """Test suite for provider error handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(username="testuser")

        self.integration = Integration.objects.create(
            name="Test Integration",
            provider_type="documenso",
            api_url="https://api.documenso.com",
            credentials={"api_key": "test"},
            is_active=True,
            owner=self.user,
        )

        self.provider = DocumensoProvider(self.integration)

        self.document = Document.objects.create(
            title="Test Document.pdf",
            content="Test content",
            mime_type="application/pdf",
            owner=self.user,
        )

    @responses.activate
    @mock.patch("documents.providers.documenso.open", create=True)
    def test_server_error_handling(self, mock_open):
        """Test handling of server errors (500)."""
        mock_file = mock.MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        responses.add(
            responses.POST,
            "https://api.documenso.com/api/v1/documents",
            json=DocumensoResponses.error_server(),
            status=500,
        )

        with self.assertRaises(Exception) as context:
            self.provider.push_document(self.document.id)

        self.assertIn("500", str(context.exception))

    @responses.activate
    def test_network_error_handling(self):
        """Test handling of network errors."""
        responses.add(
            responses.GET,
            "https://api.documenso.com/api/v1/documents/doc_123",
            body=Exception("Network error"),
        )

        with self.assertRaises(Exception) as context:
            self.provider.get_status("doc_123")

        self.assertIn("Failed to get status", str(context.exception))


# Run tests with subtests for common functionality
class TestProviderCommonFunctionality(TestCase):
    """Test common functionality across providers using subtests."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(username="testuser")

        self.document = Document.objects.create(
            title="Test Document.pdf",
            content="Test content",
            mime_type="application/pdf",
            owner=self.user,
        )

        self.providers_config = [
            {
                "name": "Documenso",
                "provider_type": "documenso",
                "api_url": "https://api.documenso.com",
                "credentials": {"api_key": "test"},
                "class": DocumensoProvider,
            },
            {
                "name": "DigiPoste",
                "provider_type": "digiposte",
                "api_url": "https://api.laposte.fr/digiposte",
                "credentials": {"access_token": "test"},
                "class": DigiPosteProvider,
            },
        ]

    def test_all_providers_have_required_methods(self):
        """Test that all providers implement required methods."""
        for config in self.providers_config:
            with self.subTest(provider=config["name"]):
                integration = Integration.objects.create(
                    name=f"Test {config['name']}",
                    provider_type=config["provider_type"],
                    api_url=config["api_url"],
                    credentials=config["credentials"],
                    is_active=True,
                    owner=self.user,
                )

                provider = config["class"](integration)

                # Check that all required methods exist
                self.assertTrue(hasattr(provider, "push_document"))
                self.assertTrue(hasattr(provider, "get_status"))
                self.assertTrue(hasattr(provider, "get_remote_url"))
                self.assertTrue(hasattr(provider, "delete_remote_document"))
                self.assertTrue(hasattr(provider, "validate_credentials"))

    def test_all_providers_return_correct_types(self):
        """Test that all providers return correct types."""
        for config in self.providers_config:
            with self.subTest(provider=config["name"]):
                integration = Integration.objects.create(
                    name=f"Test {config['name']}",
                    provider_type=config["provider_type"],
                    api_url=config["api_url"],
                    credentials=config["credentials"],
                    is_active=True,
                    owner=self.user,
                )

                provider = config["class"](integration)

                # get_remote_url should return string
                url = provider.get_remote_url("test_id")
                self.assertIsInstance(url, str)

                # validate_credentials should return bool
                # (Will fail without network, but type is correct)
                result = provider.validate_credentials()
                self.assertIsInstance(result, bool)
