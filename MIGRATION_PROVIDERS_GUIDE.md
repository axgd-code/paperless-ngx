# Guide de Migration: Providers Documenso et DigiPoste

## Vue d'Ensemble

Ce document décrit la migration complète des intégrations Documenso et DigiPoste vers la nouvelle architecture `BaseIntegrationProvider` avec une suite de tests robuste.

## 1. Architecture Provider Pattern

### Classe de Base Abstraite

Tous les providers héritent de `BaseIntegrationProvider` définie dans `src/documents/interfaces.py`:

```python
class BaseIntegrationProvider(ABC):
    @abstractmethod
    def push_document(self, document_id: int, params: Optional[Dict] = None) -> PushResult
    
    @abstractmethod
    def get_status(self, remote_id: str) -> StatusResult
    
    @abstractmethod
    def get_remote_url(self, remote_id: str) -> str
    
    @abstractmethod
    def delete_remote_document(self, remote_id: str) -> bool
    
    @abstractmethod
    def validate_credentials(self) -> bool
```

### Registry Pattern

Le `ProviderRegistry` permet l'enregistrement dynamique des providers:

```python
# Enregistrement automatique
ProviderRegistry.register("documenso", DocumensoProvider)
ProviderRegistry.register("digiposte", DigiPosteProvider)

# Utilisation
provider = ProviderRegistry.create_provider("documenso", integration)
```

## 2. Implémentation Documenso

### Authentification
- **Méthode**: API Key
- **Header**: `Authorization: Bearer {api_key}`

### Workflow de Signature

1. **Upload Document**: `POST /api/v1/documents`
   - Upload du PDF
   - Retourne `document_id`

2. **Ajouter Recipients**: `POST /api/v1/documents/{id}/recipients`
   - Ajoute les signataires
   - Role: SIGNER

3. **Envoyer pour Signature**: `POST /api/v1/documents/{id}/send`
   - Envoie les notifications
   - Change statut à PENDING

### Mapping des Statuts

| Statut Documenso | IntegrationStatus | Description |
|-----------------|-------------------|-------------|
| DRAFT | PENDING | Document en préparation |
| PENDING | PROCESSING | En attente de signatures |
| COMPLETED | SIGNED | Toutes signatures collectées |
| DECLINED | FAILED | Signature refusée |
| EXPIRED | FAILED | Document expiré |

### Exemple d'Utilisation

```python
from documents.providers.documenso import DocumensoProvider

provider = DocumensoProvider(integration)

# Envoyer pour signature
result = provider.push_document(
    document_id=123,
    params={
        "recipients": ["signer1@example.com", "signer2@example.com"],
        "subject": "Contrat à signer",
        "message": "Merci de signer ce document",
    }
)

# Vérifier le statut
status = provider.get_status(result.remote_id)
print(f"Status: {status.status.value}")  # "processing", "signed", etc.

# Obtenir l'URL
url = provider.get_remote_url(result.remote_id)
print(f"View at: {url}")
```

## 3. Implémentation DigiPoste

### Authentification
- **Méthode**: OAuth2 avec refresh automatique
- **Credentials**: `client_id`, `client_secret`, `access_token`, `refresh_token`

### Workflow d'Archivage

1. **Upload Document**: `POST /api/v3/documents`
   - Upload du PDF avec metadata
   - Spécifie folder, category, tags
   - Retourne `document_id`

2. **Refresh Token Automatique**
   - Si 401 détecté, refresh automatique
   - Mise à jour des credentials en DB

### Mapping des Statuts

| Statut DigiPoste | IntegrationStatus | Description |
|-----------------|-------------------|-------------|
| RECEIVED | ARCHIVED | Document reçu |
| PROCESSING | PROCESSING | En cours de traitement |
| ARCHIVED | ARCHIVED | Document archivé |
| DELETED | FAILED | Document supprimé |

### Exemple d'Utilisation

```python
from documents.providers.digiposte import DigiPosteProvider

provider = DigiPosteProvider(integration)

# Archiver
result = provider.push_document(
    document_id=123,
    params={
        "folder": "Factures",
        "category": "Finance",
        "tags": ["2024", "important"],
    }
)

# Vérifier le statut
status = provider.get_status(result.remote_id)
print(f"Status: {status.status.value}")  # "archived", "processing", etc.
```

## 4. Suite de Tests

### Structure des Tests

```
src/documents/tests/
├── mocks/
│   ├── __init__.py
│   └── provider_responses.py      # Fixtures JSON
└── test_provider_integrations.py   # Tests unitaires
```

### Utilisation des Mocks

Les tests utilisent `responses` pour intercepter les appels HTTP:

