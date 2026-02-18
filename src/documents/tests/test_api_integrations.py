"""
Tests for Integration API with focus on local/self-hosted URL support
"""
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from documents.models import Integration
from documents.tests.utils import DirectoriesMixin


class TestIntegrationLocalURLSupport(DirectoriesMixin, APITestCase):
    """
    Test suite to verify that Integration API properly supports
    local/self-hosted instances with various URL formats
    """

    def setUp(self) -> None:
        super().setUp()
        self.user = User.objects.create_superuser(username="test_admin")
        self.client.force_authenticate(user=self.user)

    def test_integration_accepts_localhost_url(self):
        """Test that localhost URLs are accepted"""
        response = self.client.post(
            "/api/integrations/",
            {
                "name": "Local Documenso",
                "provider_type": 1,  # Documenso
                "api_url": "http://localhost:3000",
                "credentials": {"api_key": "test-key"},
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["api_url"], "http://localhost:3000")

    def test_integration_accepts_localhost_with_port(self):
        """Test that localhost with custom port is accepted"""
        response = self.client.post(
            "/api/integrations/",
            {
                "name": "Local with Port",
                "provider_type": 1,
                "api_url": "http://localhost:8080",
                "credentials": {"api_key": "test-key"},
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_integration_accepts_loopback_ip(self):
        """Test that 127.0.0.1 is accepted"""
        response = self.client.post(
            "/api/integrations/",
            {
                "name": "Loopback IP",
                "provider_type": 1,
                "api_url": "http://127.0.0.1:3000",
                "credentials": {"api_key": "test-key"},
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_integration_accepts_private_network_ip(self):
        """Test that private network IPs are accepted"""
        response = self.client.post(
            "/api/integrations/",
            {
                "name": "Private Network",
                "provider_type": 1,
                "api_url": "http://192.168.1.100:3000",
                "credentials": {"api_key": "test-key"},
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_integration_accepts_custom_local_domain(self):
        """Test that custom local domains are accepted"""
        response = self.client.post(
            "/api/integrations/",
            {
                "name": "Custom Domain",
                "provider_type": 1,
                "api_url": "https://documenso.local",
                "credentials": {"api_key": "test-key"},
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_integration_accepts_docker_service_name(self):
        """Test that Docker service names are accepted"""
        response = self.client.post(
            "/api/integrations/",
            {
                "name": "Docker Service",
                "provider_type": 1,
                "api_url": "http://documenso:3000",
                "credentials": {"api_key": "test-key"},
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_integration_accepts_cloud_url(self):
        """Test that cloud URLs are still accepted"""
        response = self.client.post(
            "/api/integrations/",
            {
                "name": "Cloud Service",
                "provider_type": 1,
                "api_url": "https://app.documenso.com",
                "credentials": {"api_key": "test-key"},
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_integration_rejects_invalid_url(self):
        """Test that invalid URLs are rejected"""
        response = self.client.post(
            "/api/integrations/",
            {
                "name": "Invalid URL",
                "provider_type": 1,
                "api_url": "not-a-valid-url",
                "credentials": {"api_key": "test-key"},
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_integration_rejects_ftp_scheme(self):
        """Test that non-HTTP schemes are rejected"""
        response = self.client.post(
            "/api/integrations/",
            {
                "name": "FTP URL",
                "provider_type": 1,
                "api_url": "ftp://localhost:21",
                "credentials": {"api_key": "test-key"},
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_integration_list_with_local_urls(self):
        """Test that integrations with local URLs can be listed"""
        # Create test integrations
        Integration.objects.create(
            name="Local Test 1",
            provider_type=1,
            api_url="http://localhost:3000",
            credentials={"api_key": "key1"},
            is_active=True,
            owner=self.user,
        )
        Integration.objects.create(
            name="Local Test 2",
            provider_type=1,
            api_url="http://192.168.1.100:8080",
            credentials={"api_key": "key2"},
            is_active=True,
            owner=self.user,
        )

        response = self.client.get("/api/integrations/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_integration_update_url_to_local(self):
        """Test that URL can be updated to a local URL"""
        integration = Integration.objects.create(
            name="Cloud Integration",
            provider_type=1,
            api_url="https://app.documenso.com",
            credentials={"api_key": "cloud-key"},
            is_active=True,
            owner=self.user,
        )

        # Update to local URL
        response = self.client.patch(
            f"/api/integrations/{integration.id}/",
            {
                "api_url": "http://localhost:3000",
                "credentials": {"api_key": "local-key"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["api_url"], "http://localhost:3000")

        # Verify in database
        integration.refresh_from_db()
        self.assertEqual(integration.api_url, "http://localhost:3000")
