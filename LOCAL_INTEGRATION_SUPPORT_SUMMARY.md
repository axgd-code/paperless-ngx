# Integration Module: Local URL Support Summary

## Question (French)
"Est-ce que l'intégration prend bien en compte que je peux avoir les solutions en local pour Documenso par exemple ?"

Translation: "Does the integration properly take into account that I can have local solutions for Documenso for example?"

## Answer: YES! ✅

The integration module **fully supports** both cloud-hosted AND self-hosted/local instances.

## Supported URL Formats

```
┌─────────────────────────────────────────────────────────────┐
│ SUPPORTED URL TYPES FOR INTEGRATIONS                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ✅ LOCALHOST                                                │
│    http://localhost:3000                                    │
│    http://localhost:8080                                    │
│    http://127.0.0.1:3000                                    │
│                                                             │
│ ✅ PRIVATE NETWORK                                          │
│    http://192.168.1.100:3000                                │
│    http://10.0.0.50:8080                                    │
│    http://172.16.0.10:3000                                  │
│                                                             │
│ ✅ DOCKER NETWORKS                                          │
│    http://documenso:3000                                    │
│    http://digiposte:8080                                    │
│    http://integration-service:3000                          │
│                                                             │
│ ✅ CUSTOM LOCAL DOMAINS                                     │
│    https://documenso.local                                  │
│    https://documenso.company.internal                       │
│    https://services.mycompany.local                         │
│                                                             │
│ ✅ CLOUD SERVICES                                           │
│    https://app.documenso.com                                │
│    https://api.digiposte.fr                                 │
│    https://any-cloud-service.com                            │
│                                                             │
│ ❌ NOT SUPPORTED                                            │
│    ftp://localhost:21        (wrong protocol)               │
│    not-a-url                 (invalid format)               │
│    //missing-scheme.com      (no http/https)                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Real-World Example: Self-Hosted Documenso

### Scenario
You're running Documenso locally alongside Paperless-ngx on the same machine or Docker network.

### Docker Compose Setup
```yaml
version: '3.8'
services:
  paperless:
    image: ghcr.io/paperless-ngx/paperless-ngx:latest
    ports:
      - "8000:8000"
    # ... config ...
    
  documenso:
    image: documenso/documenso:latest
    ports:
      - "3000:3000"
    # ... config ...
```

### Integration Configuration in Paperless
```
Name: My Local Documenso
Provider Type: Documenso (Signature)
API URL: http://documenso:3000      ← Docker service name
Credentials: {"api_key": "your-local-api-key"}
Active: ✓ Yes
```

### Result
✅ Paperless can send documents to your local Documenso instance
✅ No internet connection required
✅ All data stays on your infrastructure
✅ Fast local network communication

## Implementation Details

### URL Validation
The integration uses Django's URL validator which accepts:
- HTTP and HTTPS schemes
- Any valid hostname (localhost, IP, domain)
- Any valid port number
- No restrictions on private/local addresses

### Code Reference
```python
# src/documents/validators.py
def url_validator(value) -> None:
    """Validates HTTP or HTTPS URLs"""
    uri_validator(value, allowed_schemes={"http", "https"})
```

### Tests Added
12 automated tests verify local URL support:
- `test_integration_accepts_localhost_url()`
- `test_integration_accepts_loopback_ip()`
- `test_integration_accepts_private_network_ip()`
- `test_integration_accepts_docker_service_name()`
- `test_integration_accepts_custom_local_domain()`
- `test_integration_accepts_cloud_url()`
- And more...

## Documentation

### English
📄 `INTEGRATIONS_MODULE_GUIDE.md`
- Full documentation with local deployment section
- SSL/TLS considerations
- Network access requirements
- Docker examples

### French (Français)
📄 `SUPPORT_INTEGRATIONS_LOCALES.md`
- Documentation complète en français
- Exemples pratiques
- Configuration Docker Compose
- Cas d'usage

## Benefits of Local Instances

🔒 **Security**: Documents stay on your infrastructure
🚀 **Performance**: Faster local network communication
💰 **Cost**: No cloud subscription fees
🔧 **Control**: Full control over configuration
📡 **Offline**: Works without internet connection
🔐 **Compliance**: Meet data sovereignty requirements

## Conclusion

**YES, the integration module fully supports local/self-hosted instances!**

You can run Documenso, Digiposte, or any other integration provider locally:
- On the same machine (localhost)
- On your private network
- In Docker containers
- On custom domains
- In air-gapped environments

The support was already there, but now it's:
✅ Explicitly documented
✅ Tested with 12 automated tests
✅ Clarified in UI help text
✅ Explained with examples in both English and French
