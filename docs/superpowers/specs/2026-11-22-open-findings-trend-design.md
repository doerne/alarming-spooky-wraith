# Offene Funde im Fokus und Verlauf von Zulauf/Abarbeitung – Design

Branch: `feat/open-findings-focus` (abgezweigt von `feat/scheduled-scan`)

## Warum

Die Schwachstellen-Seite zeigt heute ein vollständiges Archiv: Tabelle, Kacheln und
Diagramm zählen alle Funde, auch behobene, akzeptierte und False Positives. Man sieht
schlecht, was **noch niemand angefasst hat**, und gar nicht, **wie sich die Lage
entwickelt**.

Der Nutzer will zwei Dinge sehen – insgesamt und je Anwendung (Repository):

1. **Zulauf:** wie stark neue CVE-Funde dazukommen.
2. **Abarbeitung:** wie gut das Team offene Punkte erledigt.

## Begriffe (vom Nutzer entschieden)

- **Erledigt** = jeder Status außer `offen` und `in_arbeit`, also `behoben`,
  `akzeptiert`, `false_positive`.
- **Offener Bestand** = `offen` + `in_arbeit` (noch nicht erledigt).
- **Unangetastet** = Status `offen` (weder angegangen noch erledigt).

## Ziele

- Tabellen (Schwachstellen-Seite und CVE-Tab einer Anwendung) starten mit Statusfilter
  „Offen“. Der Filter bleibt wie bisher änderbar; „Filter zurücksetzen“ zeigt alle.
- Kacheln zeigen den aktuellen Bestand **und** die Veränderung im gewählten Zeitraum.
- Ein Verlaufsdiagramm zeigt je Woche: neue Funde, erledigte Funde und den offenen
  Bestand am Wochenende – auf der Schwachstellen-Seite (alle Anwendungen) und im
  CVE-Tab einer Anwendung (nur diese Anwendung).

## Nicht-Ziele

- Kein Verlauf von `in_arbeit` (nur aktueller Stand als Kachel).
- Keine Kennzahlen wie mittlere Bearbeitungszeit (MTTR) – dafür wäre später ein
  Status-Protokoll (Ansatz C) nötig.
- Kein Dashboard über Anwendungen hinweg (Ranking „wer hängt hinterher“).
- Funde, die gelöscht werden (SBOM gelöscht, Komponente entfernt), verschwinden aus
  dem Verlauf. Das ist akzeptiert.

## Anti-Ziele

- Zahlen, die das Team schlechter aussehen lassen als es ist (z. B. akzeptierte Funde
  nicht als erledigt zählen) oder künstlichen Zulauf erzeugen (dieselbe Lücke nach
  einem Versions-Update erneut als „neu“ zählen).
- Neue Abhängigkeiten. Diagramme mit dem vorhandenen recharts + shadcn `chart`.

## Ansätze

| | Ansatz | Abwägung |
|---|---|---|
| **A (gewählt)** | Verlauf aus Zeitstempeln der Funde berechnen: neue Spalte `closed_at`, Aggregation pro Woche zur Abfragezeit | Keine neue Tabelle, kein Job; `behoben` sofort rückwirkend. Wiedereröffnete Funde verlieren ihre frühere Erledigung im Verlauf. |
| B | Täglicher Snapshot je Anwendung/Status/Schweregrad nach jedem Scan | Exakt auch für `in_arbeit`, aber Verlauf erst ab heute, mehr Bausteine, Zulauf nur indirekt. |
| C | Protokoll jeder Statusänderung | Am genauesten, MTTR möglich, aber größter Aufwand (alle Schreibpfade). |

Der Nutzer hat **A** gewählt: beantwortet Zulauf und Abarbeitung mit den vorhandenen
Daten; C lässt sich später ergänzen.

## Datenmodell

### Neue Spalte `finding.closed_at` (nullable, `DateTime(timezone=True)`)

Regel (Domain, eine Stelle): Beim Statuswechsel

- von nicht erledigt → erledigt: `closed_at = jetzt`
- von erledigt → erledigt (z. B. akzeptiert → behoben): `closed_at` bleibt
- → nicht erledigt (Wiedereröffnung, `in_arbeit`): `closed_at = None`

`resolved_at` bleibt unverändert in seiner bisherigen Bedeutung (Zeitpunkt der
Behebung, nur für `behoben`).

