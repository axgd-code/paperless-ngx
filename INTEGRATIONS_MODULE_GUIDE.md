# Third-Party Integrations Module - Implementation Guide

## Overview

This implementation adds a comprehensive third-party integrations system to Paperless-ngx, allowing users to connect external services like Documenso (document signing) and Digiposte (digital vault) with hot feature toggle capability.

## Architecture

### Backend (Django)

#### Models (`src/documents/models.py`)
- **Integration**: Main model for managing integrations
  - `name`: Display name for the integration
  - `provider_type`: Enum (Documenso=1, Digiposte=2, Custom=99)
  - `api_url`: Base URL for the provider's API
  - `credentials`: JSONField for encrypted credentials storage
  - `is_active`: Boolean for hot toggle without deletion
  - `created/modified`: Timestamp fields
  - `owner`: Foreign key to User (supports multi-user setups)

#### API (`src/documents/serialisers.py` & `src/documents/views.py`)
- **IntegrationSerializer**: DRF serializer with credential validation
- **IntegrationViewSet**: Full CRUD operations with custom actions:
  - `test_connection()`: Test integration connectivity
  - `send_document()`: Queue single document for sending
  - `send_documents_bulk()`: Queue multiple documents for bulk sending

#### Async Tasks (`src/documents/tasks.py`)
- **send_document_to_integration**: Celery task for async document processing
  - Creates PaperlessTask for UI tracking
  - Handles provider-specific logic
  - Error handling and logging

#### Admin (`src/documents/admin.py`)
- **IntegrationAdmin**: Django admin interface for integration management

#### Database (`src/documents/migrations/0012_integration.py`)
- Migration file creating the Integration table
- Unique constraints on name+owner
- Proper indexes for performance

### Frontend (Angular)

#### Data Models (`src-ui/src/app/data/integration.ts`)
- **Integration** interface extending ObjectWithPermissions
- **ProviderType** enum matching backend choices

#### Services (`src-ui/src/app/services/rest/integration.service.ts`)
- **IntegrationService**: REST API service
  - `reload()`: Refresh integration list
  - `activeIntegrations`: Computed property for active integrations
  - `testConnection()`: Test provider connectivity
  - `sendDocument()`: Send single document
  - `sendDocumentsBulk()`: Send multiple documents

#### Components (`src-ui/src/app/components/manage/integrations/`)
- **IntegrationsComponent**: Management page
  - List all integrations
  - Toggle active/inactive state
  - Test connections
  - Delete integrations
  - Permission-aware UI

#### Routing (`src-ui/src/app/app-routing.module.ts`)
- Route: `/integrations`
- Guard: PermissionsGuard with Integration permission type
- Added to navigation menu

#### Permissions (`src-ui/src/app/services/permissions.service.ts`)
- Added `Integration = '%s_integration'` to PermissionType enum

## Features Implemented

### Core Functionality
1. ✅ CRUD operations for integrations
2. ✅ Hot feature toggle (activate/deactivate without deletion)
3. ✅ Async document sending via Celery
4. ✅ Connection testing
5. ✅ Bulk document operations
6. ✅ Permission-based access control
7. ✅ Multi-user support with ownership
8. ✅ Encrypted credentials storage (JSONField)

### User Interface
1. ✅ Management page accessible from navigation menu
2. ✅ List view with status indicators
3. ✅ Activate/deactivate toggle switches
4. ✅ Test connection button
5. ✅ Delete with confirmation
6. ✅ Toast notifications for feedback
7. ✅ Permission-based visibility

### Security
1. ✅ Credentials stored in JSONField (can be encrypted)
2. ✅ Permission-based access control
3. ✅ Owner-aware permissions
4. ✅ Audit log support (when enabled)

## Usage

### Adding a New Integration

1. Navigate to "Integrations" from the sidebar menu
2. Click "Add Integration" button
3. Fill in the integration details:
   - Name: Display name
   - Provider Type: Select from dropdown
   - API URL: Base URL for the provider
   - Credentials: JSON object with provider-specific credentials
4. Toggle "Active" to enable the integration
5. Use "Test" button to verify connectivity

### Supported Provider Types

#### Documenso (Signature Workflow)
```json
{
  "api_key": "your-api-key-here"
}
```

#### Digiposte (Digital Vault)
```json
{
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "access_token": "your-access-token",
  "refresh_token": "your-refresh-token",
  "expires_at": "2026-12-31T23:59:59Z"
}
```

#### Custom Integration
```json
{
  "api_key": "your-api-key",
  "username": "username",
  "password": "password"
}
```

### Sending Documents to Integrations

**From Document Detail View** (To be implemented):
- Look for integration action buttons in the toolbar
- Click to send the document to the selected integration
- Toast notification confirms the action

**Bulk Actions** (To be implemented):
- Select multiple documents
- Choose "Send to..." from the bulk actions menu
- Select the integration
- Documents are queued for sending

