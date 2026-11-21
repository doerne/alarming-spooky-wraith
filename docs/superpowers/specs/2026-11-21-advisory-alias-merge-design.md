# Advisories über Aliase zusammenführen – Design (kurz)

Stand: 2026-11-21

## Absicht
Dieselbe Schwachstelle ohne CVE-ID kommt von mehreren Quellen unter verschiedenen IDs
(z. B. `GHSA-6q48-6c7w-9gw2` von OSV, `PYSEC-2026-4320` von PyPA mit GHSA als Alias). Heute
werden daraus zwei Advisories, zwei Treffer und im Export zwei Issues. Vor den Rückkanälen
(Marker hängen an der Advisory-ID) soll es pro Schwachstelle genau eine Advisory geben.

## Entscheidungen des Nutzers
Design wie vorgeschlagen freigegeben (siehe unten).

## Ansätze
| | Ansatz | Abwägung |
|---|---|---|
| **A (gewählt)** | Scan gruppiert über ID + Aliase (transitiv), kanonische ID, Bereinigung vorhandener Duplikate | Ein Datensatz pro Lücke; Altbestand heilt beim nächsten Scan |
| B | Nur in Anzeige/Export zusammenfassen | Treffer und Marker bleiben auf zwei IDs verteilt |
| C | Zusammenführen von Hand in der Oberfläche | Wiederkehrende Handarbeit nach jedem Scan |

## Design
- **Gruppierung:** Treffer eines Laufs werden über alle IDs (`vuln.id` + `aliases`) zu
  Gruppen verbunden (Union-Find, transitiv).
- **Kanonische ID:** kleinste CVE-ID der Gruppe; sonst kleinste GHSA-ID; sonst kleinste ID.
  `cve_id` = kanonische ID, falls CVE, sonst `None`. Inhalte (Titel, CVSS, Fix …) weiter nach
  der bestehenden Quellen-Rangfolge.
- **`MergedAdvisory.aliases`:** alle IDs der Gruppe außer der kanonischen (sortiert).
- **Bereinigung beim Speichern** (nach dem Upsert der kanonischen Advisory, vor den Treffern):
  für jede Alias-ID, unter der eine Advisory existiert:
  - Treffer umhängen; gibt es für dieselbe Komponente schon einen kanonischen Treffer, beide
    zusammenführen: ist der kanonische `offen`, übernimmt er den Status des anderen; nicht leere
    Kommentare werden mit Leerzeile aneinandergehängt; der Alias-Treffer wird gelöscht;
  - Alias-Advisory-Zeile und ihre OKF-Datei löschen.
- **Alte IDs merken:** Tabelle `advisory_alias` (`alias_id` PK, `advisory_id`), Upsert für
  jede Alias-ID einer Gruppe – für spätere Zuordnung alter Issue-Marker. Zeigt ein Alias auf eine
  inzwischen anders kanonische ID, wird er überschrieben.
- Kein eigener Migrationsschritt für Daten: der nächste Scan heilt den Bestand.

## Nicht-Ziele
Auflösen alter Marker im Export/den Rückkanälen (nutzen die Tabelle später); Zusammenführen
über Läufe ohne gemeinsame Aliase.

## Tests
Gruppierung (direkt, transitiv, getrennt), kanonische ID (CVE > GHSA > min), Bereinigung
(Umhängen, Zusammenführen mit Status/Kommentar, Löschen von Zeile und Datei, Alias-Tabelle),
Ingest-Ende-zu-Ende mit GHSA + PYSEC, Repository-Tests der neuen Methoden.
