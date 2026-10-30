"""Safely initialize the four local development databases and demo fixtures."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

import pymysql
from dotenv import load_dotenv
from pymysql.constants import CLIENT
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
ENV_FILE = BACKEND / ".env"
SEED_FILE = BACKEND / "database" / "seed.sql"
COURT_MIGRATION = BACKEND / "migrations" / "20261026_add_time_slot_reservations.sql"
TARGETS = {
    "USER_DATABASE_URL": "sports_user_db",
    "COURT_DATABASE_URL": "sports_court_db",
    "BOOKING_DATABASE_URL": "sports_booking_db",
    "PAYMENT_DATABASE_URL": "sports_payment_db",
}
PROTECTED_DATABASES = {
    "sports_user_e2e_test",
    "sports_court_e2e_test",
    "sports_booking_e2e_test",
    "sports_payment_e2e_test",
    "sports_court_booking_s2_test",
}
RESERVATION_COLUMNS = {
    "reservation_status",
    "reservation_booking_id",
    "reservation_expires_at",
}


def stop(message: str) -> NoReturn:
    raise RuntimeError(message)


def load_configuration() -> tuple[dict[str, URL], URL]:
    if not ENV_FILE.is_file():
        stop("backend/.env is missing. Copy backend/.env.example and configure local MySQL first.")
    load_dotenv(ENV_FILE)  # Process environment has standard python-dotenv precedence.
    app_env = os.getenv("APP_ENV") or "development"
    if app_env.strip().lower() != "development":
        stop("APP_ENV must be development for this setup command.")
    if len(os.getenv("JWT_SECRET_KEY", "").strip()) < 32:
        stop("JWT_SECRET_KEY must be configured with at least 32 characters before setup.")
    if len(os.getenv("INTERNAL_SERVICE_TOKEN", "").strip()) < 32:
        stop("INTERNAL_SERVICE_TOKEN must be configured with at least 32 characters before setup.")

    urls: dict[str, URL] = {}
    for key, expected_database in TARGETS.items():
        raw = os.getenv(key, "").strip()
        if not raw:
            stop(f"{key} is missing from backend/.env or the process environment.")
        try:
            url = make_url(raw)
        except Exception:
            stop(f"{key} is not a valid SQLAlchemy database URL.")
        if url.drivername != "mysql+pymysql":
            stop(f"{key} must use the configured MySQL/PyMySQL driver.")
        if url.database != expected_database or url.database in PROTECTED_DATABASES:
            stop(f"{key} must target only {expected_database}; no database was changed.")
        if not url.host or not url.username or url.password is None:
            stop(f"{key} must include a local MySQL host, user, and password.")
        urls[key] = url

    coordinates = {(url.host, url.port or 3306, url.username) for url in urls.values()}
    if len(coordinates) != 1:
        stop("All four development URLs must use the same MySQL host, port, and account.")
    host = next(iter(coordinates))[0]
    if host is None:
        stop("All four development URLs must include a local MySQL host.")
    host = host.lower()
    if host not in {"localhost", "127.0.0.1", "::1"}:
        stop("The setup command only allows a local MySQL server.")

    server_url = next(iter(urls.values())).set(database="mysql")
    return urls, server_url


def inspect_targets(server_url: URL) -> dict[str, list[str]]:
    engine = create_engine(server_url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as connection:
            host, port, account = connection.execute(
                text("SELECT @@hostname, @@port, CURRENT_USER()")
            ).one()
            print(f"MySQL server: {host}:{port}; authenticated account: {account}")
            found: dict[str, list[str]] = {}
            for database in TARGETS.values():
                exists = connection.execute(
                    text("SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME=:name"),
                    {"name": database},
                ).scalar_one()
                tables = connection.execute(
                    text("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=:name ORDER BY TABLE_NAME"),
                    {"name": database},
                ).scalars().all()
                found[database] = list(tables)
                print(f"{database}: {'exists' if exists else 'will be created'}; tables={len(tables)}")
            return found
    finally:
        engine.dispose()


def preflight_existing_schema(server_url: URL, schemas: dict[str, list[str]]) -> None:
    engine = create_engine(server_url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as connection:
            user_tables = schemas["sports_user_db"]
            if "users" in user_tables:
                if "alembic_version" not in user_tables:
                    stop("sports_user_db has users but no Alembic version table; inspect it before setup.")
                versions = connection.execute(
                    text("SELECT version_num FROM sports_user_db.alembic_version")
                ).scalars().all()
                if versions and versions != ["0001_create_users"]:
                    stop("sports_user_db has an unexpected Alembic revision; no setup writes were made.")
            elif "alembic_version" in user_tables:
                stop("sports_user_db has migration metadata but no users table; inspect it before setup.")

            court_tables = schemas["sports_court_db"]
            if "time_slots" in court_tables:
                actual = set(
                    connection.execute(
                        text("SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='sports_court_db' AND TABLE_NAME='time_slots'")
                    ).scalars().all()
                )
                present = actual & RESERVATION_COLUMNS
                if present and present != RESERVATION_COLUMNS:
                    stop("Court time_slots has a partial reservation schema; inspect it before setup.")
    finally:
        engine.dispose()


def create_databases(server_url: URL) -> None:
    engine = create_engine(server_url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as connection:
            for database in TARGETS.values():
                # The names are fixed constants, not user-supplied SQL.
                connection.exec_driver_sql(
                    f"CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4"
                )
        print("Development database schemas are present.")
    finally:
        engine.dispose()


def run(command: list[str], cwd: Path, label: str) -> None:
    print(f"Initializing {label} schema...")
    result = subprocess.run(command, cwd=cwd, env=os.environ.copy(), check=False)
    if result.returncode:
        stop(f"{label} initialization failed with exit code {result.returncode}; inspect the output above.")


def initialize_service_schemas() -> None:
    user_dir = BACKEND / "services" / "user_service"
    court_dir = BACKEND / "services" / "court_service"
    booking_dir = BACKEND / "services" / "booking_service"
    payment_dir = BACKEND / "services" / "payment_service"
    run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
        user_dir,
        "User Service",
    )
    run([sys.executable, "-m", "app.init_db"], court_dir, "Court Service")
    apply_court_migration_if_needed()
    run([sys.executable, "-m", "app.init_db"], booking_dir, "Booking Service")
    run([sys.executable, "-m", "app.init_db"], payment_dir, "Payment Service")


def apply_court_migration_if_needed() -> None:
    court_url = make_url(os.environ["COURT_DATABASE_URL"])
    engine = create_engine(court_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            columns = set(
                connection.execute(
                    text("SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='sports_court_db' AND TABLE_NAME='time_slots'")
                ).scalars().all()
            )
            if not columns:
                stop("Court initialization did not create time_slots; migration was not attempted.")
            missing = RESERVATION_COLUMNS - columns
            if not missing:
                print("Court reservation migration: not needed (current model schema is present).")
                return
            if missing != RESERVATION_COLUMNS:
                stop("Court reservation columns are partially present; migration was not attempted.")
            # This is the repository's one-time migration for an older existing Court schema.
            migration = COURT_MIGRATION.read_text(encoding="utf-8")
            statement = " ".join(
                line for line in migration.splitlines() if line.strip() and not line.lstrip().startswith("--")
            ).strip()
            with engine.begin() as write_connection:
                write_connection.exec_driver_sql(statement)
            print("Court reservation migration applied to the existing Court schema.")
    finally:
        engine.dispose()


def run_seed(url: URL) -> None:
    params = {
        "host": url.host,
        "port": url.port or 3306,
        "user": url.username,
        "password": url.password or "",
        "database": "mysql",
        "charset": "utf8mb4",
        "autocommit": True,
        "client_flag": CLIENT.MULTI_STATEMENTS,
    }
    connection = pymysql.connect(**params)
    try:
        with connection.cursor() as cursor:
            cursor.execute(SEED_FILE.read_text(encoding="utf-8"))
            while cursor.nextset():
                pass  # Consume preflight and verification result sets without printing account data.
        print("Demo seed SQL completed.")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def verify_results(server_url: URL) -> None:
    engine = create_engine(server_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            expected_tables = {
                "sports_user_db": {"users", "alembic_version"},
                "sports_court_db": {"sports", "venues", "courts", "time_slots"},
                "sports_booking_db": {"bookings"},
                "sports_payment_db": {"payments"},
            }
            for database, expected in expected_tables.items():
                actual = set(
                    connection.execute(
                        text("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=:schema"),
                        {"schema": database},
                    ).scalars().all()
                )
                if not expected <= actual:
                    stop(f"Schema verification failed for {database}; expected tables are missing.")
                print(f"{database}: required tables PASS")

            demo_accounts = connection.execute(
                text("SELECT email, role, is_active FROM sports_user_db.users WHERE email IN (:a,:o1,:o2,:u1,:u2,:u3)"),
                {
                    "a": "admin.demo@example.com",
                    "o1": "owner1.demo@example.com",
                    "o2": "owner2.demo@example.com",
                    "u1": "customer1.demo@example.com",
                    "u2": "customer2.demo@example.com",
                    "u3": "customer3.demo@example.com",
                },
            ).all()
            account_roles = {email: (role, bool(active)) for email, role, active in demo_accounts}
            expected_accounts = {
                "admin.demo@example.com": "ADMIN",
                "owner1.demo@example.com": "OWNER",
                "owner2.demo@example.com": "OWNER",
                "customer1.demo@example.com": "USER",
                "customer2.demo@example.com": "USER",
                "customer3.demo@example.com": "USER",
            }
            accounts_valid = len(account_roles) == 6 and all(
                account_roles.get(email) == (role, True)
                for email, role in expected_accounts.items()
            )
            sports = connection.execute(
                text("SELECT COUNT(*) FROM sports_court_db.sports WHERE name IN ('Badminton','Football','Tennis') AND is_active=1")
            ).scalar_one()
            venues = connection.execute(
                text("SELECT COUNT(*) FROM sports_court_db.venues WHERE name IN ('Demo Badminton Center A','Demo Football Center B','Demo Tennis Center C','Demo Sports Center D') AND is_active=1")
            ).scalar_one()
            owned_venues = connection.execute(
                text("SELECT COUNT(*) FROM sports_court_db.venues v JOIN sports_user_db.users u ON u.id=v.owner_id WHERE ((v.name IN ('Demo Badminton Center A','Demo Football Center B') AND u.email='owner1.demo@example.com') OR (v.name IN ('Demo Tennis Center C','Demo Sports Center D') AND u.email='owner2.demo@example.com')) AND v.is_active=1")
            ).scalar_one()
            courts = connection.execute(
                text("SELECT COUNT(*) FROM sports_court_db.courts WHERE name IN ('Badminton Court A1','Badminton Court A2','Football Court B1','Football Court B2','Tennis Court C1','Tennis Court C2','Badminton Court D1','Tennis Court D2') AND is_active=1")
            ).scalar_one()
            linked_courts = connection.execute(
                text("SELECT COUNT(*) FROM sports_court_db.courts c JOIN sports_court_db.venues v ON v.id=c.venue_id JOIN sports_court_db.sports s ON s.id=c.sport_id WHERE ((c.name IN ('Badminton Court A1','Badminton Court A2') AND v.name='Demo Badminton Center A' AND s.name='Badminton') OR (c.name IN ('Football Court B1','Football Court B2') AND v.name='Demo Football Center B' AND s.name='Football') OR (c.name IN ('Tennis Court C1','Tennis Court C2') AND v.name='Demo Tennis Center C' AND s.name='Tennis') OR (c.name='Badminton Court D1' AND v.name='Demo Sports Center D' AND s.name='Badminton') OR (c.name='Tennis Court D2' AND v.name='Demo Sports Center D' AND s.name='Tennis')) AND c.is_active=1")
            ).scalar_one()
            slots = connection.execute(
                text("SELECT COUNT(*) FROM sports_court_db.time_slots ts JOIN sports_court_db.courts c ON c.id=ts.court_id WHERE c.name IN ('Badminton Court A1','Badminton Court A2','Football Court B1','Football Court B2','Tennis Court C1','Tennis Court C2','Badminton Court D1','Tennis Court D2') AND ts.slot_date >= CURRENT_DATE AND ts.is_active=1 AND ts.start_time='09:00:00' AND ts.end_time='10:00:00'")
            ).scalar_one()
            actual = (sports, venues, owned_venues, courts, linked_courts, slots)
            if not accounts_valid or actual != (3, 4, 4, 8, 8, 24):
                stop("Demo data verification mismatch (account roles/status or Sports/Venues/Courts/future slots).")
            print("Demo fixtures: 6 accounts, 3 sports, 4 venues, 8 courts, 24 active future slots PASS")
    finally:
        engine.dispose()


def main() -> int:
    try:
        urls, server_url = load_configuration()
        print("Development setup target: sports_user_db, sports_court_db, sports_booking_db, sports_payment_db")
        schemas = inspect_targets(server_url)
        preflight_existing_schema(server_url, schemas)
        answer = input("Type SETUP to initialize these local development databases and add missing demo rows: ")
        if answer.strip() != "SETUP":
            print("Cancelled; no database writes were made.")
            return 1
        create_databases(server_url)
        initialize_service_schemas()
        run_seed(urls["USER_DATABASE_URL"])
        verify_results(server_url)
        print("Local development database setup completed.")
        return 0
    except Exception as exc:
        # Do not expose connection URLs or credentials in errors.
        message = str(exc).replace(os.getenv("USER_DATABASE_URL", "<none>"), "<redacted>")
        print(f"SETUP STOPPED: {message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
