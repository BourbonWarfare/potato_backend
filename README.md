# potato_db

The HTTP backend powering the [Bourbon Warfare](https://bourbonwarfare.com) ARMA group.

It started life as the backend for the BW Mission Database and grew into a general-purpose group server: user/role/group management, mission upload and metadata, ARMA dedicated-server orchestration, a cron runner for scheduled work, and a small realtime event bus that talks back to the Discord bot.

It is the backend half of a pair. The frontend is the Discord bot [potato_bot](https://github.com/bourbonwarfare/potato_bot), which consumes this API over HTTP.

## What it does

- **Auth / users / groups / roles.** Discord OAuth2 login, session tokens, per-role permissions, group membership. Bot-style logins for trusted clients (the Discord bot, the cron runner).
- **Missions.** Upload and version ARMA `.pbo` missions, store metadata, track iterations.
- **ARMA server ops.** Start, stop, restart, update, and mod-update dedicated ARMA servers via `steamcmd` and a PowerShell helper.
- **Cron runner.** Loads `cron_*.py` files from a configurable directory and runs them on a schedule. Reloads on change.
- **Realtime bus.** Internal event queue that lets crons and endpoints push messages to the Discord bot via `/api/v1/realtime`.

Architecture diagrams live in [`arch/`](./arch).

## Technology

- **Python 3.12**, dependencies pinned with [uv](https://docs.astral.sh/uv/).
- **[Quart](https://quart.palletsprojects.com/)** ASGI web framework, served by **[Uvicorn](https://www.uvicorn.org/)** in production.
- **[SQLAlchemy](https://www.sqlalchemy.org/)** + **[pg8000](https://github.com/tlocke/pg8000)** against **PostgreSQL**, with **[Alembic](https://alembic.sqlalchemy.org/)** migrations.
- **[aiohttp](https://docs.aiohttp.org/)** + **aiodns** for outbound HTTP (Discord OAuth, the cron runner's self-calls).
- **[cron-converter](https://pypi.org/project/cron-converter/)** for parsing cron strings.
- **[python-dotenv](https://pypi.org/project/python-dotenv/)** plus a small key-value config loader (`conf.kv`).
- **[pytest](https://pytest.org/)** (+ `pytest-asyncio`, `pytest-mock`, `pytest-cov`) for tests, **[ruff](https://docs.astral.sh/ruff/)** for lint and format, **[ty](https://github.com/astral-sh/ty)** for type checking.

## Surfaces

- REST API mounted under `/api/v1/{auth,user,group,admin,missions,server_ops,realtime}`.
- Loopback-only API under `/api/local/*` for trusted same-host callers.
- HTML routes under `/` for the OAuth callback flow.

## Building and running

See [BUILDING.md](./BUILDING.md) for local setup, tests, migrations, cron, and the production runbook.

## License

See [LICENSE](./LICENSE).
