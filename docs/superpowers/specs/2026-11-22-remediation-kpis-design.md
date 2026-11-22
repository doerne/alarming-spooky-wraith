# Kennzahlen zur Abarbeitung: Fristen, Updates, Art der Erledigung – Design

Branch: `feat/remediation-kpis` (abgezweigt von `feat/open-findings-focus`, PR #12)

## Warum

Der Verlauf (vorheriges Feature) zeigt Zulauf und Abfluss als Zahlen. Der Nutzer will
zusätzlich beantworten:

1. **Wie gut arbeiten wir ab?** – nicht als Gesamtmenge, sondern gemessen an Fristen
   je Schweregrad.
2. **Wo lohnt sich Arbeit am meisten?** – welches Paket-Update schließt die meisten
   offenen Funde.
3. **Ist „Erledigt“ ehrlich?** – wie viel davon wirklich behoben (und bestätigt) ist,
   und wie viel nur akzeptiert, als False Positive markiert oder bloß gemeldet.

Alle drei Kennzahlen erscheinen auf der Schwachstellen-Seite (alle Anwendungen) und im
CVE-Tab einer Anwendung (nur diese Anwendung).

## Begriffe

Unverändert aus dem Verlaufs-Feature: **Erledigt** = `behoben`, `akzeptiert`,
`false_positive`. **Offener Bestand** = `offen` + `in_arbeit`.

Neu:

- **Frist** je Schweregrad (vom Nutzer bestätigt, fest im Code, Domain-Konstante):
  kritisch 7 Tage, hoch 30, mittel 90, niedrig 180.
- **Fristbeginn** = `max(first_seen_at, FRIST_START)` mit
  `FRIST_START = 2026-11-22 00:00 UTC` (Einführung der Zeiterfassung). Altfunde mit
  nachgetragenem `first_seen_at` (BASELINE) und alle vorher gesehenen Funde starten
  damit am 22.11.2026 – vom Nutzer so entschieden („Altfunde ab Einführung der
  Zeiterfassung, nicht sofort überfällig“).
- **Fällig am** = Fristbeginn + Frist. **Überfällig** = offener Bestand mit
  `fällig am <= jetzt`. **Bald fällig** = offener Bestand, nicht überfällig, fällig
  innerhalb der nächsten 7 Tage.
- **Art der Erledigung** (für erledigte Funde):
  - `behoben` mit `resolved_by = sbom` → **„Behoben, bestätigt“** (durch neue SBOM)
  - `behoben` mit `resolved_by = reported` → **„Behoben, gemeldet“** (Agent/GitHub,
    noch nicht durch SBOM bestätigt)
  - `behoben` ohne `resolved_by` → **„Behoben, von Hand“**
  - `akzeptiert` → **„Akzeptiert“**
  - `false_positive` → **„False Positive“**

## Ziele

1. **Fristen-Karte** („Fristen“): Anzahl überfällig (hervorgehoben, `text-destructive`
   wenn > 0), Anzahl bald fällig, Aufschlüsselung überfällig je Schweregrad, und das
   nächste Fälligkeitsdatum im offenen Bestand („Nächste Frist: 22.12.“). Ohne offenen
   Bestand: „Keine offenen Funde.“
2. **Update-Karte** („Behebbar durch Update“): Die bis zu 5 Pakete, deren Update die
   meisten offenen Funde schließt – je Zeile Paket, Ökosystem, Zielversion, Anzahl
   Funde, Anzahl betroffener Anwendungen (nur auf der Schwachstellen-Seite sichtbar).
   Darunter eine Zeile: „X von Y offenen Funden durch Update behebbar“ und, falls es
   mehr als 5 Pakete gibt, „+ N weitere Pakete“.
3. **Erledigungs-Aufteilung** im Verlauf: Die Kachel „Erledigt im Zeitraum“ bleibt;
   unter dem Verlaufsdiagramm bzw. als eigene kleine Karte („Wie erledigt“) erscheint
   die Aufteilung der im gewählten Zeitraum erledigten Funde nach Art der Erledigung
   (horizontale gestapelte Leiste oder Balken, plus Zahlen als Legende). Summe =
   „Erledigt im Zeitraum“.

### Skizze Schwachstellen-Seite

```
[4|12|26|52 Wochen]
[Offener Bestand] [Unangetastet] [In Arbeit] [Neu im Zeitraum] [Erledigt im Zeitraum]
[ Verlauf (2/3)                         ] [ Offen nach Schweregrad (1/3) ]
[ Fristen (1/3) ] [ Wie erledigt (1/3) ] [ Behebbar durch Update (1/3)   ]
[ Tabelle, Startfilter offen … ]
```

Im CVE-Tab einer Anwendung dieselbe dritte Reihe unter dem Verlauf (ohne Spalte
„Anwendungen“ in der Update-Karte).

## Nicht-Ziele

- Fristen konfigurierbar (pro Anwendung oder global per Einstellung). Konstanten im
  Code; später erweiterbar.
- Klick auf Kennzahl filtert die Tabelle (z. B. „nur überfällige“). Später möglich.
- Durchlaufzeit/MTTR, Wiedereröffnungsquote, Ablaufdaten akzeptierter Risiken.
- Ranking der Anwendungen.

## Anti-Ziele

- Altfunde, die vom ersten Tag an alles rot färben (deshalb Fristbeginn 22.11.).
- Eine Zielversion vorschlagen, die nicht alle Funde des Pakets schließt (deshalb die
  höchste Fix-Version je Paket, siehe unten).
- Neue Abhängigkeiten (Versionsvergleich über das vorhandene `univers`). Diagramme mit vorhandenem
  recharts + shadcn `chart`.

## Ansätze

| | Ansatz | Abwägung |
|---|---|---|
| **A (gewählt)** | Neuer Endpoint für den Stand von heute (Fristen, Updates); die Erledigungs-Aufteilung wird Teil des Verlaufs-Endpoints, weil sie vom Zeitraum abhängt | Saubere Trennung: zeitraumunabhängig vs. zeitraumabhängig; Domain-Funktionen einzeln testbar |
| B | Alles an den Verlaufs-Endpoint hängen | Ein Aufruf weniger, mischt aber Zeitraum- und Stand-Zahlen; Zeitraumwechsel rechnet Fristen unnötig neu |
| C | Im Browser aus der Fundliste rechnen | Fundliste kennt weder Erstsichtung noch `resolved_by`; Logik im Frontend statt Domain |

Claude hat A gewählt (der Nutzer hat das Wie übergeben).

## Backend

### Domain (`backend/app/domain/`, rein, ohne Framework)

- `remediation.py` (neu):
  - `DEADLINE_DAYS: dict[Severity, int]`, `DEADLINE_START: datetime`,
    `DUE_SOON_DAYS = 7`.
  - `due_at(finding) -> datetime` (Fristbeginn + Frist nach `finding.risk.level`).
  - `compute_deadlines(findings, now) -> DeadlineSummary` mit `overdue`, `due_soon`,
    `overdue_by_severity: dict[Severity, int]` (immer alle vier Stufen),
    `next_due_at: datetime | None`. Nur offener Bestand zählt.
  - `compute_update_targets(open_items, limit) -> UpdateSummary` – Eingabe sind
    Tupel/kleine Value Objects aus (Komponente: Name, Ökosystem, Version), Anwendung,
    `fixed_version | None`. Gruppierung nach (Ökosystem, Paketname). Zielversion = höchste
    `fixed_version` der Gruppe. Ergebnis: `targets` (absteigend nach Anzahl Funde, dann
    Paketname), `fixable_open`, `open_total`, `more_packages`.
  - Versionen vergleicht die Domain nicht selbst. Sie nutzt einen neuen Port
    `VersionComparator` (`domain/ports.py`), der für jedes Ökosystem richtig vergleicht.
    Die Implementierung ist `UniversVersionMatcher.is_newer` auf Basis von `univers`. Die
    Bibliothek nutzt das Projekt bereits für den Scan, sie ist also keine neue
    Abhängigkeit. (Claudes Entscheidung bei der Planung, ersetzt den eigenen
    `compare_versions`: Ein selbst geschriebener Vergleich würde npm-, PyPI- und
    Maven-Regeln nur ungefähr treffen.) Was sich nicht parsen lässt, gilt als
    „nicht neuer“.
- `finding_trend.py`: `FindingTrend` bekommt `closed_by_outcome: dict[ClosureKind, int]`
  (immer alle fünf Arten) für Funde, deren `closed_at` im Zeitraum liegt – dieselbe
  Menge, die `closed_total` zählt. `ClosureKind` (StrEnum) mit Werten
  `fixed_confirmed`, `fixed_reported`, `fixed_manual`, `accepted`, `false_positive`;
  Zuordnung in der Domain (`closure_kind_of(finding)`).

### Application

- `GetRemediationKpis(uow, clock).execute(application_id: int | None)` lädt Funde,
  Komponenten und Advisories (für `fixed_version`), prüft die Anwendung
  (`EntityNotFoundError` → 404 wie beim Verlauf), filtert auf offenen Bestand und ruft
  die Domain-Funktionen auf. Limit der Update-Liste: 5.

### Presentation

- `GET /api/findings/kpis?applicationId=` → `RemediationKpisDto` (camelCase):
  `deadlines { overdue, dueSoon, overdueBySeverity, nextDueAt }`,
  `updates { targets[{ packageName, ecosystem, targetVersion, findings, applications }],
  fixableOpen, openTotal, morePackages }`.
- `FindingTrendDto` bekommt `closedByOutcome` (Schlüssel = `ClosureKind`-Werte).
- Router ohne Logik, Registrierung in `main.py`. API-Tests: mit und ohne
  `applicationId` (200), unbekannte Anwendung (404).

## Frontend

- `shared/api/remediation-kpis.ts`: zod-Schema + `fetchRemediationKpis({ applicationId? })`.
- `shared/api/finding-trend.ts`: Schema um `closedByOutcome` erweitern.
- `shared/components/`: `deadline-card.tsx`, `update-targets-card.tsx`,
  `closure-breakdown-card.tsx` – rein, Props + `feature` für Test-IDs
  (`${feature}-card-deadlines`, `${feature}-text-overdue`, `${feature}-list-update-targets`,
  `${feature}-item-update-target-${index}`, `${feature}-card-closure-breakdown`).
  `showApplications`-Prop steuert die Spalte „Anwendungen“.
- Hooks: `features/cves/hooks/use-remediation-kpis.ts` (Key `["findings","kpis"]`),
  `features/inventory/hooks/use-application-kpis.ts`
  (Key `["application-findings", id, "kpis"]`) – damit greifen die bestehenden
  Invalidierungen (Scan, SBOM, Komponenten, GitHub-Abgleich) automatisch.
- Seiten: dritte Reihe gemäß Skizze; Fehler → `role="alert"`-Hinweis
  (`cves-error-kpis` / `inventory-error-kpis`), Laden → nichts.
- Farben: nur semantische Tokens und `--chart-*`. Überfällig > 0 → `text-destructive`.

## Festlegungen aus dem Builder-Check (Claudes Entscheidungen)

1. **Fund ohne `first_seen_at`** zählt zum offenen Bestand und bekommt den Fristbeginn
   `DEADLINE_START`. So passen Fristen-Zahlen und Kachel „Offener Bestand“ zusammen.
2. **Fix-Version gehört zur Advisory, nicht zur Komponente.** Sie gilt für einen Fund
   nur, wenn `is_newer(ecosystem, fixed_version, found_version)`. Sonst behandeln wir
   den Fund wie einen ohne bekannte Fix-Version. Das schützt vor veralteten Daten und vor
   Fix-Versionen eines anderen Pakets aus Mehrfach-Advisories, ohne neue Datenfelder.
3. **Zählweise der Update-Karte:** Eine Zeile zählt nur Funde ihrer Gruppe mit gültiger
   Fix-Version. `fixableOpen` = offene Funde mit gültiger Fix-Version, `openTotal` =
   offener Bestand. Funde derselben Gruppe ohne Fix-Version zählen nur in `openTotal`.
4. **`closed_by_outcome`** zählt genau die Menge hinter `closed_total`, also nur
   verfolgbare Funde (`_is_trackable`), deren `closed_at` im Zeitraum liegt. Die Art der
   Erledigung kommt aus dem aktuellen Status und `resolved_by`.
5. **`in_arbeit`** wird bei den Fristen genauso behandelt wie `offen`.
6. **Fälligkeit** wird als exakter Zeitpunkt (UTC) berechnet. Die Anzeige ist ein
   lokales Datum (`TT.MM.`).

## Was der Builder entscheidet

- Exakte Darstellung der Erledigungs-Aufteilung (gestapelte Leiste vs. kleine Balken),
  solange Summe und Zahlen sichtbar sind.
- Formulierung von Leerzuständen (z. B. „Kein offener Fund mit bekannter Fix-Version.“).

## Prüfungen

- Domain-Tests: Fristgrenzen (genau fällig = überfällig), Fristbeginn vor/nach
  22.11., je Schweregrad; erledigte Funde zählen nie; Gruppierung über Anwendungen;
  höchste Fix-Version inkl. `1.10.0 > 1.9.0` und Vorabversionen; Funde ohne
  Fix-Version zählen nur in `openTotal`; `closed_by_outcome`-Summe = `closed_total`.
- `make check` grün, Browser-Check hell/dunkel, Anwendung ohne Funde.
