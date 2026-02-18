# Provider Pattern Implementation Guide

## Vue d'ensemble

Ce document décrit l'implémentation complète du Provider Pattern pour le système d'intégrations de Paperless-ngx. Cette architecture permet d'ajouter facilement de nouvelles plateformes tierces (signature, cloud, coffre-fort) de manière modulaire.

## Architecture Globale

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Angular)                      │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  IntegrationProviderCapabilities                       │  │
│  │  - Définit ce que chaque provider peut faire          │  │
│  │  - Labels dynamiques pour actions                     │  │
│  └───────────────────────────────────────────────────────┘  │
│                          ▼                                    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  DocumentIntegrationMetadataService                    │  │
│  │  - API calls pour métadonnées                         │  │
│  │  - Sync status depuis platforms                       │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼ REST API
┌─────────────────────────────────────────────────────────────┐
│                      Backend (Django)                        │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Integration Model                                     │  │
│  │  - Configuration (name, api_url, credentials)         │  │
│  │  - Feature toggle (is_active)                         │  │
│  └───────────────────────────────────────────────────────┘  │
│                          │                                    │
│                          ▼                                    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  ProviderRegistry                                      │  │
│  │  - Factory pattern                                     │  │
│  │  - Enregistrement dynamique des providers             │  │
│  └───────────────────────────────────────────────────────┘  │
│                          │                                    │
│                          ▼                                    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  BaseIntegrationProvider (Abstract)                    │  │
│  │  - push_document()                                     │  │
│  │  - get_status()                                        │  │
│  │  - get_remote_url()                                    │  │
│  │  - delete_remote_document()                            │  │
│  └───────────────────────────────────────────────────────┘  │
│                          │                                    │
│         ┌────────────────┼────────────────┐                  │
│         ▼                ▼                ▼                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ DocuSeal    │  │ Documenso   │  │ Digiposte   │         │
│  │ Provider    │  │ Provider    │  │ Provider    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  DocumentIntegrationMetadata Model                     │  │
│  │  - Tracking: remote_id, status, remote_url           │  │
│  │  - Timestamps: created, updated, last_synced         │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Celery Tasks                                          │  │
│  │  - send_document_to_integration()                     │  │
│  │  - sync_integration_status()                          │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼ HTTP/API
┌─────────────────────────────────────────────────────────────┐
│                  External Platforms                          │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ DocuSeal    │  │ Documenso   │  │ Digiposte   │         │
│  │ API         │  │ API         │  │ API         │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

## Composants Principaux

### 1. Backend - Interface Abstraite

**Fichier**: `src/documents/interfaces.py`

```python
class BaseIntegrationProvider(ABC):
    """Interface abstraite que tous les providers doivent implémenter"""
    
    @abstractmethod
    def push_document(self, document_id: int, params: dict) -> PushResult:
        """Envoyer un document à la plateforme"""
        pass
    
    @abstractmethod
    def get_status(self, remote_id: str) -> StatusResult:
        """Récupérer le statut actuel"""
        pass
    
    @abstractmethod
    def get_remote_url(self, remote_id: str) -> str:
        """Obtenir l'URL directe"""
        pass
    
    def delete_remote_document(self, remote_id: str) -> bool:
        """Supprimer (optionnel)"""
        return False
```

**Classes de Données:**
- `IntegrationStatus`: Enum des statuts (pending, signed, archived, etc.)
- `PushResult`: Résultat de push avec remote_id, remote_url, status
- `StatusResult`: Résultat de get_status avec status, updated_at, metadata

**Registry:**
- `ProviderRegistry`: Factory pattern pour créer les providers dynamiquement
- `register()`: Enregistrer un nouveau provider
- `create_provider()`: Instancier un provider par son type

### 2. Backend - Implémentation DocuSeal

**Fichier**: `src/documents/providers/docuseal.py`

```python
class DocuSealProvider(BaseIntegrationProvider):
    """Implémentation pour DocuSeal (open-source signature platform)"""
    
    def __init__(self, integration):
        super().__init__(integration)
        self.api_key = self.credentials.get("api_key")
    
    def push_document(self, document_id, params):
        # Upload document pour signature
        # Retourne PushResult avec submission_id
        pass
    
    def get_status(self, remote_id):
        # Check signature status
        # Map DocuSeal status → IntegrationStatus
        pass
```

**Enregistrement automatique:**
```python
ProviderRegistry.register("docuseal", DocuSealProvider)
```

### 3. Backend - Modèles Django

**DocumentIntegrationMetadata:**
```python
class DocumentIntegrationMetadata(models.Model):
    document = ForeignKey(Document)
    integration = ForeignKey(Integration)
    remote_id = CharField(max_length=512)
    status = CharField(max_length=50, default="pending")
    remote_url = URLField(null=True)
    metadata = JSONField(default=dict)  # Provider-specific data
    created = DateTimeField()
    updated = DateTimeField(auto_now=True)
    last_synced = DateTimeField(null=True)
    
    class Meta:
        unique_together = [("document", "integration")]
```

