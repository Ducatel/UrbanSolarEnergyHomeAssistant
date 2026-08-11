# AGENTS.md - Urban Solar Home Assistant Integration

## Contexte du projet

Ce dépôt contient une **intégration personnalisée Home Assistant** pour récupérer et afficher les données de revente de production photovoltaïque depuis **Urban Solar Energy**. L'intégration permet aux utilisateurs de suivre :

- **Production totale** (kWh)
- **Cagnotte actuelle** (€) - calculée à partir des volumes non facturés
- **Valeur estimée totale** (€)
- **Production du mois** (kWh) avec détail mensuel
- **Prix d'achat actuel** (€/kWh)

Les données sont **rafraîchies toutes les 6 heures** par défaut.

---

## Architecture du composant

### Structure des fichiers

```
custom_components/urban_solar/
├── __init__.py          # Initialisation de l'intégration
├── api.py              # Client HTTP pour l'API Urban Solar (GraphQL)
├── config_flow.py      # Flux de configuration (saisie des identifiants)
├── const.py            # Constantes (DOMAIN, UPDATE_INTERVAL, etc.)
├── coordinator.py      # Coordonnateur de mise à jour des données
├── sensor.py           # Définition des capteurs (entités Home Assistant)
├── manifest.json       # Métadonnées de l'intégration
└── strings.json        # Textes localisés (FR)
```

### Flux de données

1. **Configuration** (`config_flow.py`)
   - Saisie de l'email, mot de passe et **PDL** (Point de Livraison)
   - Validation des identifiants via `UrbanSolarClient._async_login()`
   - Création d'une entrée de configuration unique par PDL

2. **API Urban Solar** (`api.py`)
   - **Endpoint** : `https://espace-client.urbansolar.energy/api`
   - **Authentification** : Basic Auth (email:password) via `/login`
   - **Requête GraphQL** : Récupère les index d'injection et les tarifs BMS
   - **Données retournées** :
     - `getInjectionIndexes` : Production quotidienne en Wh
     - `getBMSPricing` : Tarifs d'achat par période
     - `getBMSInjectionFromLastYear` : Volumes non facturés (cagnotte)

3. **Coordonnateur** (`coordinator.py`)
   - Centralise les appels API pour toutes les entités
   - Gère les erreurs (authentification, timeout, etc.)
   - Intervalle de rafraîchissement : **6 heures** (`UPDATE_INTERVAL`)

4. **Capteurs** (`sensor.py`)
   - 5 entités exposées dans Home Assistant :
     - `sensor.urban_solar_<pdl>_total_production`
     - `sensor.urban_solar_<pdl>_wallet`
     - `sensor.urban_solar_<pdl>_estimated_value`
     - `sensor.urban_solar_<pdl>_current_month_production`
     - `sensor.urban_solar_<pdl>_current_price`
   - Le capteur `current_month_production` expose un attribut `monthly` avec le détail par mois.

---

## Développement

### Environnement (Dev Container)

- **Image** : `mcr.microsoft.com/devcontainers/python:3.14`
- **Ports** : 8123 (Home Assistant) exposé automatiquement
- **Extensions VS Code** :
  - `ms-python.python`
  - `ms-python.vscode-pylance`
  - `ms-python.debugpy`
- **Script post-création** : `.devcontainer/setup.sh` (à vérifier/exécuter)

### Dépendances

- **Python** : 3.14 (via Dev Container)
- **Bibliothèques** :
  - `aiohttp` (requêtes HTTP asynchrones)
  - `homeassistant-api` (pour le développement local)
  - Voir `requirements.txt` et `requirements_test.txt`

### Workflow de développement

1. **Modification du code**
   - Les fichiers sous `custom_components/urban_solar_energy/` sont **automatiquement chargés** par Home Assistant en mode développement.
   - Pas besoin de redémarrer HA pour les changements de code (sauf pour `manifest.json`).

2. **Validation**
   - Vérifier que les capteurs apparaissent dans **Paramètres > Appareils et services**.
   - Consulter les logs HA pour les erreurs 

3. **Débogage**
   - Activer le logging en debug dans `configuration.yaml` :
     ```yaml
     logger:
       default: info
       logs:
         custom_components.urban_solar: debug
     ```

---

## Bonnes pratiques

### Code

