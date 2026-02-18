"""
Integration providers for external platforms.

This package contains implementations of BaseIntegrationProvider for various
third-party services (signature platforms, cloud storage, digital vaults, etc.).
"""

from documents.providers.docuseal import DocuSealProvider

__all__ = ["DocuSealProvider"]
