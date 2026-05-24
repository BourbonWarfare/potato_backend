# Building potato_db

This guide covers local development, tests, database migrations, the cron runner, and the production runbook.

## Prerequisites

- **Python 3.12** (the project pins `==3.12.*` in `pyproject.toml`).
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** for dependency and virtualenv management.
- **PostgreSQL 16** (or compatible) reachable from the machine you run on. Other SQLAlchemy-supported databases may work but are not exercised in CI.
- For ARMA server ops (optional in dev):
  - `steamcmd` on the host (path configured via `steam_cmd_path`).
  - `hemtt` and `a3sb` binaries under `bin/` (used to build PBOs and probe servers).
  - The `_server_manage.ps1` helper under `bin/` (Windows-only; the path is configurable).

## Install

```sh
git clone https://github.com/bourbonwarfare/potato_db.git
cd potato_db
uv sync --locked --all-extras --dev
```

Available extras:

- `tests` — `pytest` and friends.
- `development` — `pre-commit`.
- `prod` — `uvicorn` (only needed on the production host).

To install only what you need:

```sh
uv sync --locked --extra tests --dev      # tests + dev tools
uv sync --locked --extra prod             # production host
```

Install the pre-commit hooks once:

```sh
uv run pre-commit install
```

## Configure

Configuration lives in `conf.kv` at the repo root. The file is plain `key=value` lines, with `#` for comments and blank lines ignored. A working example for local development:

```
environment=local

db_driver=postgresql+pg8000
db_username=bw
db_password=...
db_address=localhost
db_name=bw_backend

default_session_length=3600
api_session_length=300

single_log_size=52428800
log_backup_count=3
mission_metadata_csv_size=5368709120

steam_cmd_path=/path/to/steamcmd
server_manage_ps1_path=./bin/_server_manage.ps1

arma_mod_configs=./server_configs/mods
arma_modlist_configs=./server_configs/modlists

discord_api_url=https://discord.com/api/v10
discord_client_id=...
discord_client_secret=...

cron_token=...
cron_path=./crons
timezone=America/Edmonton
```

The `tests/test_config.kv` file is a sane reference for the required key set.

### Required keys, by feature

- **Database** (always required): `db_driver`, `db_username`, `db_password`, `db_address`, `db_name`.
- **Discord OAuth**: `discord_api_url`, `discord_client_id`, `discord_client_secret`.
- **ARMA server ops**: `steam_cmd_path`, `server_manage_ps1_path`, `arma_mod_configs`, `arma_modlist_configs`.
- **Cron runner**: `cron_token`, `cron_path`, `timezone`.
- **Production with SSL**: `ssl_ca_certs_path`, `ssl_certfile_path`, `ssl_keyfile_path`.

Environment variables are also folded into the config map (env wins over `conf.kv`), and `.env` / `.env.secret` / `.env.shared` files are loaded if present. Secrets belong in `.env.secret` or the host's environment, **not** in `conf.kv`.

If you prefer the config writer to bootstrap the file for you:

```sh
uv run python init_server.py
```

## Database migrations

Alembic lives in `alembic/`. Create the database first (e.g. `createdb bw_backend`), then bring it up to head:

```sh
uv run alembic upgrade head
```

Other common commands:

```sh
uv run alembic revision --autogenerate -m "describe the change"
uv run alembic current
uv run alembic history
```

Downgrades and `alembic stamp` are destructive and not part of the day-to-day flow; confirm before running them on anything you care about.

## Run locally

```sh
uv run python main.py
```

`main.py` reads `environment` from the config:

- `local` (or unset) → Quart's built-in server on `http://localhost:8080`, no SSL.
- `test` → same as local on `:8080`, used by integration tests.
- `staging` → Uvicorn on `:8500`, no SSL.
- `prod` → Uvicorn on `:12239`, SSL required (see below).

In **all** environments `main.py` also spawns the cron runner as a subprocess, so you do not need a separate cron process in normal use. The bundled runner reads `cron_path` and `cron_token` from the config.

## Tests

```sh
uv run pytest                  # all tests
uv run pytest --cov=bw         # with coverage
uv run pytest tests/foo.py     # a single file
```

The test suite expects a Postgres instance reachable using the credentials in `tests/test_config.kv`. CI uses a Postgres 16 service container with `tester:tester` against database `testing_db`; mirror that locally if you want the same setup. Copy `tests/test_config.kv` to `conf.kv` (or set `ENVIRONMENT=test` and let pytest do it) before running.

## Lint, format, type-check

```sh
uv run ruff check              # lint
uv run ruff format             # format
uv run ty check                # type check
```

