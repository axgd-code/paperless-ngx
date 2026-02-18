# Support des Intégrations Locales / Auto-hébergées

## Réponse à la Question

**Oui, l'intégration prend parfaitement en compte les solutions locales !**

Le module d'intégration supporte **entièrement** les instances auto-hébergées et locales de services comme Documenso, en plus des services cloud. Vous pouvez utiliser n'importe quelle URL HTTP ou HTTPS valide.

## URLs Supportées

### ✅ Instances Locales (localhost)
```
http://localhost:3000
http://localhost:8080
http://127.0.0.1:3000
```

### ✅ Réseau Privé
```
http://192.168.1.100:3000
http://10.0.0.50:8080
```

### ✅ Docker / Conteneurs
```
http://documenso:3000
http://digiposte:8080
```
*(où 'documenso' est le nom du service Docker)*

### ✅ Domaines Locaux Personnalisés
```
https://documenso.local
https://documenso.monentreprise.local
https://services.internal.company.com
```

### ✅ Services Cloud
```
https://app.documenso.com
https://api.digiposte.fr
```

## Exemple Pratique : Documenso Auto-hébergé

### Configuration Docker Compose

```yaml
version: '3.8'
services:
  paperless:
    image: ghcr.io/paperless-ngx/paperless-ngx:latest
    ports:
      - "8000:8000"
    # ... autre configuration ...
    
  documenso:
    image: documenso/documenso:latest
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://...
      - NEXTAUTH_URL=http://localhost:3000
    # ... autre configuration ...
```

### Configuration de l'Intégration dans Paperless-ngx

1. **Naviguer** vers "Integrations" dans le menu latéral
2. **Cliquer** sur "Add Integration"
3. **Remplir** les champs :
   ```
   Nom : Mon Documenso Local
   Type de Fournisseur : Documenso (Signature)
   URL API : http://documenso:3000
   Identifiants : {"api_key": "votre-clé-api-locale"}
   ```
4. **Activer** l'intégration avec le toggle
5. **Tester** la connexion

## Considérations SSL/TLS pour Instances Locales

### Certificats Auto-signés

Si votre instance locale utilise un certificat SSL auto-signé, vous devrez peut-être configurer Python pour lui faire confiance :

```python
# Dans la configuration de Paperless-ngx
REQUESTS_CA_BUNDLE = '/chemin/vers/ca-bundle.crt'
```

### HTTP pour Développement Local

Pour les environnements de développement locaux, HTTP (non-chiffré) est acceptable :
```
URL API : http://localhost:3000
```

### Communication Docker

Si Paperless-ngx et votre service d'intégration sont tous deux dans Docker sur le même réseau :
```
URL API : http://documenso:3000
```
*(utilisez le nom du service Docker, pas localhost)*

## Exemples de Configuration

### Documenso Local (Localhost)
```json
{
  "name": "Documenso Local",
  "provider_type": 1,
  "api_url": "http://localhost:3000",
  "credentials": {
    "api_key": "votre-clé-api-locale"
  },
  "is_active": true
}
```

### Documenso sur Réseau Privé
```json
{
  "name": "Documenso Entreprise",
  "provider_type": 1,
  "api_url": "http://192.168.1.100:3000",
  "credentials": {
    "api_key": "votre-clé-api-interne"
  },
  "is_active": true
}
```

### Documenso Docker
```json
{
  "name": "Documenso Docker",
  "provider_type": 1,
  "api_url": "http://documenso:3000",
  "credentials": {
    "api_key": "votre-clé-api-docker"
  },
  "is_active": true
}
```

### Digiposte Auto-hébergé
```json
{
  "name": "Digiposte Local",
  "provider_type": 2,
  "api_url": "https://digiposte.monentreprise.local",
  "credentials": {
    "client_id": "votre-client-id",
    "client_secret": "votre-client-secret",
    "access_token": "votre-token",
    "refresh_token": "votre-refresh-token"
  },
  "is_active": true
}
```

## Exigences d'Accès Réseau

Assurez-vous que Paperless-ngx peut atteindre le service d'intégration :

1. **Même Hôte** : Utilisez `localhost` ou `127.0.0.1`
2. **Même Réseau** : Utilisez l'IP privée ou le nom d'hôte
3. **Docker** : Utilisez le nom du service ou configurez un réseau bridge
4. **Pare-feu** : Ouvrez les ports nécessaires (par exemple, 3000, 8080)

## Tests Automatisés

Le module inclut désormais des tests complets pour vérifier le support des URLs locales :
- ✅ URLs localhost
- ✅ Adresses IP loopback
- ✅ Adresses IP réseau privé
- ✅ Noms de service Docker
- ✅ Domaines locaux personnalisés
- ✅ URLs cloud
- ✅ Rejet des URLs invalides
- ✅ Rejet des schémas non-HTTP

## Cas d'Usage Supportés

1. ✅ **Développement Local** : Documenso sur localhost pendant le développement
2. ✅ **Auto-hébergement** : Instance Documenso sur la même machine que Paperless
3. ✅ **Déploiement Réseau Privé** : Services sur le réseau interne de l'entreprise
4. ✅ **Réseaux Docker/Conteneur** : Communication entre conteneurs
5. ✅ **Environnements Air-Gapped** : Déploiements sans accès internet
6. ✅ **Déploiements On-Premise** : Installations sur site
7. ✅ **Configurations Hybrides** : Mix de services cloud et locaux

## Avantages pour les Instances Locales

- 🔒 **Sécurité** : Vos documents restent sur votre infrastructure
- 🚀 **Performance** : Communication réseau local plus rapide
- 💰 **Coûts** : Pas de frais d'abonnement cloud
- 🔧 **Contrôle** : Contrôle total sur la configuration
- 📡 **Offline** : Fonctionne sans connexion internet
- 🔐 **Conformité** : Respect des exigences de souveraineté des données

## Conclusion

**Le module d'intégration est entièrement compatible avec les instances locales et auto-hébergées.** Vous pouvez déployer Documenso, Digiposte ou toute autre intégration sur votre propre infrastructure et Paperless-ngx se connectera sans problème.

Pour plus de détails, consultez le guide complet : `INTEGRATIONS_MODULE_GUIDE.md`
