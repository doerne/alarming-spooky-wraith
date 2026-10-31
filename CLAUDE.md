# alarming-spooky-wraith

Vite + React + shadcn/ui in `frontend/`, FastAPI in `backend/`, MariaDB in Docker.
Angelegt mit dem Plugin `fullstack-standards` (Marker: `.claude/fullstack-standards.json`).

Für neue Arbeit die Plugin-Skills nutzen:
`/fullstack-standards:backend-feature` · `/fullstack-standards:react-component` ·
`/fullstack-standards:db-migration` · `/fullstack-standards:harden-check`.
Sie enthalten ein vollständiges Referenz-Feature als Vorlage.

## Befehle (immer im Projekt-Root)

- Alles prüfen: `make check` – muss grün sein, bevor du fertig meldest
- Dev: `make dev-services` (DB + Backend in Docker), dann `cd frontend && npm run dev`
- Backend: `cd backend && uv run pytest` · `uv run ruff check .` · `uv run mypy` · `uv run lint-imports`
- Frontend: `cd frontend && npx vitest run` · `npx eslint .` · `npx tsc -b`
- Migration: `cd backend && uv run alembic revision --autogenerate -m "..."`, dann `make migrate`
- shadcn: immer in `frontend/` → `npx shadcn@latest add <komponente>`

## Architektur (wird von `make check` erzwungen)

Backend `backend/app/`:
- `domain/` Entities, Value Objects, Fehler, Repository-Ports (Protocol). Kein Framework.
- `application/` Use Cases, eine Klasse pro Anwendungsfall, `execute()`. Kennt nur domain.
- `infrastructure/` SQLAlchemy-Modelle, Repository- und UnitOfWork-Implementierungen, Settings.
- `presentation/` FastAPI-Router, Pydantic-DTOs (`ApiModel`, camelCase), Fehler-Mapping.
- `main.py` Composition Root – einziger Ort, der alles verdrahtet.
- presentation und infrastructure kennen sich gegenseitig NICHT.
- Use Cases rufen `uow.commit()` selbst auf. Router enthalten keine Logik.

Frontend `frontend/src/`:
- `app/` Layout, Provider, Routing. Importiert Features nur über deren `index.ts`.
- `features/<name>/` `model/` (Typen, zod) · `api/` · `hooks/` (TanStack Query) · `components/`
- `shared/` `ui/` (shadcn), `components/` (eigene Kompositionen), `lib/`, `hooks/`, `api/`
- Features importieren nur `shared`, nie andere Features.
- Container-Komponente (`*-page.tsx`) holt Daten, alle anderen Komponenten sind rein und bekommen Props.

## Clean Code

- Kleine Funktionen mit einem Zweck, sprechende Namen, keine Abkürzungen.
- Python: Typ-Hints überall (mypy strict), max. Komplexität 8, max. 5 Parameter.
- TypeScript: strict, kein `any`, max. Komplexität 8, max. 4 Parameter.
- Kein toter Code, keine auskommentierten Blöcke.
- Jede Änderung mit Test: Domain/Use Case → Unit-Test mit Fakes aus `tests/fakes.py`; Router → API-Test; Komponente → Vitest über `getByTestId`.

## UI (shadcn/ui)

- Zuerst per shadcn-MCP oder `npx shadcn@latest search` prüfen, ob es eine Komponente/einen Block gibt.
- `src/shared/ui/` nie direkt editieren (Hook blockiert das). Anpassungen als Wrapper in `shared/components/`.
- Das Theme in `src/index.css` ist der Hausstandard. Nur auf ausdrücklichen Wunsch ändern.
- Nur semantische Farben: `bg-primary`, `text-muted-foreground`, `border-border` … keine Palette wie `bg-teal-600`.
- Formulare: `Field` + `FieldLabel` + `FieldError` mit React Hook Form + zod.
- Icons: lucide-react.

## Test-IDs

Jedes interaktive Element, jeder Container und jede Liste bekommt `data-testid="<feature>-<element>-<zweck>"`,
kebab-case, mindestens drei Teile. Beispiele: `orders-btn-create`, `orders-input-title`, `orders-item-${id}`.
Element-Kürzel: btn, input, select, checkbox, form, list, item, card, dialog, text, error, link, tab.

## Container

- Alle Dienste: non-root, `read_only`, `cap_drop: ALL`, `no-new-privileges`, Ressourcenlimits.
- Secrets nur über Docker Secrets (`*_FILE`), nie in ENV-Werten, Images oder im Code.
- DB nur im internen Netz `data`. Neue Ports nur in `compose.dev.yaml` und nur auf 127.0.0.1.

## Nicht tun

- Keine Dateien in `secrets/` lesen oder ändern.
- Kein `docker compose down -v` (löscht die Datenbank).
- Keine neuen Abhängigkeiten ohne Rückfrage.
