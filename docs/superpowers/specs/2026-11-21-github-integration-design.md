# GitHub-Anbindung: Issues anlegen und Status abgleichen – Design

Stand: 2026-11-21 · Teil 4 von 4 (nach Export, Alias-Zusammenführung, Rückkanal SBOM, Rückkanal API)

## Absicht
CVE-Radar legt für offene CVEs einer Anwendung selbst GitHub-Issues im Repo der Anwendung an
und gleicht ihren Status ab: geschlossene Issues zählen als (vorläufig) behoben, von CVE-Radar
wieder geöffnete Treffer öffnen das Issue wieder. So lässt sich die Arbeit nach Risiko in
GitHub abarbeiten, ohne einen Agenten dazwischen.

## Entscheidungen des Nutzers
- **GitHub App** statt persönlichem Token (wie in seiner Arbeitsumgebung): App in der
  Organisation anlegen, in den Repos installieren; App-ID und privater Schlüssel als Secret.
- Neue Abhängigkeit **`PyJWT[crypto]`** für das RS256-JWT freigegeben.
- **Anlegen:** Mischung – Button im CVE-Reiter (alle offenen CVEs ohne Issue, optional mit
  Mindest-Risiko) **plus** Option je Anwendung „neue CVEs ab Risiko X automatisch anlegen“
  (Standard: aus).
- Issue-Inhalt wie im Export (Titel, Labels, Text, Marker); vor dem Anlegen Duplikatprüfung
  über den Marker.
- **Abgleich:** geschlossenes Issue → „behoben“ (gemeldet, vorläufig bis SBOM-Nachweis);
  auf GitHub wieder geöffnetes Issue → „offen“. CVE-Radar öffnet ein Issue wieder (mit
  Kommentar), wenn es den Treffer wieder öffnet.
- Ansatz **A**: eigener Sync-Schritt nach dem Scan, eigene Transaktion, plus Button
  „Mit GitHub abgleichen“.
- **Automatik nur für wirklich neue Treffer** (1a): angelegt werden nur Treffer, die nach dem
  Einschalten der Option entdeckt wurden; der Altbestand läuft über den Button.
- **„akzeptiert“ / „false positive“** (2a): ein auf GitHub geschlossenes Issue überschreibt sie
  nicht; setzt der Nutzer einen Treffer darauf, schließt CVE-Radar das Issue als
  `not_planned` mit Kommentar; ein auf GitHub als `not_planned` geschlossenes Issue macht
  offene Treffer zu „akzeptiert“ (statt „behoben“).

## Ziele
- Repo je Anwendung (`owner/repo`) und Auto-Anlage-Schwelle pflegen.
- Issues anlegen (manuell / automatisch), ohne Duplikate, in Risiko-Reihenfolge.
- Status zweiseitig abgleichen, ohne dass die Seiten sich gegenseitig überschreiben.
- GitHub-Fehler (nicht konfiguriert, App nicht installiert, Rate-Limit, Netz) brechen weder
  den Scan noch andere Anwendungen ab und sind im CVE-Reiter sichtbar.

## Nicht-Ziele
- Webhooks (CVE-Radar ist von GitHub aus nicht erreichbar).
- Andere Tracker (GitLab, Jira) – der Port lässt es später zu.
- Issues bei Änderungen der Advisory nachträglich bearbeiten (Titel/Text bleiben wie angelegt).
- Labels/Assignees/Milestones über `security`, `risk:<stufe>` hinaus.
- Eigener Zeitplan (Sync läuft nach dem Scan und per Button).

## Anti-Ziele
- Hunderte Issues ungewollt auf einen Schlag (deshalb Auto-Anlage standardmäßig aus).
- Flackern: Issue zu → CVE-Radar öffnet → Issue wieder zu → …
- Ein GitHub-Problem verhindert den Scan oder verliert Scan-Ergebnisse.
- App-Schlüssel im Image, in ENV-Werten, im Log oder in API-Antworten.

## Ansätze
| | Ansatz | Abwägung |
|---|---|---|
| **A (gewählt)** | Use Case `SyncGitHubIssues` nach dem Scan im selben Thread, eigene Transaktion; Button startet ihn ebenfalls im Hintergrund | GitHub-Fehler isoliert; Scan unberührt; ein Runner-Muster |
| B | Im Scan vor dem Commit | Fehler/Langsamkeit von GitHub rollt den Scan zurück |
| C | Eigener Zeitplan (z. B. stündlich) | Zweiter Runner; Nachweis kommt ohnehin erst mit der SBOM |