- **Style** : Suivre les conventions [Home Assistant](https://developers.home-assistant.io/docs/dev/1000_best_practices/) :
  - Noms de classes en `PascalCase` (ex: `UrbanSolarClient`)
  - Noms de méthodes en `snake_case` (ex: `async_fetch`)
  - Docstrings pour toutes les classes/méthodes publiques
  - Type hints obligatoires (`from __future__ import annotations`)

- **Gestion des erreurs** :
  - Utiliser les exceptions dédiées (`UrbanSolarApiError`, `UrbanSolarAuthenticationError`)
  - Ne **jamais** exposer les identifiants dans les logs ou erreurs

- **Performances** :
  - Limiter les appels API (1 appel toutes les 6h par défaut)
  - Utiliser le coordonnateur pour partager les données entre entités

### Sécurité

- **Identifiants** :
  - Stockés dans le **config entry** de Home Assistant (chiffré)
  - Jamais écrits dans les logs ou le code
  - Transmis en **Basic Auth** (HTTPS obligatoire)

- **API Urban Solar** :
  - Toujours utiliser `timeout=aiohttp.ClientTimeout(total=30)`
  - Gérer les erreurs 401/403 (authentification) et 5xx (serveur)

### Tests

Le projet inclut maintenant une **suite complète de tests unitaires** (94 tests) pour valider le fonctionnement de l'intégration.

#### Structure des tests

```
tests/
├── __init__.py              # Initialisation du package de tests
├── conftest.py              # Configuration pytest et fixtures globales
├── README.md                # Documentation des tests
├── pytest.ini               # Configuration pytest
├── fixtures/                # Données de test mockées
│   ├── urban_solar_response.json    # Réponse API complète
│   ├── urban_solar_empty_response.json  # Réponse vide
│   └── urban_solar_error_response.json  # Réponse d'erreur
├── test_api.py              # 38 tests pour UrbanSolarClient
├── test_coordinator.py     # 16 tests pour le coordinator
├── test_sensor.py           # 32 tests pour les capteurs
└── test_init.py             # 8 tests pour l'initialisation
```

#### Exécution des tests

1. **Installer les dépendances de test** :
   ```bash
   pip install -r requirements_test.txt
   ```

2. **Exécuter tous les tests** :
   ```bash
   pytest
   ```

3. **Exécuter avec couverture de code** :
   ```bash
   pytest --cov=custom_components/urban_solar_energy --cov-report=term-missing
   ```

4. **Exécuter des tests spécifiques** :
   ```bash
   # Un module spécifique
   pytest tests/test_api.py
   
   # Une classe spécifique
   pytest tests/test_api.py::TestUrbanSolarClientInitialization
   
   # Un test spécifique
   pytest tests/test_api.py::TestUrbanSolarClientInitialization::test_init_creates_unique_session_id
   ```

#### Couverture des tests

- **API Client** : Initialisation, headers, calcul des prix, agrégation des données, gestion des erreurs
- **Coordinator** : Initialisation, mise à jour des données, gestion des erreurs, propriétés
- **Sensors** : Descriptions, initialisation, valeurs natives, attributs supplémentaires, héritage
- **Integration** : Setup, unload, forwarding des plateformes

#### Bonnes pratiques pour les tests

- Utiliser des **mocks** pour les dépendances externes (API, Home Assistant)
- Tester à la fois les **cas de succès** et les **cas d'erreur**
- Garder les tests **indépendants** les uns des autres
- Utiliser des **fixtures** pour les données de test réutilisables

---

## Déploiement

### Pour usage personnel

1. Copier le dossier `custom_components/urban_solar_energy/` dans le dossier `custom_components/` de votre installation Home Assistant.
2. Redémarrer Home Assistant.
3. Ajouter l'intégration via **Paramètres > Appareils et services > Ajouter une intégration > Urban Solar**.

### Pour publication HACS

1. **Créer un dépôt GitHub** avec ce code.
2. **Configurer HACS** :
   - Ajouter le dépôt comme **Custom Repository** (type: Integration)
   - URL : `https://github.com/votre_utilisateur/UrbanSolarHomeAssistant`
3. **Mettre à jour `manifest.json`** :
   - Vérifier `documentation` et `issue_tracker` pointent vers votre dépôt
   - Incrémenter `version` à chaque release
4. **Soumettre à HACS** : Ouvrir une PR sur [hacs/integration](https://github.com/hacs/integration) pour une inclusion officielle.

---

## Problèmes connus / Limitations

1. **Données historiques** :
   - L'API Urban Solar ne fournit des données qu'à partir du **1er janvier 2025** (`FIRST_DATA_DATE` dans `api.py`).
   - Les données avant cette date ne seront pas incluses.

2. **Cagnotte vs. Valeur estimée** :
   - La **cagnotte** (`wallet_eur`) est calculée par Urban Solar à partir des volumes **non facturés**.
   - La **valeur estimée totale** (`estimated_value`) est calculée localement à partir de tous les index d'injection et des tarifs BMS.
   - Ces deux valeurs peuvent différer légèrement.

3. **Fréquence de rafraîchissement** :
   - Les données sont mises à jour toutes les 6 heures par défaut.
   - Pour un rafraîchissement plus fréquent, modifier `UPDATE_INTERVAL` dans `const.py` (attention aux limites de l'API).

4. **Multi-PDL** :
   - Actuellement, une seule entrée de configuration par PDL est supportée.
   - Pour gérer plusieurs PDL, il faudrait étendre `config_flow.py` pour permettre plusieurs entrées.

---

## Ressources utiles

- [Documentation Développeurs Home Assistant](https://developers.home-assistant.io/)
- [Guide des Intégrations Personnalisées](https://developers.home-assistant.io/docs/creating_integration_code/)
- [API GraphQL Urban Solar](https://espace-client.urbansolar.energy/api/graphql) (nécessite authentification)
- [Forum Home Assistant France](https://forum.hacf.fr/)

---

## Contacts

- **Auteur** : David Ducatel (à adapter selon ton nom GitHub)
- **Dépôt** : [github.com/davidducatel/UrbanSolarHomeAssistant](https://github.com/davidducatel/UrbanSolarHomeAssistant)
- **Issues** : Utiliser le tracker GitHub pour signaler les bugs ou demander des fonctionnalités.