Alle Schreibpfade, die den Status ändern, müssen über diese Regel laufen:
`save_triage`, `resolve`, `save_report` im Repository bzw. deren Aufrufer
(`finding_report.py`, `github_sync.py`, `retired_findings.py`, Triage-Endpoint).
Empfehlung: eine Domain-Methode `Finding.with_status(status, now)` bzw. eine reine
Funktion `closed_at_after(old_status, new_status, old_closed_at, now)`, die alle
Pfade nutzen; das Repository schreibt `closed_at` nur durch.

### Zusammenführen (`absorb`)

`Finding.absorb` (Übertrag auf die Nachfolger-Komponente nach Versions-Update in
`retired_findings._transfer`, Alias-Zusammenführung in `alias_absorber`):

- übernimmt das **frühere** der beiden `first_seen_at`. Sonst zählt dieselbe Lücke
  nach jedem Update wieder als „neu“. Folge (gewollt, Entscheidung Builder-Check): Eine
  nach Versions-Update weiter bestehende Lücke löst kein neues Auto-Issue aus – ihr
  Issue-Link wird ohnehin übertragen.
- übernimmt beim Statusübertrag das `closed_at` **des Spenders** (wie heute
  `resolved_at`), nicht „jetzt“. Sonst entstünde künstliche Abarbeitung. Die
  `closed_at`-Regel oben gilt für echte Statuswechsel; die Übernahme ist ein eigener
  Pfad mit fremdem Zeitstempel.
- `save_report` schreibt künftig `closed_at` **und** `first_seen_at` (heute schreibt
  es keines davon; `first_seen_at` wird nur in `upsert` beim Anlegen gesetzt).

### Migration

`updated_at` taugt nicht als Ersatzdatum: es springt bei jedem Scan (`upsert`),
Kommentar und Issue-Link und läge bei Altfunden in der jüngsten Woche – genau der
künstliche Zulauf, den die Anti-Ziele ausschließen.

Stattdessen ein **festes Ausgangsdatum** `BASELINE = Migrationszeitpunkt − 53 Wochen`
(vor dem längsten wählbaren Zeitraum):

1. Spalte `closed_at` anlegen.
2. `first_seen_at IS NULL` → `first_seen_at = BASELINE`. Altfunde landen damit in
   jedem Zeitraum nur im Ausgangsbestand `openAtStart`, nie als „neu“.
3. Bestehende erledigte Funde:
   - `behoben` mit `resolved_at` → `closed_at = resolved_at`
   - sonst erledigt → `closed_at = BASELINE` (zählt nie als „erledigt im Zeitraum“)
4. Schutz Auto-Issues: `GithubSync._seen_after_enable` vergleicht
   `first_seen_at >= auto_issue_enabled_at`. Weil `BASELINE` vor jedem
   `auto_issue_enabled_at` liegt (Feature existiert erst seit 2026-11), lösen
   nachgetragene Werte keine Issues aus. Ein Test für den Sync-Pfad sichert das ab.

## Backend

### Domain: Verlaufsberechnung (rein, ohne Framework)

`compute_trend(findings, now, weeks) -> FindingTrend`

- Wochen: ISO-Wochen, Beginn Montag 00:00 **UTC** (Builder-Entscheidung, kleine
  Verschiebung zur Ortszeit akzeptiert). Die aktuelle, angebrochene Woche ist die
  letzte Woche.
- je Woche: `new` = Funde mit `first_seen_at` in der Woche, `closed` = Funde mit
  `closed_at` in der Woche, `open_at_end` = Funde mit `first_seen_at < Wochenende`
  und (`closed_at` leer oder ≥ Wochenende).
- zusätzlich: `open_at_start` (Bestand zu Beginn des Zeitraums), Summen `new_total`,
  `closed_total` für den Zeitraum, aktueller Stand `untouched_now` (`offen`),
  `in_progress_now` (`in_arbeit`), `open_by_severity_now` (offener Bestand je Stufe).
- Funde ohne `first_seen_at` (sollte es nach der Migration nicht mehr geben) werden
  übersprungen.

### Use Case `GetFindingTrend`

`execute(weeks, application_id | None)` – lädt Funde (alle oder einer Anwendung) über
das Repository und ruft `compute_trend`. In-Memory-Aggregation ist bei der heutigen
Datenmenge (Hunderte bis wenige Tausend Funde) ausreichend; eine SQL-Aggregation ist
nicht nötig.

### Endpoint

`GET /api/findings/trend?weeks=12&applicationId=…`

- `weeks`: erlaubt 4, 12, 26, 52; Standard 12.
- Antwort (camelCase, `ApiModel`):

```json
{
  "weeks": [{ "weekStart": "2026-11-16", "new": 3, "closed": 5, "openAtEnd": 42 }],
  "openAtStart": 44, "newTotal": 7, "closedTotal": 12,
  "untouchedNow": 30, "inProgressNow": 12,
  "openBySeverityNow": { "kritisch": 3, "hoch": 10, "mittel": 20, "niedrig": 9 }
}
```

