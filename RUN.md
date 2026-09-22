# AIMPF — easiest local run

## Prerequisites

Install:

- Docker Desktop (Windows/macOS) or Docker Engine + Compose (Linux)
- Python 3.11+
- Node.js 18+

## One command

From the `project/` directory:

```bash
python run.py
```

On Windows, the same command works in PowerShell or Command Prompt:

```powershell
py run.py
```

The launcher will:

1. start PostgreSQL + pgvector with Docker Compose
2. create `.venv` when needed
3. install backend dependencies
4. install frontend dependencies
5. create safe local `.env` files when missing
6. apply Alembic migrations
7. seed reproducible demo data
8. start FastAPI on `http://127.0.0.1:8000`
9. start Next.js on `http://127.0.0.1:3000`

Press `Ctrl+C` to stop the application processes. The PostgreSQL volume is intentionally kept; no destructive database reset is performed.

## Optional modes

Skip dependency installation when already installed:

```bash
python run.py --no-install
```

Run the deterministic research benchmark before startup:

```bash
python run.py --research
```

Skip demo-data seeding:

```bash
python run.py --no-seed
```

## Troubleshooting

If Docker is not running, start Docker Desktop/Engine and run the command again.

If ports `5432`, `8000`, or `3000` are already in use, stop the conflicting process before starting AIMPF.

Runtime logs are written to `aimpf-api.log` and `aimpf-web.log`. These are local runtime files and are intentionally ignored by Git/submission cleanup.