The pre-commit hook runs `ruff check` and `ruff format` on staged files.

## Cron jobs

The cron runner walks `cron_path` (recursively), imports every `cron_*.py` file it finds, and schedules the first class in each file that inherits from `crons.cron.Cron`. Files are reloaded when their mtime changes, so you can edit a cron and the runner will pick it up within a tick (about a minute) without a restart.

A minimal cron:

```python
# crons/cron_my_task.py
from crons.cron import Cron

class MyTask(Cron):
    @staticmethod
    def cron_str() -> str:
        return '*/5 * * * *'  # every 5 minutes

    def run(self) -> None:
        # synchronous setup
        ...

    async def async_run(self) -> None:
        # async work, no auth
        ...

    async def request(self, session) -> None:
        # async work with an aiohttp session pre-authed against the backend
        ...
```

See `crons/README.md` and `crons/cron_example.py` for the full pattern. The runner authenticates to the backend over `http://localhost:{port}/api/v1/auth/login/bot` using `cron_token`, so the cron and the backend always need to share that token.

### Running the cron runner standalone

`main.py` already spawns the runner as a subprocess. If you want to run it on its own (separate systemd unit, separate process group, separate restart cadence), use:

```sh
uv run python cron_main.py
```

The standalone runner needs the backend to be reachable on `localhost:{port}`; it will retry the login for up to 10 attempts before giving up.

## Production runbook

Production deployment is two long-running processes plus Postgres.

1. **Provision the host.**
   - Install Python 3.12 and uv.
   - Install Postgres 16 and create the production database and role.
   - Install `steamcmd`, the ARMA dedicated server binaries, `hemtt`, and `a3sb` where the config expects them.
   - Obtain TLS certificate, key, and CA bundle for the backend's public hostname.

2. **Deploy the code.**
   ```sh
   git clone https://github.com/bourbonwarfare/potato_db.git /opt/potato_db
   cd /opt/potato_db
   uv sync --locked --extra prod
   ```

3. **Write `conf.kv`** with `environment=prod` and the SSL keys filled in:
   ```
   environment=prod
   ssl_ca_certs_path=/etc/ssl/bw/chain.pem
   ssl_certfile_path=/etc/ssl/bw/fullchain.pem
   ssl_keyfile_path=/etc/ssl/bw/privkey.pem
   # ...plus all the other required keys above
   ```
   Keep secrets in `.env.secret` or systemd `EnvironmentFile=`, not in `conf.kv`.

4. **Apply migrations.**
   ```sh
   uv run alembic upgrade head
   ```

5. **Run the server.**

   `main.py` detects `environment=prod` and starts:
   - **Uvicorn** binding `0.0.0.0:12239` with the configured TLS material, serving `bw.server:app`.
   - A **cron subprocess** authenticated with `cron_token`.

   ```sh
   uv run python main.py
   ```

   In practice you want this under a process supervisor. A minimal systemd unit:

   ```ini
   # /etc/systemd/system/potato-db.service
   [Unit]
   Description=potato_db backend
   After=network-online.target postgresql.service
   Wants=network-online.target

   [Service]
   Type=simple
   User=potato
   WorkingDirectory=/opt/potato_db
   EnvironmentFile=/etc/potato_db/secrets.env
   ExecStart=/usr/local/bin/uv run python main.py
   Restart=on-failure
   RestartSec=5s

   [Install]
   WantedBy=multi-user.target
   ```

   The cron runner is bundled into `main.py`, so a single unit is enough. If you would rather isolate it (so a crashing cron does not take the API down, and vice versa), unset `cron_token` in the API process, run a second unit that calls `uv run python cron_main.py`, and let the standalone runner pick up the token from its own `EnvironmentFile`.

6. **Reverse proxy and firewall.**
   - Uvicorn binds `0.0.0.0:12239` with TLS already terminated. If you front it with nginx or Caddy, terminate TLS there instead and have Uvicorn listen on `127.0.0.1` (clear `ssl_*` and adjust the port).
   - Only the API port needs to be reachable from the public internet. The cron runner is loopback-only.

7. **Upgrades.**
   ```sh
   git pull
   uv sync --locked --extra prod
   uv run alembic upgrade head
   systemctl restart potato-db
   ```

## CI

`.github/workflows/test_runner.yml` runs `pytest` against a Postgres 16 service container with `uv sync --locked --extra tests --dev`.

`.github/workflows/code_quality.yml` runs the ruff hooks. Match what CI does locally with:

```sh
uv run pre-commit run --all-files
uv run pytest
```