```python
@responses.activate
def test_push_document_success(self):
    responses.add(
        responses.POST,
        "https://api.documenso.com/api/v1/documents",
        json=DocumensoResponses.document_upload_success(),
        status=200,
    )
    
    result = self.provider.push_document(self.document.id)
    self.assertTrue(result.success)
```

### Catégories de Tests

1. **Validation Credentials**
   - Success, Failure, Missing keys
   - Token refresh (DigiPoste)

2. **Push Document**
   - Success nominal
   - Erreurs HTTP (401, 404, 500)
   - Document non trouvé

3. **Get Status**
   - Tous les statuts possibles
   - Document non trouvé
   - Erreurs réseau

4. **Delete Document**
   - Success
   - Document déjà supprimé

5. **Feature Toggle**
   - Integration active/inactive

6. **SubTests**
   - Logique commune entre providers
   - Vérification des types de retour

### Exécution des Tests

```bash
# Tous les tests d'intégration
python manage.py test documents.tests.test_provider_integrations

# Tests spécifiques
python manage.py test documents.tests.test_provider_integrations.TestDocumensoProvider
python manage.py test documents.tests.test_provider_integrations.TestDigiPosteProvider

# Avec verbose
python manage.py test documents.tests.test_provider_integrations -v 2

# Avec coverage
coverage run --source='documents' manage.py test documents.tests.test_provider_integrations
coverage report
```

## 5. Modèle DocumentIntegrationMetadata

### Schéma

```python
class DocumentIntegrationMetadata(models.Model):
    document = models.ForeignKey(Document)
    integration = models.ForeignKey(Integration)
    remote_id = models.CharField(max_length=255)
    status = models.CharField(max_length=50)
    remote_url = models.URLField(blank=True)
    metadata = models.JSONField(default=dict)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    last_synced = models.DateTimeField(null=True)
    
    class Meta:
        unique_together = ["document", "integration"]
```

### Utilisation

```python
# Créer metadata après push
metadata = DocumentIntegrationMetadata.objects.create(
    document=document,
    integration=integration,
    remote_id=result.remote_id,
    status=result.status.value,
    remote_url=provider.get_remote_url(result.remote_id),
    metadata=result.metadata,
)

# Mettre à jour le statut
status_result = provider.get_status(metadata.remote_id)
metadata.status = status_result.status.value
metadata.last_synced = timezone.now()
metadata.save()
```

## 6. Intégration avec Celery

### Tâche Mise à Jour

La tâche `send_document_to_integration` a été refactorisée:

```python
@shared_task(bind=True, base=PaperlessTask)
def send_document_to_integration(
    self,
    document_id: int,
    integration_id: int,
    params: Optional[Dict[str, Any]] = None,
):
    try:
        document = Document.objects.get(pk=document_id)
        integration = Integration.objects.get(pk=integration_id)
        
        # Vérifier que l'intégration est active
        if not integration.is_active:
            raise Exception("Integration is not active")
        
        # Créer le provider via Registry
        provider = ProviderRegistry.create_provider(
            integration.provider_type,
            integration,
        )
        
        # Envoyer le document
        result = provider.push_document(document_id, params)
        
        # Créer/mettre à jour metadata
        metadata, created = DocumentIntegrationMetadata.objects.update_or_create(
            document=document,
            integration=integration,
            defaults={
                "remote_id": result.remote_id,
                "status": result.status.value,
                "remote_url": provider.get_remote_url(result.remote_id),
                "metadata": result.metadata,
            },
        )
        
        logger.info(f"Document {document_id} sent to {integration.name}")
        
    except Exception as e:
        logger.error(f"Failed to send document: {e}")
        raise
```

### Tâche de Synchronisation

```python
@shared_task
def sync_integration_status(metadata_id: int):
    """Synchroniser le statut depuis la plateforme externe."""
    metadata = DocumentIntegrationMetadata.objects.get(pk=metadata_id)
    
    provider = ProviderRegistry.create_provider(
        metadata.integration.provider_type,
        metadata.integration,
    )
    
    result = provider.get_status(metadata.remote_id)
    
    metadata.status = result.status.value
    metadata.metadata.update(result.metadata)
    metadata.last_synced = timezone.now()
    metadata.save()
```

## 7. Ajout d'un Nouveau Provider

### Étape 1: Créer la Classe

Créer `src/documents/providers/monprovider.py`:

```python
from documents.interfaces import BaseIntegrationProvider, PushResult, StatusResult

class MonProvider(BaseIntegrationProvider):
    def __init__(self, integration):
        super().__init__(integration)
        self.api_url = integration.api_url
        # Initialiser credentials
    
    def validate_credentials(self) -> bool:
        # Tester les credentials
        pass
    
    def push_document(self, document_id, params=None) -> PushResult:
        # Envoyer le document
        pass
    
    def get_status(self, remote_id) -> StatusResult:
        # Récupérer le statut
        pass
    
    def get_remote_url(self, remote_id) -> str:
        # Construire l'URL
        pass
    
    def delete_remote_document(self, remote_id) -> bool:
        # Supprimer le document
        pass

# Enregistrement automatique
ProviderRegistry.register("monprovider", MonProvider)
```

