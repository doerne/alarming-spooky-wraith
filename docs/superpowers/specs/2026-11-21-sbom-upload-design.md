# SBOM-Upload im Inventar – Design

Stand: 2026-11-21

## Absicht
Zu einer Anwendung im Inventar sollen sich eine oder mehrere Software-Stücklisten (SBOM) hinterlegen
lassen – typischerweise die vier CycloneDX-Dateien, die die GitHub Action pro Release erzeugt
(`backend-source`, `frontend-source`, `backend-image`, `frontend-image`). Ihre Komponenten werden wie
die manuell gepflegten gegen die Advisories abgeglichen. Das ist die im CVE-Radar-Design (§8) und im
SBOM-Action-Design angekündigte Folgeerweiterung.

## Entscheidungen des Nutzers
- Format: **CycloneDX JSON**. SPDX und CycloneDX XML vorerst nicht.
- Eine SBOM wird **pro Version** gespeichert. Jeder Upload unter demselben SBOM-Namen ist eine neue
  Version; die bisherige wird **archiviert**.
- **CVE-Zuordnung nur für die aktuelle Version** jeder SBOM. Archivierte Versionen werden nicht geprüft.
- Archiv: Man soll sehen, **dass es eine Version gab**, und **ihre Komponentenliste ansehen** können.
  Keine Originaldatei, keine Momentaufnahme der Treffer.
- Ansatz **A** (siehe unten).
- Pakete ohne passendes Ökosystem (v. a. `pkg:deb`, `pkg:apk` aus Image-SBOMs) werden **importiert und
  angezeigt, aber nicht abgeglichen** („nicht geprüft“).

## Ziele
- SBOM hochladen, unter einem Namen pro Anwendung führen, neue Versionen nachladen.
- Versionshistorie je SBOM mit Bezeichnung, Upload-Zeitpunkt und Komponentenliste.
- Komponenten der aktuellen Version fließen in Abgleich, Treffer, Filter und Dashboard ein.
- Status und Kommentar eines Treffers bleiben über Versionswechsel erhalten, solange die Komponente
  (Name, Ökosystem, Version) unverändert bleibt.

## Nicht-Ziele
- SPDX, CycloneDX XML, Protobuf.
- Ablegen der Originaldatei, Download archivierter SBOMs.
- Treffer-Historie archivierter Versionen.
- Debian/Alpine als Ökosysteme mit Versionsvergleich (eigenes Folgevorhaben).
- Automatischer Upload aus der GitHub Action (kein Token, keine Erreichbarkeit nach außen).
- Signaturprüfung der SBOM.

## Anti-Ziele (wäre ein Fehlschlag, auch wenn es „funktioniert“)
- Komponenten verdoppeln sich bei jedem Release-Upload.
- Treffer verlieren Status/Kommentar, obwohl sich die Komponente nicht geändert hat.
- Hunderte OS-Pakete erzeugen Fehltreffer über den Produktnamen-Abgleich.
- Manuelle Komponenten werden durch einen SBOM-Upload verändert oder gelöscht.

## Ansätze
| | Ansatz | Abwägung |
|---|---|---|
| **A (gewählt)** | Aktuelle Version zusätzlich „live“ in `component` (mit `sbom_id`), jede Version als Momentaufnahme (JSON) in `sbom_version` | Abgleich, Treffer, Filter bleiben unverändert; Archiv nur anzeigbar, nicht per SQL durchsuchbar – reicht |
| B | Wie A, Archiv normalisiert in eigener Tabelle `sbom_component` | Durchsuchbar, aber eine Tabelle/Repo/Migration mehr ohne heutigen Nutzen |
| C | Alle Versionen in `component` mit `sbom_version_id` | Jede Abfrage muss „manuell oder aktuell“ filtern; Treffer beim Wechsel umhängen – fehleranfällig |

## Fachmodell (domain)
- `Sbom`: `id`, `application_id`, `name` (eindeutig je Anwendung, 1–100 Zeichen).
- `SbomVersion`: `id`, `sbom_id`, `label`, `uploaded_at`, `serial_number | None`, `is_current`,
  `components: tuple[SbomEntry, ...]`.
- `SbomEntry` (Wertobjekt, Inhalt der Momentaufnahme): `name`, `version`, `purl | None`,
  `ecosystem | None`, `category`, `direct`.
- `Component` bekommt zwei Felder:
  - `sbom_id: int | None` – `None` = manuell gepflegt.
  - `checked: bool` – `False`, wenn kein Ökosystem zugeordnet werden konnte. Manuelle Komponenten sind
    immer `checked=True` (heutiges Verhalten unverändert, inkl. Produkt-/CPE-Abgleich ohne Ökosystem).