## Konfiguration und Betrieb
- **GitHub App** (vom Nutzer angelegt): Repository-Rechte *Issues: Read & write*, *Metadata:
  Read*; kein Webhook. Installation in den gewünschten Repos.
- **Settings** (`infrastructure/config.py`): `github_app_id: str | None` (ENV
  `GITHUB_APP_ID`, keine Geheimsache), `github_app_private_key_file: Path`
  (Standard `/run/secrets/github_app_private_key`), `github_api_url`
  (Standard `https://api.github.com`).
- **Docker Secret** `github_app_private_key` (`./secrets/github_app_private_key.pem`) am
  Backend. `scripts/generate-secrets.sh` legt die Datei **leer** an, falls sie fehlt, damit
  Compose ohne GitHub startet. Leere Datei oder fehlende App-ID → GitHub „nicht konfiguriert“.
- Der Schlüssel wird nur im Adapter gelesen, nie geloggt oder ausgegeben.

## Datenmodell
- `Application`: `github_repository: str | None` (`owner/repo`, Muster
  `^[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}$`), `auto_issue_min_level: Severity | None`
  (None = keine Automatik), `github_synced_at: datetime | None`,
  `github_sync_message: str` (letztes Ergebnis/Fehler, ≤ 500).
- `Finding`: zusätzlich `issue_state: IssueState | None` (`open` / `closed`) – der zuletzt
  bei GitHub gesehene Zustand – und `first_seen_at: datetime | None` (beim ersten Upsert
  gesetzt; Bestand: NULL = „vor der Automatik“).
- `Application.auto_issue_enabled_at: datetime | None` – gesetzt beim Einschalten bzw. Ändern
  der Schwelle; Automatik legt nur Treffer mit `first_seen_at ≥ auto_issue_enabled_at` an. Grundlage, um zu erkennen, welche Seite sich geändert hat.
  `issue_url` (vorhanden) wird beim Anlegen/Verknüpfen gesetzt.
- Migration für die neuen Spalten.

## Port und Adapter
```python
# domain/ports.py
@dataclass(frozen=True)
class TrackedIssue:
    number: int
    url: str
    is_open: bool
    not_planned: bool = False          # geschlossen mit state_reason "not_planned"

class IssueTracker(Protocol):
    def is_configured(self) -> bool: ...
    def existing_markers(self, repository: str) -> dict[str, TrackedIssue]:
        """Marker-Zeile → Issue, für alle Issues mit Label `security` (alle Zustände)."""
    def get(self, repository: str, number: int) -> TrackedIssue: ...
    def create(self, repository: str, draft: IssueContent) -> TrackedIssue: ...
    def set_open(
        self, repository: str, number: int, is_open: bool, comment: str, not_planned: bool = False
    ) -> None: ...

@dataclass(frozen=True)
class IssueContent:
    title: str
    body: str
    labels: tuple[str, ...]

class IssueFormatter(Protocol):
    """Erzeugt Titel/Text/Labels eines Issues aus einem IssueDraft (wie der Export)."""
    def format(self, application_id: int, draft: IssueDraft) -> IssueContent: ...
```
- Fehler des Trackers: neue `IssueTrackerError(DomainError)` mit verständlicher Meldung
  (nicht konfiguriert, App im Repo nicht installiert, Zugriff verweigert, Rate-Limit, Netz).
- **`IssueFormatter`-Implementierung** in `presentation/issue_export_markdown.py` (nutzt die
  bestehenden Funktionen für Titel, Labels, Body inkl. Marker); verdrahtet in `main.py`.
  `IssueDraft` liegt bereits in `application/issue_export.py`.
- **Adapter** `infrastructure/github/app_client.py` (`GitHubAppIssueTracker`, `httpx`):
  - App-JWT (RS256, `iat` −60 s, `exp` +9 min) mit `PyJWT`;
  - Installation je Repo: `GET /repos/{owner}/{repo}/installation`; Installations-Token
    `POST /app/installations/{id}/access_tokens`, im Speicher bis 5 min vor Ablauf gecacht;
  - `existing_markers`: `GET /repos/{r}/issues?labels=security&state=all&per_page=100`
    seitenweise (Link-Header), Pull Requests ignorieren, Marker per Regex aus dem Body;
  - `create`: `POST /repos/{r}/issues`; fehlende Labels vorher anlegen
    (`POST /repos/{r}/labels`, 422 „already exists“ ignorieren); zwischen zwei Anlagen
    **1 s Pause** (sekundäres Rate-Limit);
  - `set_open`: Kommentar `POST …/issues/{n}/comments`, dann `PATCH …/issues/{n}`
    (`state`, beim Schließen `state_reason: completed`);
  - 401/403/404 → `IssueTrackerError` mit Klartext; 403/429 mit Rate-Limit-Headern →
    „Rate-Limit erreicht“.