### Étape 2: Importer dans `__init__.py`

```python
from documents.providers.monprovider import MonProvider

__all__ = [..., "MonProvider"]
```

### Étape 3: Créer les Mocks

Dans `tests/mocks/provider_responses.py`:

```python
class MonProviderResponses:
    @staticmethod
    def success_response():
        return {"id": "123", "status": "OK"}
```

### Étape 4: Créer les Tests

```python
class TestMonProvider(TestCase):
    @responses.activate
    def test_push_document(self):
        responses.add(...)
        result = provider.push_document(doc_id)
        self.assertTrue(result.success)
```

### Étape 5: Utiliser

```python
integration = Integration.objects.create(
    provider_type="monprovider",
    ...
)

provider = ProviderRegistry.create_provider("monprovider", integration)
result = provider.push_document(doc_id)
```

## 8. Gestion d'Erreurs

### Erreurs HTTP

```python
try:
    result = provider.push_document(doc_id)
except Exception as e:
    if "401" in str(e):
        # Credentials invalides
    elif "404" in str(e):
        # Ressource non trouvée
    elif "500" in str(e):
        # Erreur serveur
```

### Erreurs Réseau

```python
try:
    result = provider.get_status(remote_id)
except requests.exceptions.RequestException as e:
    logger.error(f"Network error: {e}")
    # Retry ou signaler l'erreur
```

### Token Refresh (OAuth2)

DigiPoste gère automatiquement le refresh:

```python
def _make_request(self, url, **kwargs):
    response = requests.get(url, **kwargs)
    
    if response.status_code == 401:
        # Token expiré, refresh automatique
        if self._refresh_access_token():
            # Retry avec nouveau token
            response = requests.get(url, **kwargs)
    
    return response
```

## 9. Monitoring et Logging

### Logs Structurés

```python
logger = logging.getLogger("paperless.integrations.documenso")

logger.info(f"Sending document {doc_id} to Documenso")
logger.error(f"Failed to send document: {error}")
logger.warning(f"Token expired, refreshing")
```

### Tracking avec PaperlessTask

```python
@shared_task(bind=True, base=PaperlessTask)
def send_document_to_integration(self, ...):
    self.update_state(
        state='PROGRESS',
        meta={'current': 1, 'total': 2, 'status': 'Uploading...'}
    )
```

## 10. Sécurité

### Stockage des Credentials

- Actuellement: JSONField en plaintext
- **Recommandé**: Chiffrement au repos (voir Phase 6 du plan initial)

### Permissions

```python
# Vérifier ownership
if integration.owner != request.user:
    raise PermissionDenied

# Vérifier activation
if not integration.is_active:
    raise Exception("Integration is not active")
```

### Validation des Entrées

```python
def push_document(self, document_id, params=None):
    params = params or {}
    
    # Valider les paramètres
    if "recipients" in params:
        for email in params["recipients"]:
            validate_email(email)
```

## 11. Performance

### Async Processing

- Utilisation de Celery pour toutes les opérations longues
- Pas de blocage de l'UI

### Caching

```python
# Cache des capabilities
@lru_cache(maxsize=128)
def get_provider_capabilities(provider_type: str):
    return PROVIDER_CAPABILITIES.get(provider_type)
```

### Batch Operations

```python
def sync_all_pending_documents():
    """Synchroniser tous les documents en attente."""
    pending = DocumentIntegrationMetadata.objects.filter(
        status=IntegrationStatus.PENDING.value
    )
    
    for metadata in pending:
        sync_integration_status.delay(metadata.id)
```

## 12. Conformité

### ✅ Typage Strict
- Type hints dans toutes les méthodes
- Dataclasses pour les résultats

### ✅ Open/Closed Principle
- Ajouter un provider = nouvelle classe uniquement
- Pas de modification du code existant

### ✅ Tests Isolés
- Pas d'appels réseau réels
- Utilisation de `responses` et `mock`

### ✅ Documentation
- Docstrings complets
- Exemples d'utilisation
- Guide de migration

## Conclusion

Cette migration apporte:

1. **Extensibilité**: Ajout facile de nouveaux providers
2. **Maintenabilité**: Code structuré et testé
3. **Fiabilité**: Tests complets avec mocks
4. **Performance**: Processing asynchrone
5. **Sécurité**: Validation et gestion d'erreurs
6. **Documentation**: Guides complets

Le système est prêt pour la production et l'ajout de nouveaux providers (Nextcloud, ownCloud, etc.).
