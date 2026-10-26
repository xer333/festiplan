# Prise en main de l’API avec PowerShell

Ces commandes supposent une base de démonstration fraîchement initialisée avec `python -m app.seed` et une API lancée à l’adresse `http://127.0.0.1:8000`. Elles modifient uniquement cette base de développement. Les identifiants sont récupérés dans les réponses de l’API.

## Consulter le festival et son planning

```powershell
$api = 'http://127.0.0.1:8000'
$festival = @(Invoke-RestMethod "$api/festivals")[0]
$planning = @(Invoke-RestMethod "$api/concerts?festival_id=$($festival.id)")
$concert = $planning[0]
$planning | Format-Table id, artist_id, stage_id, start_time, end_time, status
```

Les concerts sont classés par heure de début. Les concerts annulés sont exclus de cette liste et restent accessibles avec `GET /concerts/{id}`.

## Déplacer un concert et consulter le statut de notification

Le premier concert du jeu de démonstration peut être déplacé de 16 h à 17 h le 18 juin 2027.

```powershell
$deplacement = @{
    start_time = '2027-06-18T16:00:00'
    end_time = '2027-06-18T17:00:00'
} | ConvertTo-Json

$reponse = Invoke-WebRequest -UseBasicParsing -Method Patch `
    -Uri "$api/concerts/$($concert.id)/reschedule" `
    -ContentType 'application/json' -Body $deplacement

$reponse.StatusCode
$reponse.Headers['X-Notification-Status']
$reponse.Content | ConvertFrom-Json
```

Une réponse 200 confirme le déplacement enregistré. L’en-tête `X-Notification-Status` vaut `sent` ou `failed`. Une panne de notification ne remet pas en cause le déplacement ; il suffit de relire le concert pour confirmer ses horaires.

## Publier puis rouvrir le planning

```powershell
Invoke-RestMethod -Method Post -Uri "$api/festivals/$($festival.id)/publish"
```

Le festival passe à l’état `published`. À ce stade, la commande de déplacement précédente renverrait 409, comme toute modification ordinaire de programmation. Pour autoriser de nouveaux changements :

```powershell
Invoke-RestMethod -Method Post -Uri "$api/festivals/$($festival.id)/unpublish"
```

Le planning retourne à l’état `preparation`. Il pourra être republié après modification et revalidation de ses concerts.

## Déclarer et consulter un incident

La déclaration reste disponible même lorsque le planning est publié.

```powershell
$incident = @{
    concert_id = $concert.id
    description = 'Coupure temporaire du son pendant le concert'
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "$api/incidents" `
    -ContentType 'application/json' -Body $incident

Invoke-RestMethod "$api/incidents?concert_id=$($concert.id)"
```

La description doit être non vide et le concert doit exister. Si `occurred_at` est omis, l’API renseigne l’instant courant en UTC.

## Interpréter un refus

| Code | Signification |
| --- | --- |
| 400 | Règle métier non respectée : chevauchement, période ou équipements incompatibles, par exemple |
| 404 | Festival, artiste, scène ou concert introuvable |
| 409 | Action incompatible avec l’état du planning ou du concert |
| 422 | Format de requête invalide |

Swagger reste accessible sur `/docs` pour explorer l’ensemble des opérations et leurs formats.
