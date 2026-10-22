# FestiPlan

Dépôt GitHub : [xer333/festiplan](https://github.com/xer333/festiplan) (public).

API Python de gestion d'un festival fictif, refactorisée selon une architecture hexagonale et un modèle DDD. Les règles de programmation sont partagées entre création, déplacement et publication. Les trois défauts du sujet sont reproduits, corrigés et couverts par des tests.

## Installation sous Windows PowerShell

Prérequis : Python 3.11 ou plus récent. Depuis ce dossier :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Ces commandes n'exigent pas l'activation du venv ni une modification de la politique PowerShell.

Documentation Swagger : http://127.0.0.1:8000/docs ; schéma OpenAPI : http://127.0.0.1:8000/openapi.json.

Sous macOS ou Linux :

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m app.seed
python -m uvicorn app.main:app --reload
```

## Configuration et données de démonstration

La base SQLite `festiplan.db` est créée dans le dossier courant. Les valeurs par défaut figurent dans `.env.example` ; un fichier `.env` facultatif peut les remplacer :

```dotenv
FESTIPLAN_DATABASE_URL=sqlite:///./festiplan.db
FESTIPLAN_FAIL_NOTIFICATIONS=false
FESTIPLAN_APP_NAME=FestiPlan
```

`python -m app.seed` crée **Hellforge Open Air**, du 18 au 20 juin 2027, ses 4 scènes, 12 artistes et 14 concerts. Les données sont fictives. L'initialisation utilise les invariants du domaine et une transaction unique. Si la base contient déjà des données, la commande s'arrête sans les effacer.

Pour remplacer volontairement les données de développement :

```powershell
.\.venv\Scripts\python.exe -m app.seed --reset
```

L'option `--reset` efface les festivals, artistes, scènes, concerts et incidents de la base configurée. La base de travail n'est pas automatiquement initialisée par les tests.

## Fonctionnalités et contrat HTTP

- Festivals, artistes et équipements, scènes et capacités.
- Création, consultation, déplacement et annulation de concerts.
- Planning chronologique : `GET /concerts?festival_id=1` ou `GET /concerts/schedule/1`.
- Publication : `POST /festivals/1/publish`.
- Dépublication explicite : `POST /festivals/1/unpublish`.
- Déclaration et consultation des incidents.
- Notifications locales simulées : aucun email réel n'est envoyé.

Un planning publié refuse les modifications ordinaires de programmation et l'ajout de scènes. Il faut le dépublier, effectuer les changements puis le republier. Les incidents restent déclarables. Un concert annulé est exclu du planning et libère son créneau ; il reste consultable par identifiant.

Les conflits scène et artiste sont contrôlés à la création, au déplacement et à la publication. La disponibilité de l'artiste est vérifiée entre tous les festivals. Les créneaux contigus sont autorisés. Les dates avec un fuseau sont converties en UTC ; les dates sans fuseau sont interprétées comme UTC et les réponses conservent le format historique sans suffixe.

Codes d'erreur : **400** pour une règle métier invalide, **404** pour une référence absente, **409** pour une opération incompatible avec l'état et **422** pour un format de requête invalide.

Après un déplacement, une publication ou une dépublication enregistrés, la réponse contient `X-Notification-Status: sent` ou `failed`. Une panne d'envoi retourne **200**, avec le résultat métier enregistré et un journal d'erreur. Elle ne justifie pas de répéter la modification. Les corps de réponse existants sont conservés.

Pour simuler une panne, définir `FESTIPLAN_FAIL_NOTIFICATIONS=true` dans l'environnement ou `.env`, puis redémarrer l'API.

## Exécuter les tests

Dernière vérification : **92 tests réussis**. Le démarrage réel avec Uvicorn, Swagger et la consultation des 14 concerts ont aussi été vérifiés ; voir le [rapport de lancement](docs/verification_lancement.txt).

Suite complète :

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Domaine et application uniquement, sans FastAPI ni SQLite :

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/domain tests/application tests/test_architecture.py
```

Les trois non-régressions du sujet :

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/integration/test_regressions.py
```

Les tests d'intégration utilisent un moteur et une application de test explicitement injectés. Ils créent et suppriment leur propre base temporaire, même si l'application de travail a été importée avant pytest. Ils couvrent également le rollback SQL, les réservations simultanées et la commande d'initialisation. Les six tests initiaux sont conservés. Une dépréciation interne à Starlette/AnyIO peut être affichée avec les dépendances installées ; elle ne correspond pas à un échec de test.

## Organisation

```text
app/
  domain/          Entités, objets-valeurs, Planning, politique et événements
  application/     Cas d'utilisation, commandes et ports sortants
  adapters/        Persistance SQLAlchemy et notifications simulées
  api/             Contrôleurs FastAPI
  composition.py   Injection des dépendances concrètes
  models.py        Tables SQLAlchemy historiques
  database.py      Moteur et sessions
  schemas.py       Formats HTTP Pydantic
  main.py          Démarrage et traduction des erreurs
  seed.py          Données de démonstration
```

## Livrables du sujet

- [Diagnostic de l'architecture initiale et reproduction des défauts](docs/diagnostic_initial.md)
- [Note d'architecture : DDD, invariants R1-R10, ports, choix et limites](docs/architecture.md)
- [Rapport de seconde vérification](docs/verification_finale.md)
- [Diagramme UML de composants](docs/composants.svg) et [source PlantUML](docs/composants.puml)
- [Diagramme UML de séquence du déplacement](docs/sequence_deplacement.svg) et [source PlantUML](docs/sequence_deplacement.puml)
- [Tests avant correction](docs/tests_avant.txt), [preuves HTTP initiales](docs/evidence_initiale.json) et [tests après correction](docs/tests_apres.txt)

Les diagrammes sont aussi fournis en PNG. Java et PlantUML ne sont pas nécessaires pour lancer l'application. Pour régénérer les SVG avec un fichier `plantuml.jar` local :

```powershell
java '-Djava.awt.headless=true' -jar plantuml.jar -charset UTF-8 -tsvg 'docs/*.puml'
```

Le schéma SQL initial reste compatible. L'ancien fichier de configuration Alembic est fourni sans répertoire de migrations : aucune procédure de migration n'est revendiquée. Les limites de concurrence hors SQLite, de notification sans livraison garantie et de volumétrie sont détaillées dans la note d'architecture.
