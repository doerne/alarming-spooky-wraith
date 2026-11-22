# Täglicher Scan nach Zeitplan – Design

Stand: 2026-11-22 · Stufe 5 der Haupt-Spec (`2026-10-31-cve-radar-design.md`), ohne Queue/Worker

## Absicht
Der Nutzer will **jeden Tag für jede Anwendung den aktuellen Stand an CVEs sehen**, ohne an
*Scan starten* denken zu müssen. Heute läuft der Scan nur auf Knopfdruck; damit hängen auch der
GitHub-Abgleich (läuft nach dem Scan) und die SBOM-Nachweise für „behoben“ (kommen mit dem
nächsten Scan) davon ab, dass jemand klickt.

## Entscheidungen des Nutzers
- Scan **täglich automatisch**, für alle Anwendungen.
- Sichtbarkeit: ein Hinweis **„Stand von …“** reicht; er warnt, wenn der Stand älter als ein Tag
  ist oder der letzte Lauf Fehler hatte. Keine Höchstdauer je Quelle, keine weiteren Alarme.
- Umsetzung über **APScheduler** (Ansatz B); die neue Abhängigkeit ist damit freigegeben.
- **Je Anwendung ehrlich (a):** Wurde eine Anwendung, eine ihrer Komponenten oder ihre aktuelle
  SBOM-Version nach dem letzten brauchbaren Lauf angelegt bzw. geändert, zeigt ihr CVE-Reiter
  „Noch nicht gescannt“ statt „Stand von …“ (siehe „Stand je Anwendung“).
- Die Festlegungen unten („Meine Festlegung“) hat der Nutzer mit „passt“ übernommen.

## Ziele
- Ein Scan pro Tag zu einer festen Uhrzeit, ohne Zutun.
- Ein verpasster Lauf (Backend war aus) wird beim Start nachgeholt.
- Ergebnis jedes Laufs (manuell oder geplant) übersteht einen Neustart.
- Im UI ist sichtbar, von wann der Stand ist und ob er verlässlich ist.

## Nicht-Ziele
- Uhrzeit oder Zeitplan in der Oberfläche einstellen (nur ENV).
- Mehrere Läufe pro Tag, Scan je Anwendung, Queue/Worker/Redis (arq).
- Höchstdauer oder Wiederholung je Quelle; Benachrichtigungen (Mail, Chat).
- Verlauf aller Läufe im UI (gespeichert wird er, angezeigt nur der letzte).

## Anti-Ziele
- Zwei Scans gleichzeitig (geplant + manuell, oder doppelt nach dem Nachholen).
- Ein „Stand: heute“, obwohl der Lauf gescheitert ist oder Quellen Lücken hatten.
- Der Zeitplan verhindert den Start des Backends oder bringt es zum Absturz.

## Rahmenbedingungen
- Backend läuft als **ein** uvicorn-Prozess (`backend/Dockerfile`); Scan und GitHub-Abgleich
  laufen als Thread über `ThreadIngestRunner`/`ThreadSyncRunner`, gemeinsam gesperrt über
  `JobGate`. Ein Scheduler im selben Prozess reicht.
- Container sind `read_only`; der Scheduler darf nichts ins Dateisystem schreiben.
- Clean Architecture: Scheduler-Bibliothek nur in `infrastructure/`, Verdrahtung in `main.py`.

## Ansätze
| | Ansatz | Abwägung |
|---|---|---|
| A | Eigener kleiner Timer-Thread im Backend | keine Abhängigkeit; Zeit-/Zeitzonenlogik selbst |
| **B (gewählt)** | **APScheduler 3.11** `BackgroundScheduler` mit `CronTrigger` im Backend | erprobte Cron-/Zeitzonenlogik; neue Abhängigkeit; Nachholen bleibt eigene Logik |
| C | Eigener Cron-Container ruft `POST /api/ingest/run` | sauber getrennt, aber weiterer gehärteter Dienst, Netzzugang, Nachholen ungelöst |
| – | arq + Redis (Haupt-Spec) | verworfen: neuer Datendienst + Worker für einen Job am Tag |

Gewählt hat der Nutzer B. APScheduler **3.x** (stabil), nicht 4.x (Vorabversion, andere API).

## Konfiguration
`infrastructure/config.py`:
- `scan_schedule_enabled: bool = True` (ENV `SCAN_SCHEDULE_ENABLED`) – zum Abschalten, z. B. im
  Notweg oder in Tests.
- `scan_schedule_time: str = "04:00"` (ENV `SCAN_SCHEDULE_TIME`, Format `HH:MM`, beim Start
  validiert; ungültig → Start schlägt mit klarer Meldung fehl).
- `scan_schedule_timezone: str = "Europe/Berlin"` (ENV `SCAN_SCHEDULE_TIMEZONE`, IANA-Name).

