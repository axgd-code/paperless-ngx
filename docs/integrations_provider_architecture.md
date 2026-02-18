---
title: Integration Provider Architecture
---

# Integration Provider Architecture

This page documents the robustness of `BaseIntegrationProvider` for heterogeneous third-party integrations (signature, logistics, AI analysis, accounting) and the extension points used by task orchestration.

## Current Contract

The integration contract in `src/documents/interfaces.py` is centered around:

-   `push_document(document_id, params=None) -> PushResult`
-   `get_status(remote_id) -> StatusResult`
-   `get_remote_url(remote_id) -> str | None`
-   Optional: `delete_remote_document(remote_id)`
-   Optional: `validate_credentials()`

`PushResult.metadata` already allows arbitrary provider-specific payloads (for example extracted tags, accounting fields, tracking references, API receipts).

## Stress-Test Matrix

### 1) AI / Analysis Providers (OpenAI-like)

Typical output is not a remote document but metadata such as:

-   Summary
-   Tags / labels
-   Classification scores
-   Structured extraction output

Assessment:

-   `push_document(..., params)` is suitable (prompt/template/model settings can be passed in `params`).
-   `PushResult.metadata` is suitable for analysis output.
-   The previous orchestration flow expected `remote_id` for success, which is not always applicable.

### 2) Logistics Providers (Maileva-like)

Typical lifecycle combines technical acceptance and physical delivery progression:

-   Accepted by provider
-   Printed / dispatched
-   In transit / delivered / returned

Assessment:

-   `get_status(remote_id)` is suitable for asynchronous tracking.
-   `StatusResult.metadata` can carry postal tracking identifiers and carrier events.
-   Capability signaling is useful because not all providers expose the same synchronization model.

### 3) Accounting Providers (Pennylane-like)

Typical push requires document plus structured financial metadata:

-   VAT rate / code
-   Total amount
-   Supplier/accounting dimensions
-   Accounting period / ledger target

Assessment:

-   Existing `params` is suitable for dynamic financial fields.
-   `PushResult.metadata` can store normalized accounting acknowledgements.
-   Optional provider-level declarations of required/optional fields improve validation and UX guidance.

## Gaps Identified

Two architectural gaps were identified:

1. No explicit capability contract to describe provider behavior differences.
2. Task orchestration treated `remote_id` as mandatory for successful pushes.

## Implemented Improvements

The following changes were applied:

-   Added `ProviderCapabilities` dataclass in `src/documents/interfaces.py`.
-   Added `BaseIntegrationProvider.get_capabilities()` with a safe default.
-   Implemented provider capabilities in current providers (`DocuSeal`, `Documenso`, `DigiPoste`).
-   Updated task orchestration (`src/documents/tasks.py`) to:
    -   support successful metadata-only pushes (without external remote artifact),
    -   create an internal synthetic `remote_id` when provider capabilities allow metadata-only mode,
    -   skip remote status synchronization for providers that declare `supports_status_tracking=False`.

This keeps backward compatibility with existing providers and enables non-file-centric integrations without major interface breakage.

## How to Model New Providers

### AI provider example

-   `produces_remote_document=False`
-   `supports_metadata_only_push=True`
-   `supports_status_tracking=False`
-   Declare optional params such as `model`, `prompt_template`, `max_tokens`.

### Logistics provider example

-   `produces_remote_document=True` (or provider job id)
-   `supports_status_tracking=True`
-   Expose tracking references in `StatusResult.metadata`.

### Accounting provider example

-   `produces_remote_document=True`
-   `supports_status_tracking=True` (if asynchronous bookkeeping exists)
-   Declare `required_push_params` such as `amount`, `vat_rate`, `currency`.

## Design Guidance

When adding providers:

-   Keep provider-specific payloads inside `params` (input) and `metadata` (output).
-   Use capabilities instead of hard-coded assumptions in orchestration.
-   Return normalized `IntegrationStatus` values and keep raw provider status in `metadata`.
-   Prefer additive evolution of capabilities to avoid breaking existing providers.
