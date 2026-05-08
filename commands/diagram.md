---
description: "Generate or update project diagrams by scanning actual code — architecture, API, database, infrastructure."
scope: project
argument-hint: "<type> [--update]"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# /diagram — Generate Project Diagrams

Scan the actual project and generate/update diagrams based on what exists in code.

**Type:** $ARGUMENTS

Available types:
- `architecture` — System overview: services, connections, data flow → updates `docs/ARCHITECTURE.md`
- `api` — API routes map: all endpoints grouped by resource → updates `docs/ARCHITECTURE.md`
- `database` — Database schema: tables/collections, indexes, relationships → updates `docs/ARCHITECTURE.md`
- `infrastructure` — Deployment topology: servers, containers, regions → updates `docs/INFRASTRUCTURE.md`
- `all` — Generate all diagram types

If `--update` is passed, replace existing diagrams in-place. Otherwise, show the diagram and ask before writing.

## Diagram Format

**ALL diagrams use ASCII box-drawing characters.** No Mermaid, no SVG, no external tools.

```
Box characters: ┌ ┐ └ ┘ │ ─ ├ ┤ ┬ ┴ ┼
Arrows: → ← ↑ ↓ ──> <──
```

---

## Type: `architecture`

### What to scan

Detect project language/framework first, then run the appropriate scans.

**TypeScript/JavaScript:**
```bash
find src/ -name "*.ts" -o -name "*.tsx" -o -name "*.js" 2>/dev/null | head -50
grep -rl "app.listen\|createServer\|express()\|fastify()\|Hono()\|new Elysia" src/ 2>/dev/null
grep -rn "app\.\(get\|post\|put\|delete\|patch\)\|router\.\(get\|post\|put\|delete\|patch\)" src/ 2>/dev/null
```

**Python:**
```bash
find src/ -name "*.py" 2>/dev/null | head -50
grep -rl "Flask\|FastAPI\|app = \|app=\|@app.route\|@router\." src/ 2>/dev/null
grep -rn "@app\.\(get\|post\|put\|delete\|patch\)\|@router\.\|app\.add_url_rule" src/ 2>/dev/null
```

**Go:**
```bash
find . -name "*.go" 2>/dev/null | grep -v "_test.go" | head -50
grep -rn "http.HandleFunc\|r.GET\|r.POST\|http.Handle" . 2>/dev/null
```

If tessera MCP is active, call `graph_continue` with "architecture overview" as the query, then read the `recommended_files` — this surfaces the most structurally significant files without a full scan.

### Generate the diagram

**Adapt to what ACTUALLY exists.** Only diagram what you found in code.

```
┌─────────────────────────────────────────────┐
│                  SYSTEM NAME                 │
│                                             │
│  ┌──────────┐   HTTP    ┌──────────────┐   │
│  │  Client  │──────────>│   Frontend   │   │
│  │          │           │   :PORT      │   │
│  └──────────┘           └──────┬───────┘   │
│                                │            │
│                    API calls   │            │
│                                ▼            │
│                         ┌──────────────┐   │
│                         │   Backend    │   │
│                         │   :PORT      │   │
│                         └──────┬───────┘   │
│                                │            │
│                      read/write│            │
│                                ▼            │
│                         ┌──────────────┐   │
│                         │   Database   │   │
│                         └──────────────┘   │
└─────────────────────────────────────────────┘
```

### Where to write

Replace the `## System Overview` diagram section in `docs/ARCHITECTURE.md`.
Also update `## Service Responsibilities` table and `## Data Flow` section.

---

## Type: `api`

### What to scan

**TypeScript/JavaScript:**
```bash
grep -rn "app\.\(get\|post\|put\|delete\|patch\)\|router\.\(get\|post\|put\|delete\|patch\)" src/ 2>/dev/null
find src/app/api -name "route.ts" -o -name "route.tsx" 2>/dev/null
find src/pages/api -name "*.ts" -o -name "*.tsx" 2>/dev/null
```

**Python (Flask/FastAPI):**
```bash
grep -rn "@app\.route\|@router\.\|@app\.\(get\|post\|put\|delete\|patch\)" src/ 2>/dev/null
```

### Generate the diagram

```
API Routes Map
==============

  /api/
  ├── auth/
  │   ├── POST   /login          → handlers/auth:login
  │   └── POST   /logout         → handlers/auth:logout
  ├── users/
  │   ├── GET    /               → handlers/users:list
  │   ├── GET    /:id            → handlers/users:get
  │   └── DELETE /:id            → handlers/users:delete
  └── health/
      └── GET    /               → server (inline)
```

### Where to write

Add/update an `## API Routes` section in `docs/ARCHITECTURE.md`.

---

## Type: `database`

### What to scan

**SQLite/SQLAlchemy/Prisma/Mongoose — detect from deps then scan:**

```bash
# Python (SQLAlchemy / raw SQLite)
grep -rn "CREATE TABLE\|class.*Base\|__tablename__\|Column(" src/ 2>/dev/null | head -40

# TypeScript (Prisma)
cat prisma/schema.prisma 2>/dev/null

# TypeScript (Mongoose)
grep -rn "new Schema\|model(" src/ 2>/dev/null | head -40

# Tessera-style SQLite migrations
find . -name "migrations.py" -o -name "schema.sql" 2>/dev/null
grep -rn "CREATE TABLE\|CREATE INDEX" src/ 2>/dev/null | head -40
```

### Generate the diagram

```
Database Schema
===============

  ┌─────────────────────────┐      ┌─────────────────────────┐
  │ table_name              │      │ other_table             │
  ├─────────────────────────┤      ├─────────────────────────┤
  │ id          INTEGER  PK │──┐   │ id          INTEGER  PK │
  │ name        TEXT NOT NULL│  │   │ parent_id   INTEGER  FK │──┐
  │ created_at  REAL        │  │   │ value       TEXT        │  │
  └─────────────────────────┘  │   └─────────────────────────┘  │
                               │                                 │
                               └──────── FK reference ──────────┘

  Indexes:
    table_name.name    — unique
    other_table.parent — compound (parent_id, created_at DESC)

  [PK] primary key  [FK] foreign key  [U] unique  [TTL] auto-expiring
```

### Where to write

Add/update a `## Database Schema` section in `docs/ARCHITECTURE.md`.

---

## Type: `infrastructure`

### What to scan

```bash
# Ports and hosts
grep -n "PORT\|HOST\|REGION\|VPS\|VERCEL\|RAILWAY" .env.example .env 2>/dev/null

# Containers
ls Dockerfile docker-compose.yml docker-compose.yaml 2>/dev/null

# Deployment config
grep -n "DOKPLOY\|HOSTINGER\|VERCEL\|VPS\|RAILWAY\|FLY" .env.example .env 2>/dev/null
```

### Generate the diagram

**Single region:**
```
Infrastructure
==============

  ┌──────────────── Production ────────────────┐
  │                                             │
  │   ┌─────────────┐     ┌─────────────┐     │
  │   │   Service   │────>│  Database   │     │
  │   │   :PORT     │     │             │     │
  │   └─────────────┘     └─────────────┘     │
  │                                             │
  │   Host: (from .env)                         │
  │                                             │
  └─────────────────────────────────────────────┘
```

### Where to write

Replace the `## Environment Overview` diagram in `docs/INFRASTRUCTURE.md`.

---

## Type: `all`

Run all four types in sequence: architecture → api → database → infrastructure.

---

## After Generating

1. Show the generated diagram(s) to the user
2. If `--update` was passed: write directly to the docs
3. If not: ask "Write this to docs/ARCHITECTURE.md?" before writing
4. Report what was generated and what files were updated