### 4. Backend - Tâches Celery

**send_document_to_integration:**
```python
@shared_task
def send_document_to_integration(document_id, integration_id, params=None):
    # 1. Récupérer document et integration
    # 2. Créer provider via Registry
    # 3. Appeler provider.push_document()
    # 4. Créer/mettre à jour DocumentIntegrationMetadata
    # 5. Retourner résultat
    pass
```

**sync_integration_status:**
```python
@shared_task
def sync_integration_status(metadata_id):
    # 1. Récupérer metadata
    # 2. Créer provider
    # 3. Appeler provider.get_status()
    # 4. Mettre à jour metadata.status et last_synced
    pass
```

### 5. Frontend - Interfaces TypeScript

**Fichier**: `src-ui/src/app/data/integration.ts`

```typescript
export interface IntegrationProviderCapabilities {
  canPush: boolean
  canGetStatus: boolean
  canGetRemoteUrl: boolean
  canDelete: boolean
  pushActionLabel?: string     // "Send for Signature"
  statusActionLabel?: string    // "Check Status"
  iconName?: string             // "pen"
}

export const PROVIDER_CAPABILITIES: Record<ProviderType, IntegrationProviderCapabilities> = {
  [ProviderType.Documenso]: {
    canPush: true,
    canGetStatus: true,
    canGetRemoteUrl: true,
    canDelete: false,
    pushActionLabel: $localize`Send for Signature`,
    statusActionLabel: $localize`Check Signature Status`,
    iconName: 'pen',
  },
  // ...
}
```

### 6. Frontend - Services

**DocumentIntegrationMetadataService:**
```typescript
@Injectable()
export class DocumentIntegrationMetadataService {
  listAll(): Observable<Results<DocumentIntegrationMetadata>>
  get(id): Observable<DocumentIntegrationMetadata>
  getByDocument(docId): Observable<Results<DocumentIntegrationMetadata>>
  create(metadata): Observable<DocumentIntegrationMetadata>
  update(metadata): Observable<DocumentIntegrationMetadata>
  delete(metadata): Observable<any>
  syncStatus(metadataId): Observable<SyncStatusResult>
}
```

## Ajouter un Nouveau Provider

### Étape 1: Backend - Créer le Provider

Créer `src/documents/providers/mon_provider.py`:

```python
from documents.interfaces import BaseIntegrationProvider, PushResult, StatusResult, IntegrationStatus
from documents.providers import ProviderRegistry

class MonProvider(BaseIntegrationProvider):
    def __init__(self, integration):
        super().__init__(integration)
        # Initialiser credentials, API client, etc.
    
    def push_document(self, document_id, params):
        # Implémenter l'upload
        return PushResult(
            success=True,
            remote_id="...",
            remote_url="...",
            status=IntegrationStatus.PENDING,
        )
    
    def get_status(self, remote_id):
        # Implémenter le check de statut
        return StatusResult(
            status=IntegrationStatus.COMPLETED,
            updated_at=datetime.now(),
        )
    
    def get_remote_url(self, remote_id):
        return f"{self.api_url}/documents/{remote_id}"

# Enregistrer le provider
ProviderRegistry.register("mon_provider", MonProvider)
```

### Étape 2: Backend - Importer le Provider

Dans `src/documents/providers/__init__.py`:

```python
from documents.providers.docuseal import DocuSealProvider
from documents.providers.mon_provider import MonProvider

__all__ = ["DocuSealProvider", "MonProvider"]
```

### Étape 3: Backend - Mapper le Provider Type

Dans `src/documents/tasks.py`, ajouter au mapping:

```python
provider_type_map = {
    Integration.ProviderType.DOCUMENSO: "docuseal",
    Integration.ProviderType.DIGIPOSTE: "docuseal",
    Integration.ProviderType.MON_TYPE: "mon_provider",  # ← Ajouter ici
    Integration.ProviderType.CUSTOM: "docuseal",
}
```

### Étape 4: Frontend - Définir les Capacités

Dans `src-ui/src/app/data/integration.ts`:

```typescript
export const PROVIDER_CAPABILITIES: Record<ProviderType, IntegrationProviderCapabilities> = {
  [ProviderType.MonType]: {
    canPush: true,
    canGetStatus: true,
    canGetRemoteUrl: true,
    canDelete: false,
    pushActionLabel: $localize`Envoyer vers Mon Provider`,
    statusActionLabel: $localize`Vérifier le statut`,
    iconName: 'cloud-upload',
  },
  // ...
}
```

### Étape 5: C'est Tout!

