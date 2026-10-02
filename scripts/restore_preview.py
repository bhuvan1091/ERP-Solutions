"""Recover existing local preview services after a sandbox reset.

Explicit developer/testing utility, not an application startup or production script.
Creates only a missing configured PostgreSQL role/database; never resets existing data.
Application startup remains responsible for its existing empty-database demo seed.
"""
import subprocess
from pathlib import Path

from dotenv import dotenv_values
from psycopg2.extensions import adapt
from sqlalchemy.engine import make_url


def run(*args, **kwargs):
    return subprocess.run(args, text=True, capture_output=True, check=True, **kwargs)


def psql(query):
    return run("sudo", "-u", "postgres", "psql", "-v", "ON_ERROR_STOP=1", "-tA", input=query).stdout.strip()


def identifier(value):
    return '"' + value.replace('"', '""') + '"'


def literal(value):
    return adapt(value).getquoted().decode()


if __name__ == "__main__":
    config = dotenv_values(Path(__file__).resolve().parents[1] / "backend" / ".env")
    url = make_url(config["DATABASE_URL"])
    if url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise SystemExit("Refusing to modify a non-local database.")
    # The existing local cluster may be running already; pg_ctlcluster returns 2 then.
    pg = subprocess.run(["sudo", "pg_ctlcluster", "15", "main", "start"], capture_output=True, text=True)
    if pg.returncode not in (0, 2):
        raise SystemExit(pg.stderr)
    if not psql("SELECT 1 FROM pg_roles WHERE rolname=" + literal(url.username) + ";"):
        psql("CREATE ROLE " + identifier(url.username) + " LOGIN PASSWORD " + literal(url.password) + ";")
        print("Restored missing local database role from existing configuration.")
    if not psql("SELECT 1 FROM pg_database WHERE datname=" + literal(url.database) + ";"):
        psql("CREATE DATABASE " + identifier(url.database) + " OWNER " + identifier(url.username) + ";")
        print("Created missing preview database. Only seeded demo data will be available.")
    status = subprocess.run(["sudo", "supervisorctl", "status"], capture_output=True, text=True)
    if "no such file" in status.stdout + status.stderr or "refused" in status.stdout + status.stderr:
        run("sudo", "supervisord", "-c", "/etc/supervisor/supervisord.conf")
        print("Started existing supervisor configuration.")
    else:
        run("sudo", "supervisorctl", "restart", "backend")
        print("Restarted backend after database recovery.")