## Use Case `SyncGitHubIssues`
`application/github_sync.py`:
```python
@dataclass(frozen=True)
class SyncRequest:
    application_id: int | None          # None = alle Anwendungen mit Repo
    create_issues: bool                 # Button „Issues anlegen“
    min_level: Severity | None          # Mindest-Risiko für den Button

class SyncGitHubIssues:
    def __init__(self, uow, tracker: IssueTracker, formatter: IssueFormatter,
                 drafts: ExportApplicationIssues, clock) -> None
    def execute(self, request: SyncRequest) -> list[SyncOutcome]
```
Je Anwendung mit Repo, in dieser Reihenfolge, Fehler je Anwendung abgefangen und in
`github_sync_message` vermerkt (nächste Anwendung läuft weiter); ein Commit je Anwendung:

1. **Abgleich bestehender Issues** (je Advisory der Anwendung mit `issue_url` in diesem Repo;
   Nummer aus der URL; alle Treffer der Anwendung zu dieser Advisory gemeinsam, ein Issue je
   CVE und Anwendung). „Aktive“ Treffer = an nicht ausgebauten Komponenten; der
   **Gesamtzustand** der CVE in CVE-Radar:
   - *offen*: mindestens ein aktiver Treffer `offen` / `in_arbeit`;
   - *bewertet*: kein offener, aber aktive `akzeptiert` / `false_positive`;
   - *behoben*: keiner offen/bewertet und mindestens ein Treffer `behoben` (auch ausgebaute).
   `get`, dann:
   | gespeichert → jetzt (GitHub) | Gesamtzustand | Aktion |
   |---|---|---|
   | (keiner) → closed, completed | offen | Treffer „behoben“ (gemeldet) – Ausgangsstand, nicht wieder öffnen |
   | (keiner) → closed, not_planned | offen | Treffer „akzeptiert“ |
   | (keiner) → open | beliebig | nur Ausgangsstand merken, weiter wie „unverändert open“ |
   | open → closed, completed | offen | aktive offene Treffer „behoben“ (gemeldet), Auflösung „Issue #n geschlossen“ |
   | open → closed, not_planned | offen | aktive offene Treffer „akzeptiert“, Notiz „Issue #n als not planned geschlossen“ |
   | closed → open | behoben / bewertet | aktive Treffer `reopened()` + Notiz „Issue #n wieder geöffnet“ |
   | unverändert open | behoben, mind. ein SBOM-Nachweis | Issue schließen (completed), Kommentar „Behoben: <resolution>“ |
   | unverändert open | bewertet | Issue schließen (not_planned), Kommentar „In CVE-Radar als <status> bewertet“ |
   | unverändert closed | offen | Issue wieder öffnen, Kommentar = letzte Notiz eines offenen Treffers |
   | sonst | – | nichts |
   Ein geschlossenes Issue überschreibt nie `akzeptiert` / `false_positive`. Danach
   `issue_state` aller Treffer der CVE = Zustand nach der Aktion. Ausgebaute Treffer: nur
   Verknüpfung/Zustand, keine Statusänderung.
2. **Anlegen** (wenn `create_issues` oder `auto_issue_min_level` gesetzt): Drafts aus
   `ExportApplicationIssues` (offen / in Arbeit, nach Risiko sortiert), ohne vorhandene
   `issue_url`, Risiko ≥ Schwelle (`min_level` des Buttons bzw. `auto_issue_min_level`);
   bei der Automatik zusätzlich nur Drafts, deren jüngster Treffer
   `first_seen_at ≥ auto_issue_enabled_at` hat.
   Für jeden Draft: Marker in `existing_markers` → nur verknüpfen (URL, Zustand); sonst
   `create`. Treffer erhalten `issue_url` und `issue_state`.
3. `github_synced_at`, `github_sync_message` („3 angelegt, 1 geschlossen, 2 verknüpft“ bzw.
   Fehlertext) speichern, commit.

Status-Rangfolge Risiko: `niedrig` < `mittel` < `hoch` < `kritisch` (Hilfsfunktion in der
Domain).