✅ Aucune modification dans les vues, tâches, ou UI
✅ Le provider est automatiquement utilisé selon la configuration
✅ Les actions UI apparaissent selon les capacités définies

## Workflow Complet

### 1. Configuration (Admin)

1. Admin crée une Integration dans Django Admin ou via UI
2. Remplit: name, provider_type, api_url, credentials
3. Active avec is_active=True

### 2. Envoi d'un Document

```python
# Via UI ou API
result = send_document_to_integration.delay(
    document_id=123,
    integration_id=1,
    params={"recipients": ["user@example.com"]}
)
```

**Workflow interne:**
1. Tâche Celery démarre
2. Registry crée le provider: `ProviderRegistry.create_provider("docuseal", integration)`
3. Provider pousse: `result = provider.push_document(123, params)`
4. Metadata créée: `DocumentIntegrationMetadata.objects.create(...)`
5. Retour du résultat

### 3. Vérification du Statut

```python
# Via UI ou tâche périodique
sync_integration_status.delay(metadata_id=456)
```

**Workflow interne:**
1. Récupère metadata depuis DB
2. Crée provider
3. Appelle: `status = provider.get_status(metadata.remote_id)`
4. Met à jour: `metadata.status = status.status.value`

### 4. Affichage UI

```typescript
// Component récupère les métadonnées
metadataService.getByDocument(documentId).subscribe(results => {
  results.results.forEach(metadata => {
    // Afficher badge avec statut
    const badgeClass = getStatusBadgeClass(metadata.status)
    const label = getStatusLabel(metadata.status)
    
    // Afficher actions selon capabilities
    const capabilities = getProviderCapabilities(metadata.provider_type)
    if (capabilities.canGetRemoteUrl && metadata.remote_url) {
      // Afficher bouton "Open External"
    }
  })
})
```

## Tests

### Backend

```python
# tests/test_providers.py
def test_docuseal_provider():
    integration = Integration.objects.create(
        name="Test DocuSeal",
        provider_type=Integration.ProviderType.DOCUMENSO,
        api_url="http://localhost:3000",
        credentials={"api_key": "test_key"},
    )
    
    provider = ProviderRegistry.create_provider("docuseal", integration)
    assert provider is not None
    
    # Mock API calls
    with patch('requests.post') as mock_post:
        mock_post.return_value.json.return_value = {"id": "sub_123"}
        result = provider.push_document(1, {"recipients": ["test@example.com"]})
        
        assert result.success
        assert result.remote_id == "sub_123"
```

### Frontend

```typescript
// integration.service.spec.ts
it('should get provider capabilities', () => {
  const capabilities = getProviderCapabilities(ProviderType.Documenso)
  expect(capabilities.canPush).toBe(true)
  expect(capabilities.pushActionLabel).toBeDefined()
})
```

## Sécurité

1. **Credentials**: Stockées dans JSONField (à chiffrer avec django-encrypted-fields)
2. **Permissions**: Vérifiées au niveau de l'Integration model (owner, permissions)
3. **API Keys**: Ne jamais exposer dans les logs
4. **Validation**: URL et credentials validées avant utilisation

## Performance

1. **Celery**: Toutes les opérations longues sont asynchrones
2. **Indexes**: DB indexes sur (document, integration), remote_id, status
3. **Caching**: Capabilities mappées en constante (pas de DB query)
4. **Batch**: sync_integration_status peut être schedulée en batch

## Monitoring

1. **Logs**: `logger = logging.getLogger("paperless.integrations")`
2. **PaperlessTask**: Toutes les tâches trackées dans la DB
3. **Metadata**: Timestamps (created, updated, last_synced) pour audit

## Migration depuis Ancien Code

Si vous aviez du code hardcodé:

```python
# Ancien code ❌
if integration.provider_type == Integration.ProviderType.DOCUMENSO:
    # Code spécifique Documenso
    send_to_documenso(document)
elif integration.provider_type == Integration.ProviderType.DIGIPOSTE:
    # Code spécifique Digiposte
    send_to_digiposte(document)
```

```python
# Nouveau code ✅
provider = ProviderRegistry.create_provider(provider_type, integration)
result = provider.push_document(document_id, params)
```

## Conclusion

Cette architecture Provider Pattern offre:

✅ **Extensibilité**: Ajouter providers sans modifier le code existant
✅ **Maintenabilité**: Logique isolée par provider
✅ **Testabilité**: Chaque provider testé indépendamment
✅ **Type Safety**: Type hints Python + TypeScript interfaces
✅ **UI Dynamique**: Actions apparaissent selon capabilities
✅ **i18n**: Tous les labels internationalisés
✅ **Open/Closed Principle**: Open à extension, fermé à modification

Le système est prêt pour l'ajout de nouveaux providers (Documenso réel, Digiposte, SignNow, Adobe Sign, etc.) sans impact sur le code existant.
