# Software-Stücklisten (SBOM)

Diese Dateien erzeugt der Workflow `.github/workflows/sbom.yml` automatisch mit
[Trivy](https://trivy.dev) im Format [CycloneDX](https://cyclonedx.org) (JSON). Nicht von Hand ändern.

| Datei | Inhalt |
|---|---|
| `backend-source.cdx.json` | Python-Pakete aus `backend/uv.lock` |
| `frontend-source.cdx.json` | npm-Pakete aus `frontend/package-lock.json` |
| `backend-image.cdx.json` | Backend-Docker-Image: Basis-Image, Debian-Pakete, Python-Umgebung |
| `frontend-image.cdx.json` | Frontend-Docker-Image: nginx-Basis-Image und dessen Pakete |

**Wann aktualisiert:** bei Pushes auf `main`, die Lockfiles, Dockerfiles oder `compose.yaml`
ändern; jeden Montag; manuell unter *Actions → SBOM → Run workflow*.

Ein Commit entsteht nur, wenn sich der Inhalt ändert. Zufällige IDs, Seriennummer und
Zeitstempel, die Trivy bei jedem Lauf neu vergibt, zählen nicht als Änderung
(`.github/scripts/sbom-normalize.jq`).