- Port `SbomParser` (Protocol): `parse(document: Mapping[str, object]) -> ParsedSbom`
  mit `entries`, `serial_number`, `suggested_label`. Fehler → neue Domain-Fehlerklasse `InvalidSbomError`.
- Neue Repository-Ports `SbomRepository` (add, get, find_by_name, list_for_application, delete) und
  `SbomVersionRepository` (add, list_for_sbom, get, mark_archived) sowie Erweiterungen:
  `ComponentRepository.delete`, `ComponentRepository.list_for_sbom`,
  `FindingRepository.delete_for_component`. Die UnitOfWork bekommt `sboms` und `sbom_versions`.

## Abgleich (Ansatz A im Detail)
Schlüssel einer Komponente: `(ecosystem, normalize_package_name(ecosystem, name), version)`.

Upload einer neuen Version für SBOM *S* (Use Case `UploadSbomVersion`):
1. SBOM *S* per Name suchen, sonst anlegen.
2. Ist `serial_number` gesetzt und gleich der der aktuellen Version → `DuplicateSbomVersionError` (409).
3. Bisherige aktuelle Version als archiviert markieren, neue Version mit Momentaufnahme als aktuell anlegen.
4. Live-Komponenten von *S* (`component` mit `sbom_id = S`) gegen die neuen Einträge abgleichen:
   - Schlüssel in beiden → Komponente bleibt (inkl. Treffern); `category`, `direct`, `checked` werden aktualisiert.
   - nur alt → Treffer der Komponente löschen, Komponente löschen.
   - nur neu → Komponente anlegen.
5. `uow.commit()`.

Doppelte Einträge innerhalb einer SBOM (gleicher Schlüssel) werden zu einem zusammengefasst
(`direct` = irgendeiner direkt).

Der Ingest-Lauf (`IngestUseCase`) berücksichtigt nur Komponenten mit `checked=True`. Neue Treffer
erscheinen beim nächsten Ingest-Lauf (täglich oder manuell ausgelöst); der Upload löst keinen Lauf aus.

`DeleteSbom` entfernt alle Versionen, die Live-Komponenten von *S* und deren Treffer.

## CycloneDX-Parser (infrastructure, `infrastructure/sbom/cyclonedx.py`)
- Pflicht: `bomFormat == "CycloneDX"`, `specVersion` 1.4–1.7, `components` ist eine Liste.
  Sonst `InvalidSbomError` mit verständlicher Meldung (422).
- Komponenten rekursiv inkl. verschachtelter `components` einlesen; `metadata.component` selbst ist
  keine Komponente.
- Nur Typen `library`, `framework`, `application`; `operating-system`, `file`, `container`, `device`,
  `data` u. a. werden ignoriert.
- Ökosystem aus der purl über die bestehende Zuordnung in `infrastructure/sources/purl.py`
  (Umkehrabbildung ergänzen). Kein purl oder unbekannter purl-Typ → `ecosystem=None`, `checked=False`.
- Name: bei Maven `group:name`, bei npm mit Scope `@scope/name`, bei Go der volle Modulpfad – passend
  zu dem, was die Quellen erwarten (`purl.py` zeigt das Gegenstück).
- Kategorie: CycloneDX `framework` → `framework`, sonst `library`.
- `direct`: Komponente steht in `dependencies` unter `dependsOn` von `metadata.component.bom-ref`.
  Fehlt der Abhängigkeitsgraph, gelten alle als direkt.
- Komponenten ohne `version` oder mit zu langem Namen (> 200) bzw. zu langer Version (> 100,
  Spaltenlängen in `component`) werden übersprungen und gezählt (`skipped`).
- Vorschlag für die Versionsbezeichnung: `metadata.component.version`, sonst `metadata.timestamp`,
  sonst Upload-Zeitpunkt.

## API (presentation, camelCase)
- `GET  /api/applications/{id}/sboms` → Liste: `id`, `name`, aktuelle Version (`label`, `uploadedAt`,
  `componentCount`, `uncheckedCount`), `versionCount`.
- `POST /api/applications/{id}/sboms/versions` Body `{ name, label?, document }`
  (`document` = geparstes CycloneDX-JSON) → angelegte Version + Zusammenfassung
  (`added`, `removed`, `kept`, `unchecked`, `skipped`). 201.
- `GET  /api/applications/{id}/sboms/{sbomId}/versions` → Versionshistorie ohne Komponenten.
- `GET  /api/applications/{id}/sboms/{sbomId}/versions/{versionId}` → Version mit Komponentenliste.
- `DELETE /api/applications/{id}/sboms/{sbomId}` → 204.
- `ComponentResponse` bekommt `sbomId`, `sbomName` und `checked`.
- `PUT …/components/{id}` auf eine SBOM-Komponente → 409 (`ComponentManagedBySbomError`),
  weil die nächste Version sie überschreiben würde.
