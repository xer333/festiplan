# Diagnostic de l'architecture initiale

Analyse et reproduction réalisées le 22 octobre 2026, avant le remplacement des routes et services.

## Exploration et résultat initial

La page Swagger `/docs` et le schéma `/openapi.json` ont été consultés avec le client HTTP de test. Les opérations couvrent les festivals, artistes, scènes, concerts, le planning, la publication et les incidents. Il n'existe initialement aucune opération de dépublication.

Les six tests fournis passent. Trois tests de non-régression ajoutés avant correction échouent : le déplacement sur une scène occupée renvoie 200, la panne de notification renvoie 500 et le déplacement après publication renvoie 200.

Preuves conservées : [sortie pytest avant correction](tests_avant.txt) et [résultats HTTP et données relues](evidence_initiale.json). Les scénarios ont également été rejoués sur une copie de l'application initiale, avec une base temporaire indépendante. La base de travail n'a pas été réinitialisée.

## Responsabilités et dépendances observées

| Partie initiale | Responsabilité effective | Problème |
| --- | --- | --- |
| `app/api/*.py` | Requêtes, réponses, exceptions HTTP | Plusieurs routes interrogent SQLAlchemy et enregistrent directement des données |
| `app/schemas.py` | Validation Pydantic des types et formats | Capacité contrôlée uniquement à l'entrée HTTP ; espaces seuls acceptés pour un incident |
| `app/services/` | Création, déplacement, publication | Dépendances SQLAlchemy, modèle ORM et notifications concrètes créées dans les services |
| `app/repositories/` | Requêtes et création SQL | Chaque création décide de son propre commit ; aucune transaction applicative commune |
| `app/models.py` | Tables et relations SQLAlchemy | Modèles de stockage utilisés comme objets métier, sans invariants de domaine |
| `app/utils/email_sender.py` | Simulation d'envoi et de panne | Exception technique propagée après une modification déjà validée |
| `app/database.py`, `app/main.py` | Sessions, moteur, assemblage | Création des tables à l'import de l'application |

La dépendance principale est `route -> service concret -> repository concret / Session -> modèle ORM`. Certains parcours raccourcissent cette chaîne en allant directement de la route à SQLAlchemy. `SchedulingService` instancie lui-même son repository et son service de notification : remplacer la base ou simuler un expéditeur impose de modifier ou contourner le service.

Les règles de création sont concentrées dans `SchedulingService.create_concert`, mais la comparaison des horaires est aussi présente dans la route de déplacement. La capacité n'est protégée que par Pydantic. Le contrôle des conflits existe à la création, mais il n'est pas appelé au déplacement. Deux services proposent en outre une publication, sans revalidation complète des concerts.

Exemple concret : la route `create_incident` vérifie elle-même l'existence du concert, construit une ligne ORM et appelle `commit`. Cette responsabilité associe directement protocole HTTP, règle R10 et transaction SQL ; aucun cas d'utilisation réutilisable sans FastAPI n'existe.

## Reproduction des trois défauts

Préparation commune : créer un festival du 18 juin 2027 à 10 h au 20 juin à 23 h, deux artistes et deux scènes. Programmer le premier artiste sur Mainstage de 18 h à 19 h, le second de 20 h à 21 h le 18 juin. Les identifiants retournés par l'API doivent être réutilisés.

1. **Chevauchement** : envoyer `PATCH /concerts/{premier}/reschedule` avec `start_time=2027-06-18T20:15:00` et `end_time=2027-06-18T21:15:00`. Réponse initiale : 200. Relire le concert : les horaires qui chevauchent le second concert sont enregistrés. Le service ne relance ni la politique de conflits ni les autres contraintes de création.
2. **Notification après commit** : repartir de la préparation commune, activer `FESTIPLAN_FAIL_NOTIFICATIONS=true` avant le démarrage (ou modifier le paramètre dans le test), puis déplacer le premier concert de 16 h à 17 h. Réponse initiale : 500. `GET /concerts/{premier}` retourne pourtant `16:00:00` : le commit précède l'exception de l'expéditeur.
3. **Planning publié** : repartir de la préparation commune, envoyer `POST /festivals/{id}/publish`, puis déplacer le premier concert de 16 h à 17 h. Réponse initiale : 200. La consultation des festivals retourne toujours `published`, tandis que les nouveaux horaires ont été enregistrés.

Ces défauts rendent les reprises après erreur ambiguës, autorisent un planning incohérent et empêchent les tests métier de fonctionner indépendamment de la base. Ils justifient une politique unique de programmation, des états explicites, des ports injectables et une transaction maîtrisée par le cas d'utilisation.
