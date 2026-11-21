# Rückkanal SBOM: Treffer als „behoben“ markieren – Design (kurz)

Stand: 2026-11-21 · Teil 2 von 4 (nach Export und Alias-Zusammenführung)

## Absicht
Verschwindet eine betroffene Komponente mit einer neuen SBOM-Version oder bekommt sie eine
neue Version, soll ihr Treffer nicht gelöscht, sondern „behoben“ werden – Grundlage dafür,
dass Issues später automatisch geschlossen werden.

## Entscheidungen des Nutzers
- **Erst der nächste Scan entscheidet**, nicht der Upload (Upgrade ohne Fix darf kein Issue
  schließen).
- Ansatz **A**: ausgebaute Komponenten bleiben erhalten.
- Status beim Auflösen: offen / in Arbeit / akzeptiert → behoben; false positive bleibt.
- SBOM löschen bleibt echtes Löschen.

## Ansätze
| | Ansatz | Abwägung |
|---|---|---|
| **A (gewählt)** | Komponente „ausgebaut“ markieren, Treffer bleiben, Scan löst auf | Bestehende Tabellen/Ansichten; „behoben“ direkt nutzbar |
| B | Historien-Tabelle behobener Treffer | Zwei Quellen für Liste/Detail/Rückkanäle, Zwischenzustand trotzdem nötig |
| C | Sofort beim Upload „behoben“ | Schließt Issues bei Upgrade ohne Fix fälschlich (vom Nutzer verworfen) |

## Design
- `Component.retired_in_version_id: int | None` (FK `sbom_version.id`) – „ausgebaut mit
  Version X“. Ausgebaute Komponenten: nicht im Scan, nicht im Komponenten-Reiter, nicht im
  SBOM-Abgleich (nur Live-Komponenten werden abgeglichen); `DeleteSbom` löscht sie mit.
- `Finding.resolved_at: datetime | None`, `Finding.resolution: str` (Text, z. B.
  „Komponente ausgebaut mit SBOM backend-image v1.5.0“).
- **Upload:** verschwundene Komponenten mit Treffern → ausgebaut (Treffer bleiben);
  verschwundene ohne Treffer → gelöscht wie bisher.
- **Ende des Scans** (nach dem Speichern der Treffer, vor dem Commit), nur wenn **keine
  Quelle mit Fehler** endete (sonst könnte eine ausgefallene Quelle Lücken als behoben
  erscheinen lassen): für jeden noch nicht aufgelösten Treffer an einer ausgebauten Komponente
  - gibt es für dieselbe Anwendung und Advisory einen Treffer an einer Live-Komponente:
    dieser übernimmt Status (falls er `offen` ist) und Kommentar, der alte Treffer wird gelöscht;
  - sonst: Status `behoben` (außer `false_positive`), `resolved_at` = Scan-Zeit,
    `resolution` mit SBOM-Name und Versionsbezeichnung.
  - Ausgebaute Komponenten ohne verbleibende Treffer werden gelöscht.
- Export: Treffer ausgebauter, noch nicht aufgelöster Komponenten bleiben bis zum Scan drin
  (vorsichtig). `behoben` ist ohnehin nicht im Export.

## Nicht-Ziele
UI für `resolution` / `resolved_at` (Liste zeigt Status „Behoben“, Filter existiert);
manuelle Komponenten (können nicht entfernt werden); GitHub-Issues schließen (Teil 4).

## Tests
Upload (ausgebaut vs. gelöscht), Scan-Auflösung (behoben, false positive bleibt, Übernahme auf
neuen Treffer, Quelle mit Fehler → keine Auflösung, aufgeräumte Komponente), Scan ignoriert
ausgebaute Komponenten, Komponenten-Reiter ohne ausgebaute, DeleteSbom mit ausgebauten,
Repository/Migration, alembic check.