- Fehler-Mapping: `InvalidSbomError` → 422, `DuplicateSbomVersionError` → 409.

## Upload-Weg und Grenzen
- Das Frontend liest die Datei (`File.text()`, `JSON.parse`) und schickt JSON. Kein Multipart, also
  keine neue Abhängigkeit (`python-multipart` fehlt).
- nginx: `client_max_body_size 1m` bleibt global; eigener `location` für
  `/api/applications/…/sboms/versions` mit **25m** (Sicherheits-Header dort wiederholen, siehe Kommentar
  in `nginx.conf`).
- Backend: höchstens 50 000 Komponenten je Dokument, sonst 422.

## Oberfläche (frontend, feature `inventory`)
Neuer Tab **„SBOMs“** in der Anwendungsdetailseite neben „Komponenten“ und „CVEs“:

```
SBOMs                                            [ SBOM hochladen ]
┌───────────────────────────────────────────────────────────────┐
│ backend-image   v1.4.0 · 21.11.2026 · 412 Komp. (318 n. gepr.)│
│                 3 Versionen  [Neue Version] [Verlauf] [🗑]    │
│ frontend-source v1.4.0 · 21.11.2026 · 287 Komp.              │
└───────────────────────────────────────────────────────────────┘
```

- **Hochladen-Dialog**: Datei wählen, Name (Vorbelegung aus `metadata.component.name` bzw. bei
  „Neue Version“ fest), Versionsbezeichnung (vorbelegt, änderbar). Nach Erfolg kurze Zusammenfassung
  (hinzugefügt / entfernt / unverändert / nicht geprüft) und Hinweis, dass Treffer nach dem nächsten
  Abgleich erscheinen.
- **Verlauf**: Liste der Versionen (Bezeichnung, Zeitpunkt, Anzahl, „aktuell“/„archiviert“); Klick
  öffnet die Komponentenliste der Version (nur lesend: Name, Version, Ökosystem, purl, geprüft).
- **Löschen** mit Bestätigungsdialog (nennt die Zahl der betroffenen Komponenten).
- **Tab „Komponenten“**: neue Spalte „Quelle“ (manuell / SBOM-Name), Badge „nicht geprüft“;
  Bearbeiten nur bei manuellen Komponenten.
- shadcn: vorhandene `tabs`, `table`, `dialog`, `alert-dialog`, `badge`, `field` nutzen; fehlende per
  `npx shadcn@latest add`. Test-IDs nach Schema, z. B. `inventory-btn-sbom-upload`,
  `inventory-item-sbom-${id}`, `inventory-dialog-sbom-upload`.

## Datenbank
Eine Alembic-Migration:
- `sbom` (`id`, `application_id` FK, `name` String(100), Unique `(application_id, name)`).
- `sbom_version` (`id`, `sbom_id` FK, `label` String(100), `uploaded_at` DateTime tz,
  `serial_number` String(100) nullable, `is_current` bool, `components` JSON).
- `component`: `sbom_id` FK nullable, `checked` bool default true (Bestandsdaten → true).

## Tests
- Domain/Use Cases mit Fakes aus `tests/fakes.py`: erster Upload, neue Version (behalten / entfernen /
  hinzufügen, Treffer bleiben bzw. verschwinden), doppelte Seriennummer, Löschen, Schutz manueller
  Komponenten, Ingest ignoriert `checked=False`.
- Parser: kleine CycloneDX-Fixtures (npm mit Scope, PyPI, Maven, deb, verschachtelt, ohne
  Abhängigkeitsgraph, falsches Format, ohne Version).
- API-Tests für alle Endpoints inkl. 409/422.
- Vitest über `getByTestId`: SBOM-Liste, Upload-Dialog (inkl. ungültiger Datei), Verlauf,
  Spalte „Quelle“ und Badge.

## Meine Festlegungen (vom Nutzer nicht ausdrücklich entschieden)
- Versionsbezeichnung aus der SBOM vorbelegt, beim Upload überschreibbar; Bezeichnungen müssen nicht
  eindeutig sein.
- Gleiche Seriennummer wie die aktuelle Version → Ablehnung (409).
- Treffer verschwundener Komponenten werden gelöscht, nicht als „behoben“ markiert.
- SBOM-Komponenten sind nicht von Hand bearbeitbar.
- Upload als JSON-Body statt Multipart; Grenze 25 MB / 50 000 Komponenten.
- Kein Ingest-Lauf direkt nach dem Upload.

## Offen für den Bauenden
- Genaue Aufteilung der Use-Case-Klassen und Hilfsfunktionen (Komplexität ≤ 8).
- Ob die Umkehrabbildung purl-Typ → Ökosystem in `purl.py` oder im Parser liegt.
- Layout-Feinheiten der Tabelle/Dialoge im Rahmen des Haus-Themes.