**Meine Festlegung:** Standard 04:00 statt 03:00 – APScheduler rechnet in Ortszeit, und 02:00–03:00
fällt bei der Zeitumstellung weg oder kommt doppelt; 04:00 liegt sicher außerhalb.

## Ablauf
1. **Täglich:** `CronTrigger(hour, minute, timezone)` ruft `ingest_runner.start()` – denselben
   Einstieg wie der Button. Gibt `start()` `False` zurück (Scan oder Abgleich läuft schon), wird
   der Lauf übersprungen und geloggt; kein Nachholen am selben Tag nötig, weil gerade gescannt wird.
   Job-Optionen: `max_instances=1`, `coalesce=True`, `misfire_grace_time` großzügig (z. B. 1 h).
2. **Nachholen beim Start:** Nach dem Start (im `on_startup`, nach `reset_interrupted_runs`)
   startet ein Use Case einmal `ingest_runner.start()` (Trigger `catch_up`), wenn **beides** gilt:
   - der letzte **regulär beendete** Lauf (`ok`, `incomplete` oder `failed` – aber nicht „durch
     Neustart abgebrochen“) hat vor mehr als 24 h begonnen oder es gibt keinen, und
   - in den letzten 24 h wurde **kein** `catch_up`-Lauf gestartet.

   **Meine Festlegung:** Ein gescheiterter Lauf zählt als erledigt (sonst scannt jeder Neustart
   nach einem Fehler sofort wieder). Ein durch Neustart abgebrochener Lauf zählt nicht – ein
   Deployment um 04:05 soll den Tagesstand nicht kosten. Die zweite Bedingung verhindert eine
   Schleife, falls der Scan selbst den Prozess abstürzen lässt (höchstens ein Nachholversuch pro Tag).
   Ist `SCAN_SCHEDULE_ENABLED=false`, entfällt auch das Nachholen.
3. **Herunterfahren:** Im Lifespan `scheduler.shutdown(wait=False)`; ein laufender Scan-Thread
   ist ohnehin ein Daemon-Thread und wird von `reset_interrupted_runs` beim nächsten Start aufgeräumt.
4. Der GitHub-Abgleich hängt wie bisher am Scan (`run_scan_then_sync`) und läuft dadurch mit.

## Lauf-Ergebnis speichern
Neue Tabelle `scan_run` (eine Zeile je Lauf, manuell und geplant):
`id`, `trigger` (`manual` / `schedule` / `catch_up`), `started_at`, `finished_at` (NULL solange
er läuft), `outcome` (`ok` / `incomplete` / `failed`), `components_scanned`, `findings_found`,
`message` (≤ 500, z. B. „2 Quellen mit Fehlern: NVD, Snyk“).

- `ok`: Lauf fertig, keine Quelle `unreliable` (`SourceRunResult.unreliable`, übersprungene
  Quellen ohne Key zählen nicht).
- `incomplete`: Lauf fertig, aber mindestens eine Quelle mit Fehler oder Teilausfall.
- `failed`: Lauf als Ganzes gescheitert (Ausnahme außerhalb der Quellen).
- `reset_interrupted_runs` setzt Läufe ohne `finished_at` beim Start auf `failed`,
  `finished_at` = Zeitpunkt des Resets, Meldung „durch Neustart abgebrochen“ (Kennzeichen
  `interrupted = true`, damit das Nachholen sie erkennt).
- `GET /api/ingest/status` liefert wie bisher `running`/`startedAt` des aktuellen Laufs und
  zusätzlich **aus der DB** (damit der Stand einen Neustart übersteht):
  - `lastRun`: der zuletzt beendete Lauf (`trigger`, `outcome`, `startedAt`, `finishedAt`,
    `findingsFound`, `message`),
  - `lastUsableRun`: der zuletzt beendete Lauf mit `outcome` `ok` oder `incomplete` – er bestimmt
    den „Stand“. Beide sind `null`, wenn es keinen gibt.
- Der GitHub-Abgleich nach dem Scan fließt **nicht** in `outcome` ein. **Meine Festlegung:** Sein
  Ergebnis steht schon je Anwendung in `github_sync_message` und wird im CVE-Reiter angezeigt;
  der „Stand“ beschreibt die CVE-Daten.
- Aufräumen alter Zeilen: **Meine Festlegung:** nichts löschen (eine Zeile pro Tag ist vernachlässigbar).

## Anzeige „Stand von …“
Eine reine Komponente in `shared/components/` (beide Features nutzen sie; Features importieren
sich nicht gegenseitig), gespeist aus `GET /api/ingest/status`:

```
Stand: heute 04:12 · automatisch                       (ok, < 24 h)
⚠ Stand: heute 04:12 · 2 Quellen mit Fehlern            (incomplete)
⚠ Stand: 20.11. 04:09 – älter als ein Tag               (> 24 h)
⚠ Letzter Scan fehlgeschlagen (20.11. 04:09)            (failed; Stand = letzter ok/incomplete)
Noch kein Scan                                           (keine Zeile)
```

- Normalfall in `text-muted-foreground`, Warnung mit Icon (`TriangleAlert`) und `text-destructive`
  bzw. passendem semantischem Token; keine Palettenfarben.
- Ort: neben *Scan starten* auf der Schwachstellen-Seite (ersetzt „Letzter Scan: n Funde“ in
  `ingest-control.tsx`) **und** im CVE-Reiter der Anwendung. **Meine Festlegung:** auch in der
  Anwendung, weil der Nutzer „für jede Anwendung“ den Stand sehen will; der Stand ist für alle
  Anwendungen derselbe (ein Lauf deckt alle ab).
- Test-IDs z. B. `cves-text-scan-freshness`, `inventory-text-scan-freshness`.
- „älter als ein Tag“ = `lastUsableRun.finishedAt` mehr als **26 h** vor jetzt (Browserzeit).
  **Meine Festlegung:** 2 h Puffer, damit nicht jeden Morgen während des laufenden Scans eine
  Warnung erscheint.
- Zustände in dieser Reihenfolge (der erste passende gewinnt), Text zusammengesetzt:
  1. Scan läuft → „Scan läuft seit 04:00“ (neutral; darunter bleibt der bisherige Stand sichtbar).
  2. Kein `lastUsableRun` → „Noch kein vollständiger Scan“ (Warnung, wenn `lastRun` `failed`).
  3. Sonst „Stand: <lastUsableRun.finishedAt>“ plus Warnzusätze, die sich ergänzen:
     „älter als ein Tag“ (> 26 h), „n Quellen mit Fehlern“ (`incomplete`),
     „letzter Scan fehlgeschlagen“ (`lastRun` ist `failed` und neuer als `lastUsableRun`).
     Mindestens ein Zusatz → Warnung, sonst neutral.
- Die Komponente bekommt `running`/`startedAt` mit; der CVE-Reiter der Anwendung fragt dafür
  ebenfalls `GET /api/ingest/status` ab.

## Stand je Anwendung
- Neue Spalte `application.inventory_changed_at` (`DateTime(timezone=True)`, NULL = Bestand vor
  diesem Feature, gilt als gescannt). Gesetzt beim Anlegen der Anwendung, beim Anlegen, Ändern
  oder Löschen einer Komponente und beim Hochladen oder Löschen einer SBOM bzw. SBOM-Version – in
  den jeweiligen Use Cases (Domain-Methode `Application.mark_inventory_changed(now)`).
- `GET /api/applications/{id}` liefert zusätzlich `inventoryChangedAt`.
- Der CVE-Reiter zeigt „Noch nicht gescannt – Änderungen seit dem letzten Scan“ (Warnung), wenn
  `inventoryChangedAt` nach `lastUsableRun.startedAt` liegt oder es keinen `lastUsableRun` gibt;
  sonst die normale Anzeige. **Meine Festlegung:** Vergleich mit `startedAt`, weil der Scan die
  Komponenten zu Beginn liest. Läuft gerade ein Scan, gilt Zustand 1 („Scan läuft …“).
- Die Schwachstellen-Seite zeigt nur den globalen Stand.

## Tests
- Unit: Nachhol-Entscheidung (kein Lauf / 23 h / 25 h / letzter Lauf `failed`), Ermittlung von
  `outcome` aus den Quellen-Ergebnissen, Reset unterbrochener Läufe – mit Fakes aus `tests/fakes.py`.
- Infrastructure: Scheduler-Adapter registriert genau einen Cron-Job mit Uhrzeit/Zeitzone aus den
  Settings; ungültige Uhrzeit → Fehler; abgeschaltet → kein Job. Kein echtes Warten auf die Uhr.
- API: `GET /api/ingest/status` liefert den gespeicherten letzten Lauf nach „Neustart“ (neuer Runner).
- Frontend (Vitest): alle fünf Zustände der Anzeige über `getByTestId`.

## Dem Builder überlassen
- Genaue Port-Namen (z. B. `ScanRunRepository`, `ScanScheduler`) und Schnitt der Use Cases.
- Ob der Runner den Lauf selbst in `scan_run` schreibt oder der Ingest-Job es übernimmt
  (Hauptsache: auch manuelle Läufe und Abstürze landen dort).
- Prüfen, ob `python:3.13-slim` Zeitzonendaten für `zoneinfo` mitbringt; sonst `tzdata`
  (Python-Paket) ergänzen – das wäre eine weitere Abhängigkeit und vorher abzustimmen.
- Doku: `README.md` und `docs/local-development.md` (Scan läuft täglich, ENV-Werte, Abschalten).