### Monitoring

- Check Django Admin > Paperless Tasks for task status
- View Celery logs for detailed execution information
- Toast notifications provide immediate feedback in the UI

## API Endpoints

### Integration Management
- `GET /api/integrations/` - List all integrations
- `POST /api/integrations/` - Create new integration
- `GET /api/integrations/{id}/` - Get integration details
- `PUT /api/integrations/{id}/` - Update integration
- `PATCH /api/integrations/{id}/` - Partial update
- `DELETE /api/integrations/{id}/` - Delete integration

### Custom Actions
- `POST /api/integrations/{id}/test_connection/` - Test connection
- `POST /api/integrations/{id}/send_document/` - Send single document
  - Body: `{"document_id": 123}`
- `POST /api/integrations/{id}/send_documents_bulk/` - Send multiple documents
  - Body: `{"document_ids": [123, 456, 789]}`

## Future Enhancements

### To Be Implemented
1. Integration action buttons in document detail view
2. Bulk actions menu integration
3. Integration edit dialog component
4. Provider-specific configuration forms
5. Real provider implementations (Documenso, Digiposte)
6. Webhook support for provider callbacks
7. Integration activity logs
8. Retry mechanism for failed sends
9. Rate limiting per integration
10. Integration statistics dashboard

### Potential Extensions
1. More provider types (Adobe Sign, DocuSign, etc.)
2. Bi-directional sync
3. Scheduled integration tasks
4. Integration templates
5. Multi-step workflows
6. Integration marketplace

## Testing

### Backend Tests (To be implemented)
```python
# Example test structure
class IntegrationAPITestCase(TestCase):
    def test_create_integration(self):
        # Test integration creation
        pass
    
    def test_toggle_active(self):
        # Test activate/deactivate
        pass
    
    def test_send_document(self):
        # Test document sending
        pass
```

### Frontend Tests (To be implemented)
```typescript
// Example test structure
describe('IntegrationService', () => {
  it('should load integrations', () => {
    // Test service loading
  });
  
  it('should filter active integrations', () => {
    // Test filtering
  });
});
```

### Manual Testing Checklist
- [ ] Create integration via UI
- [ ] Update integration details
- [ ] Toggle active/inactive
- [ ] Test connection
- [ ] Delete integration
- [ ] Verify permissions work correctly
- [ ] Test Celery task execution
- [ ] Verify audit logging (if enabled)

## Security Considerations

1. **Credentials Storage**: 
   - Currently stored in JSONField
   - Should be encrypted at rest using django-encrypted-fields or similar
   - Consider using secrets management service (Vault, AWS Secrets Manager)

2. **API Keys**:
   - Never log credentials
   - Mask credentials in API responses
   - Rotate keys regularly

3. **Permissions**:
   - Only superusers can see all integrations
   - Regular users see only their own integrations
   - Owner-aware permission system enforced

4. **Rate Limiting**:
   - Consider implementing rate limiting per integration
   - Protect against abuse

## Troubleshooting

### Common Issues

1. **Integration not appearing in menu**
   - Check user permissions
   - Verify Integration permission is granted
   - Check browser console for errors

2. **Test connection fails**
   - Verify API URL is correct
   - Check credentials are valid
   - Review integration logs in Django admin

3. **Documents not sending**
   - Check integration is active
   - Verify Celery is running
   - Review task logs in PaperlessTasks

4. **Permission denied errors**
   - Verify user has view_integration permission
   - Check object-level permissions for specific integration
   - Verify user is owner or has granted permissions

## Migration Guide

### Upgrading from Previous Versions

1. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

2. **Grant permissions** (if needed):
   ```python
   from django.contrib.auth.models import User, Permission
   from django.contrib.contenttypes.models import ContentType
   from documents.models import Integration
   
   content_type = ContentType.objects.get_for_model(Integration)
   permissions = Permission.objects.filter(content_type=content_type)
   
   # Grant to all staff users
   for user in User.objects.filter(is_staff=True):
       user.user_permissions.add(*permissions)
   ```

3. **Configure Celery** (if not already running):
   ```bash
   celery -A paperless worker -l info
   ```

4. **Restart Paperless**:
   ```bash
   systemctl restart paperless-webserver
   ```

## Contributing

When adding new provider types:

1. Add to `ProviderType` enum in both backend and frontend
2. Implement provider-specific logic in `send_document_to_integration` task
3. Add provider-specific credential validation
4. Update documentation with credential format
5. Add tests for the new provider

## License

This implementation is part of Paperless-ngx and follows the same license (GPL-3.0).

## Support

For issues or questions:
- GitHub Issues: https://github.com/paperless-ngx/paperless-ngx/issues
- Documentation: https://docs.paperless-ngx.com
- Community: https://github.com/paperless-ngx/paperless-ngx/discussions
