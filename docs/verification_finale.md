# Rapport de seconde vérification

Vérification effectuée le 22 octobre 2026 à partir des règles R1 à R10 et des livrables demandés dans le sujet.

## Corrections supplémentaires issues de la relecture

- **Agrégat Planning** : ses propres concerts sont systématiquement pris en compte dans les conflits et la publication, même si une liste externe est vide. L'agrégat refuse les enfants d'un autre festival, les identités dupliquées et la modification d'un concert qu'il ne contient pas. Sa collection est immuable.
- **Isolation des tests** : le moteur SQL et l'application de test sont créés explicitement. Une importation préalable de l'application ne peut plus faire pointer les tests vers la base de travail. Un test lance les trois non-régressions dans cette situation et compare le fichier de la base avant et après.
- **Dates extrêmes** : un dépassement lors de la conversion en UTC est traduit en erreur métier et en HTTP 400, sans erreur serveur ni écriture.
- **Réponses HTTP** : la lecture des festivals ne réapplique plus les restrictions propres au formulaire de création. Un objet valide créé par un cas d'utilisation sans HTTP peut être consulté normalement.
- **Contrôle d'architecture** : les imports relatifs sont aussi vérifiés, et le domaine ne peut pas dépendre de la couche application.

Sept tests reproduisaient les faiblesses principales avant ces corrections ; leur sortie est conservée dans [audit_avant.txt](audit_avant.txt). Des tests complémentaires protègent les invariants de l'agrégat et les dates limites à l'entrée HTTP.

## Résultats

| Contrôle | Résultat |
| --- | --- |
| Suite complète | 92 tests réussis : [sortie détaillée](tests_apres.txt) |
| Base de travail après les tests | Fichier strictement inchangé, comparaison SHA-256 |
| Dépendances installées | `python -m pip check` : aucune incompatibilité déclarée |
| Trois défauts initiaux | Reproduits avant correction, couverts par les non-régressions conservées |
| Règles R1 à R10 | Traçabilité et responsabilités vérifiées dans la [note d'architecture](architecture.md) |
| UML de composants et de séquence | Sources PlantUML, SVG et PNG présents ; rendus contrôlés |
| README et documentation | Installation, initialisation, lancement, tests, décisions et limites documentés |
| Archive livrable | [Extraction, tests, initialisation et démarrage HTTP vérifiés dans un dossier temporaire](verification_archive.txt) |

La vérification de l'archive utilise le même interpréteur et les dépendances installées, mais exécute exclusivement le code extrait. Le dossier extrait ne contient ni environnement virtuel ni base préexistante. Il crée ses propres données de démonstration puis démarre Uvicorn pour vérifier les routes HTTP.

Un avertissement de dépréciation interne à Starlette/AnyIO subsiste dans l'environnement installé. Il ne provoque aucun échec. Les limites de livraison des notifications sans outbox et de concurrence sur un moteur autre que SQLite restent explicitement documentées ; elles ne font pas partie des défauts à corriger imposés par le sujet.
