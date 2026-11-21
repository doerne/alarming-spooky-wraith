# Rückkanal API: Agent meldet Issue und Status – Design (kurz)

Stand: 2026-11-21 · Teil 3 von 4

## Absicht
Ein Agent, der aus dem Export Issues anlegt und abarbeitet, meldet Issue-URL und Fortschritt an
CVE-Radar zurück – adressiert wie der Marker über Anwendung + Advisory.

## Entscheidungen des Nutzers
- „behoben“ vom Agenten gilt **vorläufig** (Herkunft „gemeldet“). Nachweis ist die nächste
  SBOM-Version derselben SBOM: ist die Komponente darin unverändert enthalten → automatisch
  wieder „offen“ mit Kommentar; sonst bleibt „behoben“. Manuelle Komponenten: Meldung bleibt.
- Vorschlag für Endpoint/Alias/Anleitung/ohne Anmeldung freigegeben.

## Ansätze
| | Ansatz | Abwägung |
|---|---|---|
| **A (gewählt)** | Meldung vorläufig, SBOM-Upload prüft nach | Kein Flackern durch tägliche Scans; Nachweis = ausgeliefertes Artefakt |
| B | Meldung gilt, nächster Scan-Treffer öffnet wieder | Öffnet täglich neu, solange das Release fehlt |

## Design
- `PATCH /api/applications/{application_id}/cves/{advisory_id}` Body (camelCase, alles optional,
  mindestens ein Feld): `status` (FindingStatus), `issueUrl` (http/https, ≤ 500), `comment`
  (≤ 2 000, wird mit Leerzeile **angehängt**). Wirkt auf alle Treffer der Anwendung zu dieser
  Advisory. Antwort: `{ advisoryId, updated }`.
- Unbekannte Advisory-ID → über `advisory_alias` auflösen (alte Marker). Keine Treffer → 404.
- Finding-Felder neu: `issue_url: str`, `resolved_by: ResolutionSource | None`
  (`sbom` | `reported`). SBOM-Auflösung setzt `sbom`.
- Status `behoben` per API: `resolved_at` = jetzt, `resolved_by = reported`,
  `resolution` = „Als behoben gemeldet (Issue <url>)“ bzw. „Als behoben gemeldet“.
  Anderer Status per API: `resolved_at/by/resolution` werden geleert.
- **Nachweis beim SBOM-Upload:** für *behaltene* Komponenten (gleicher Name/Ökosystem/Version):
  Treffer mit `behoben` + `reported` → `offen`, Auflösung geleert, Kommentar
  „Wieder offen: <name> <version> weiterhin in SBOM <sbom> <label> enthalten.“ angehängt.
- Export: Anleitung um `curl`-Beispiele ergänzt (nach Anlegen `issueUrl`, nach Schließen
  `status: "behoben"`); zeigt eine vorhandene Issue-URL im Issue-Text.

## Nicht-Ziele
Anmeldung/Token (wie übrige API), UI-Bearbeitung des Status, GitHub abfragen (Teil 4).

## Tests
Use Case (Status/URL/Kommentar, Alias-Auflösung, 404, behoben setzt/anderer Status leert),
Upload-Nachweis (wieder offen vs. bleibt), API (422 bei leerem Body/ungültiger URL, 404),
Export (Anleitung, Issue-URL), Repository/Migration.
