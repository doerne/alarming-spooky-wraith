# Normalisiert eine CycloneDX-SBOM für den Vergleich zweier Läufe. Ausgeblendet wird,
# was sich bei jedem Lauf ändert, ohne dass sich der Inhalt ändert:
# - Seriennummer und Zeitstempel,
# - zufällige UUID-Referenzen,
# - Image-/Layer-Hashes (ein frischer Build hat immer neue IDs, auch bei gleichen Paketen),
# - die Reihenfolge von Komponenten und Abhängigkeiten.
def is_uuid: test("^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$");
def volatile_property:
  .name | IN(
    "aquasecurity:trivy:ImageID",
    "aquasecurity:trivy:DiffID",
    "aquasecurity:trivy:RepoDigest",
    "aquasecurity:trivy:LayerDiffID",
    "aquasecurity:trivy:LayerDigest"
  );

del(.serialNumber, .metadata.timestamp)
| walk(if type == "object" and has("properties") and (.properties | type) == "array"
       then .properties |= map(select(volatile_property | not))
       else . end)
| walk(if type == "string" then
         (if is_uuid then "UUID" else gsub("sha256:[0-9a-f]+"; "sha256:DIGEST") end)
       else . end)
| if .components then .components |= sort_by(.purl // "", .name, .version // "") else . end
| if .dependencies then
    .dependencies |= (map(if .dependsOn then .dependsOn |= sort else . end)
                      | sort_by(.ref, (.dependsOn // [] | tostring)))
  else . end