- Unbekannte `applicationId` → 404 wie bei den übrigen Anwendungs-Endpunkten.

## Frontend

### Schwachstellen-Seite (`features/cves`)

```
[Zeitraum: 4 W | 12 W | 26 W | 52 W]                         [Scan starten]
┌ Offener Bestand ┐┌ Unangetastet ┐┌ In Arbeit ┐┌ Neu (Zeitraum) ┐┌ Erledigt (Zeitraum) ┐
│ 42   ▼2         ││ 30           ││ 12        ││ 7              ││ 12                  │
└─────────────────┘└──────────────┘└───────────┘└────────────────┘└─────────────────────┘
┌ Verlauf ───────────────────────────────┐┌ Offen nach Schweregrad ┐
│ Balken: neu (oben) / erledigt          ││ kritisch ███ 3          │
│ Linie: offener Bestand                 ││ hoch ██████ 10 …        │
└────────────────────────────────────────┘└─────────────────────────┘
Tabelle (Start-Filter: Status = Offen)
```

- **Kacheln** aus dem Trend-Endpoint. „Offener Bestand“ zeigt die Differenz
  `aktuell − openAtStart` mit Pfeil; weniger ist gut (semantische Farben, keine Palette).
  Die bisherigen Kacheln „Funde gesamt“, „Kritisch“, „Hoch“ entfallen;
  Kritisch/Hoch stecken im Schweregrad-Diagramm.
- **Schweregrad-Diagramm** zeigt nur noch den offenen Bestand (`openBySeverityNow`).
- **Verlaufsdiagramm**: Balken „neu“ und „erledigt“ je Woche (z. B. gespiegelt oder
  nebeneinander, Builder-Entscheidung), Linie „offener Bestand“. Ein Tooltip pro Woche.
- **Zeitraum-Auswahl** steuert Kacheln und Verlauf; Standard 12 Wochen.
- **Tabelle**: Startfilter `statuses: ["offen"]`. Die Filter-Zusammenfassung zeigt den
  Filter als aktiv. „Zurücksetzen“ leert alle Filter (zeigt alles), wie bisher.

### CVE-Tab einer Anwendung (`features/inventory`)

- Kompakte Variante: Kacheln + Verlaufsdiagramm über der Tabelle, gleicher Endpoint
  mit `applicationId`, eigene Zeitraum-Auswahl.
- Tabelle startet ebenfalls mit Statusfilter „Offen“.

### Struktur

- Features dürfen sich nicht importieren. Das reine Verlaufsdiagramm und die
  Trend-Kacheln liegen daher in `shared/components/` (rein, Props), der Typ samt
  zod-Schema in `shared/api/` oder `shared/lib/`. Je Feature ein eigener
  TanStack-Query-Hook im `hooks/`-Ordner, der den Endpoint abfragt.
- Query-Invalidierung: Nach Triage-Änderung, Scan-Ende und SBOM-Upload wird die
  Trend-Query wie die Findings-Query ungültig gemacht.
- Test-IDs z. B. `cves-select-trend-range`, `cves-card-trend-open`,
  `cves-chart-trend`, `inventory-chart-trend`.

## Tests

- Domain: `closed_at`-Regel (alle Übergänge), `absorb` behält frühestes
  `first_seen_at`, `compute_trend` (Wochengrenzen, Wiedereröffnung, leere Wochen,
  Funde vor dem Zeitraum).
- Use Case mit Fakes; Router-API-Test für Parameter, 404, Antwortform.
- Migration: Befüllregeln gegen MariaDB prüfen (Skill `db-migration`).
- Frontend: Kacheln (Differenz/Pfeil), Diagramm rendert Wochen, Zeitraum-Auswahl,
  Startfilter „Offen“ in beiden Tabellen (Vitest über `getByTestId`).

## Dem Builder überlassen

- Genaue Darstellung der Balken (gespiegelt vs. gruppiert) und Farbzuordnung aus den
  `--chart-*`-Tokens.
- Ob das Diagramm leere Wochen am Anfang ausblendet.

## Entscheidungen aus dem Builder-Check (Vorschlag, vom Nutzer zu prüfen)

- Festes Ausgangsdatum statt `updated_at` für nachgetragene Zeitstempel.
- `absorb` übernimmt frühestes `first_seen_at` und das `closed_at` des Spenders.
- Auto-Issues werden durch die Migration nicht ausgelöst (abgesichert durch Test).