## Ablauf und Runner
- `run_ingest_job` ruft nach dem Commit des Scans in **eigener** Unit of Work
  `SyncGitHubIssues(SyncRequest(None, create_issues=False, min_level=None))` auf, nur wenn
  der Tracker konfiguriert ist. Ausnahmen werden geloggt, das Scan-Ergebnis bleibt.
- **Eine gemeinsame Sperre für Scan und Abgleich:** der vorhandene Runner wird zu einem
  `ThreadJobRunner`, der beide Job-Arten nacheinander, nie gleichzeitig, ausführt (verhindert
  doppelt angelegte Issues und gegenseitiges Überschreiben).
- Manueller Start: `POST /api/applications/{id}/github/sync`
  Body `{ "createIssues": bool, "minLevel": Severity | null }` → 202; läuft im
  Hintergrund über denselben Runner; 409 wenn schon ein Scan oder Abgleich läuft,
  503 wenn GitHub nicht konfiguriert ist.
- `GET /api/applications/{id}` liefert zusätzlich `githubRepository`,
  `autoIssueMinLevel`, `githubSyncedAt`, `githubSyncMessage`; `GET /api/github/status`
  liefert `{ configured: bool, running: bool }`.
- `PATCH /api/applications/{id}` mit `githubRepository` (Muster s. o., `null` zum Entfernen)
  und `autoIssueMinLevel` (`null` = aus).

## Oberfläche (feature `inventory`)
- **Anwendung bearbeiten:** kleiner Dialog im Detail-Kopf („GitHub“-Button) mit Feldern
  Repository (`owner/repo`) und „Neue CVEs automatisch anlegen ab“ (Select: aus / kritisch /
  hoch / mittel / niedrig). RHF + zod.
- **CVE-Reiter:** neben „Für KI exportieren“:
  - „Issues in GitHub anlegen“ (Dialog mit Mindest-Risiko, Standard „hoch“), startet Sync mit
    `createIssues: true`;
  - „Mit GitHub abgleichen“ (ohne Anlegen);
  - Statuszeile „Letzter Abgleich: <Zeit> · <Meldung>“; Buttons deaktiviert, wenn kein Repo
    hinterlegt, GitHub nicht konfiguriert oder ein Sync läuft (mit Hinweistext).
  - Tabelle: Spalte/Link „Issue“ (öffnet `issue_url` in neuem Tab, `rel="noopener"`).
- Test-IDs nach Schema (`inventory-btn-github-sync`, `inventory-dialog-github-settings` …).

## Sicherheit
- Schlüssel nur als Docker Secret, gelesen im Adapter; JWT/Token nie geloggt; Fehlermeldungen
  ohne Token-Inhalte.
- Issue-Texte durchlaufen dieselbe Entschärfung wie der Export.
- `github_repository` streng validiert (kein Pfad-Trick in API-URLs).
- Container-Härtung bleibt (read_only, non-root); kein neuer Port.

## Tests
- Domain: Risiko-Rangfolge, `IssueState`.
- Use Case mit `FakeIssueTracker`: Anlegen (Schwelle, Reihenfolge, Duplikat per Marker,
  vorhandene URL), Abgleich-Tabelle (alle Zeilen), Fehler je Anwendung isoliert,
  ausgebaute Komponenten, Auto-Anlage nach Scan.
- Adapter mit `httpx.MockTransport`: JWT-Aufbau (mit Testschlüssel), Installations-Token und
  Cache, Paginierung, Labels anlegen, Fehlerabbildung (401/403/404/429).
- API: PATCH Anwendung (Validierung), Sync-Start (202/409/503), Detailfelder.
- Frontend: Einstellungsdialog, Buttons/Zustände, Issue-Link.
- Echter Durchlauf gegen ein Test-Repo des Nutzers (sobald App angelegt).

## Offen für den Bauenden
- Aufteilung des Adapters in Hilfsfunktionen (Komplexität ≤ 8), genaue Fehlertexte.
- Ob `ThreadJobRunner` generisch über einen Typparameter oder einfache Zustandsklasse.

## Festlegungen des Designers nach Builder-Check
- Schließen erst, wenn kein aktiver Treffer der CVE mehr offen/in Arbeit ist und mindestens
  einer per SBOM bestätigt behoben ist (auch ausgebaute zählen); Wiederöffnen, sobald einer
  offen ist.
- Vorhandene Links ohne gespeicherten Zustand: erster Abgleich = Ausgangsstand; geschlossen
  bei offenem Treffer → „behoben (gemeldet)“ (nicht wieder öffnen).
- Scan und Abgleich teilen eine Sperre (ein Runner).
