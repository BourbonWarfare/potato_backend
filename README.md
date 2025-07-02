# potato_backend
## The backend server Bourbon Warfare uses to manage stuff

### What is this?

This is a server for the ARMA group Bourbon Warfare. It was originally created to
be a backend for the BW Mission Database, but it is used for any of the groups needs.

## Development
### Setup
Use your favourite Python package manager to install the requirements as laid out in
`pyproject.toml`. `development` and `tests` are available as extras if you want to
use additional features

#### Example
**Install project and all extras**
`uv sync --locked --all-extras --dev`

**Install project, but only test extras**
`uv sync --locked --extra tests --dev`

## Running
### Local
A helper `main.py` function is available in the root directory to run the server locally.
Connect to `localhost:8080` to see the server

### Production
The project uses `Quart` to manage the server. This framework requires a valid `ASGI`
server to run. See [Quart documentation](https://quart.palletsprojects.com/en/latest/tutorials/deployment/)
for more information.

## Configuration
All server-specific configuration is contained in `conf.txt`. Some attributes are required,
and if not present the project will exist with a `ConfigError` exception.

Values are stored as `key=value`, and you can add comments with `# comment` syntax.

## Database
Some server features requires a database to run. The server is developed assuming Postgres
is used, but other databases may work.

### Configuration
In `conf.txt`, the following keys are required for database connections:
- `db_driver`: driver which is powering the database, see
[SQL Alchemy documentation](https://docs.sqlalchemy.org/en/20/core/engines.html) for more information
- `db_username`: username which will be connected for all database operations
- `db_password`: password for `db_username`
- `db_address`: address which will be connected to
- `db_name`: the specific database which operations will be performed on