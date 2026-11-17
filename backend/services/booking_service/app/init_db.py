from sqlalchemy import text
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.database import Base, engine
from app import models  # noqa: F401

_OBJECT_INVENTORY_SQL = text("""
    SELECT 'TABLE' AS object_type, TABLE_NAME AS object_name
      FROM information_schema.TABLES
     WHERE TABLE_SCHEMA = :schema_name AND TABLE_TYPE = 'BASE TABLE'
    UNION ALL
    SELECT 'VIEW', TABLE_NAME FROM information_schema.VIEWS
     WHERE TABLE_SCHEMA = :schema_name
    UNION ALL
    SELECT 'TRIGGER', TRIGGER_NAME FROM information_schema.TRIGGERS
     WHERE TRIGGER_SCHEMA = :schema_name
    UNION ALL
    SELECT ROUTINE_TYPE, ROUTINE_NAME FROM information_schema.ROUTINES
     WHERE ROUTINE_SCHEMA = :schema_name
    UNION ALL
    SELECT 'EVENT', EVENT_NAME FROM information_schema.EVENTS
     WHERE EVENT_SCHEMA = :schema_name
""")
_OBJECT_TYPES = {"TABLE", "VIEW", "TRIGGER", "PROCEDURE", "FUNCTION", "EVENT"}
_REQUIRED_METADATA_PRIVILEGES = {"SELECT", "SHOW VIEW", "TRIGGER", "EVENT", "SHOW_ROUTINE"}


def _can_inspect_schema_objects(grants, schema_name: str) -> bool:
    visible_privileges = set()
    schema_scope = f"{schema_name.lower()}.*"
    for grant in grants:
        normalized = str(grant).lower().replace("`", "")
        if not normalized.startswith("grant ") or " on " not in normalized:
            continue
        privilege_text, scope_and_recipient = normalized[6:].split(" on ", 1)
        scope = scope_and_recipient.split(" to ", 1)[0].strip()
        if scope not in {"*.*", schema_scope}:
            continue
        privileges = {item.strip().upper() for item in privilege_text.split(",")}
        if "ALL PRIVILEGES" in privileges:
            return True
        visible_privileges.update(privileges)
    return _REQUIRED_METADATA_PRIVILEGES.issubset(visible_privileges)


def main() -> None:
    if engine is None:
        raise RuntimeError("BOOKING_DATABASE_URL must be configured")
    if not _validate_existing_schema():
        Base.metadata.create_all(engine)
    print("Booking Service tables are ready.")


def _validate_existing_schema() -> bool:
    try:
        with engine.connect() as connection:
            schema_name = connection.execute(text("SELECT DATABASE()")).scalar_one()
            if not isinstance(schema_name, str) or not schema_name:
                raise ValueError("The database connection has no selected schema.")
            grants = connection.execute(text("SHOW GRANTS")).scalars().all()
            if not _can_inspect_schema_objects(grants, schema_name):
                raise PermissionError("Full schema-object inspection privileges could not be confirmed.")
            rows = connection.execute(_OBJECT_INVENTORY_SQL, {"schema_name": schema_name}).mappings().all()
    except Exception:
        raise RuntimeError("Could not safely inspect all Booking schema objects in MySQL. Check database access and metadata visibility; no tables were changed.") from None

    objects = {object_type: set() for object_type in _OBJECT_TYPES}
    try:
        for row in rows:
            object_type, object_name = row["object_type"], row["object_name"]
            if object_type not in _OBJECT_TYPES or not isinstance(object_name, str) or not object_name:
                raise ValueError("Unexpected MySQL metadata response.")
            objects[object_type].add(object_name)
    except (KeyError, TypeError, ValueError):
        raise RuntimeError("MySQL returned incomplete Booking schema inventory. No tables were changed.") from None

    if not any(objects.values()):
        return False
    unexpected = {kind: names for kind, names in objects.items() if kind != "TABLE" and names}
    if unexpected:
        summary = ", ".join(f"{kind.lower()}s ({len(names)})" for kind, names in sorted(unexpected.items()))
        raise RuntimeError(f"Existing Booking schema contains objects outside the modeled tables: {summary}. No tables were changed; review it manually.")
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection, opts={"compare_type": True, "compare_server_default": True})
            differences = compare_metadata(context, Base.metadata)
    except Exception:
        raise RuntimeError("Could not compare the existing Booking schema with current models. No tables were changed; check database privileges and retry.") from None
    if differences:
        raise RuntimeError("Existing Booking schema differs from the current models. No tables were changed; review and migrate it manually.")
    return True


if __name__ == "__main__":
    main()
