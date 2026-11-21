# CVE-Export für KI / GitHub-Issues – Design (kurz)

Stand: 2026-11-21

## Absicht
Pro Anwendung eine Markdown-Datei mit allen noch zu bearbeitenden CVEs herunterladen, die man
einer KI gibt – im Chat oder einem Agenten im Repo (z. B. Claude Code mit `gh`) –, damit daraus
GitHub-Issues entstehen, die man nach Risiko geordnet abarbeitet.

Teil 1 von 4. Folgevorhaben: Rückkanal SBOM (Treffer werden „behoben“ statt gelöscht),
Rückkanal API (Agent meldet „behoben“ + Issue), GitHub-Anbindung (Repo-Link je Anwendung,
CVE-Radar legt Issues selbst an und gleicht ihren Status ab).

## Entscheidungen des Nutzers
- **Ein Issue pro CVE** (genauer: pro CVE und Anwendung).
- Eine Datei für beide Wege: Chat und Agent mit `gh`.
- Ansatz **A**: Das Backend erzeugt das Markdown.

## Ziele
- Download im CVE-Reiter der Anwendung („Für KI exportieren“), auch per `curl` abrufbar.
- Jedes Issue nennt Risiko (Score + Stufe + Begründung), sodass die Reihenfolge klar ist.
- Jedes Issue trägt eine feste Kennung, über die spätere Rückkanäle es zuordnen.

## Nicht-Ziele
- Issues selbst anlegen, Status zurückmelden (Folgevorhaben).
- Andere Formate (JSON, CSV), Export über mehrere Anwendungen.

## Anti-Ziele
- Issues für schon Erledigtes (behoben / akzeptiert / false positive).
- Doppelte Issues, wenn der Export erneut verarbeitet wird.

## Ansätze
| | Ansatz | Abwägung |
|---|---|---|
| **A (gewählt)** | Backend-Use-Case + `GET /api/applications/{id}/cves/export` liefert `text/markdown` | Agent kann selbst abrufen; Daten (inkl. Advisory-Beschreibung) an einer Stelle; testbar |
| B | Frontend setzt Markdown aus vorhandenen APIs zusammen | N+1 Anfragen, Fachlogik im Browser, Agent kommt nicht dran |
| C | Backend liefert JSON, Frontend formatiert | Agent bekäme nur JSON ohne Anleitung |

## Inhalt (meine Festlegungen)
- **Auswahl:** Treffer der Anwendung mit Status `offen` oder `in_arbeit`, nur geprüfte, noch
  vorhandene Komponenten (wie die CVE-Liste). Tabellenfilter gelten nicht.
- **Gruppierung:** ein Abschnitt pro Advisory; betrifft sie mehrere Komponenten, stehen alle
  darin. Risiko des Abschnitts = höchster Score der Treffer.
- **Reihenfolge:** Score absteigend, bei Gleichstand Advisory-ID.
- **Kopf der Datei:** Anwendung, Erzeugungszeitpunkt (UTC), Anzahl, und eine Anleitung:
  - pro Abschnitt genau ein Issue; Titel und Labels aus dem Abschnitt übernehmen;
  - vor dem Anlegen vorhandene Issues mit Label `security` samt Text holen
    (`gh issue list --label security --state all --limit 1000 --json number,body`), auf den
    Marker prüfen und vorhandene Issues nicht doppelt anlegen. (Umsetzung: Die GitHub-Suche
    findet HTML-Kommentare nicht verlässlich.)
  - Fremdtexte (Advisory, SBOM-Namen, Triage-Kommentare) werden entschärft: kein `<!--`, kein
    `cve-radar:`; einzeilige Felder ohne Zeilenumbrüche, `|` in Tabellenzellen maskiert.
  - Labels bei Bedarf anlegen; in Score-Reihenfolge anlegen.
- **Pro Abschnitt:**
  - Issue-Titel: `[<score>] <CVE-ID oder Advisory-ID> – <Komponente> <Version>` (bei mehreren
    Komponenten die erste + „u. a.“).
  - Labels: `security`, `risk:<stufe>` (kritisch/hoch/mittel/niedrig).
  - Issue-Text: Risiko (Score, Stufe, Begründung), CVSS, betroffene Komponenten mit gefundener
    Version, Ökosystem und Quelle (manuell / SBOM-Name), Fix-Version bzw. „kein Fix bekannt“,
    vorgeschlagene Maßnahme („auf ≥ <fix> aktualisieren“), Beschreibung (gekürzt auf
    4 000 Zeichen), Referenzen (höchstens 10), Triage-Kommentar falls vorhanden,
    Marker als letzte Zeile.
- **Marker:** `<!-- cve-radar:application=<id>;advisory=<advisory-id> -->` – stabil über
  wiederholte Exporte, unsichtbar im gerenderten Issue.
- Der Issue-Text steht je Abschnitt in einem eigenen Codeblock (````markdown), damit die KI
  ihn unverändert übernehmen kann und Überschriften aus Fremdtexten die Struktur nicht stören.
- **Leer:** keine offenen Treffer → Datei mit Kopf und dem Satz „Keine offenen Schwachstellen.“
- **Dateiname:** `cve-issues-<anwendungsname-slug>-<YYYY-MM-DD>.md` (Content-Disposition).

## Architektur
- `application/issue_export.py`: Use Case `ExportApplicationIssues(uow, store, clock)` →
  `IssueExport` (Anwendung, Zeitpunkt, Liste `IssueDraft` je Advisory). Nutzt vorhandene
  Bausteine (`AdvisoryStore.read_document`, Risk Score).
- `presentation/`: Markdown-Renderer (reine Formatierung) und Endpoint; 404 für unbekannte
  Anwendung.
- Frontend: Button im CVE-Reiter (`inventory-btn-cves-export`), lädt die Datei per Link
  herunter (kein neuer State, kein neues Paket).

## Tests
- Use Case: Auswahl nach Status, Gruppierung mehrerer Komponenten, Sortierung, höchster Score,
  Fallback ohne Advisory-Datei, leere Anwendung, unbekannte Anwendung.
- Renderer: Titel, Labels, Marker, Kürzung, Codeblock-Escaping (Beschreibung mit ```),
  „kein Fix bekannt“.
- API: Content-Type, Content-Disposition, 404.
- Vitest: Button verweist auf den Export-Pfad.

## Offen für den Bauenden
- Exakte Wortwahl der Anleitung; Aufteilung Renderer in Hilfsfunktionen (Komplexität ≤ 8).
