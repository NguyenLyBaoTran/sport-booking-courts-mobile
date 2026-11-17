from unittest.mock import Mock

import pytest

from app import init_db


class Result:
    def __init__(self, rows=(), value=None):
        self.rows = rows
        self.value = value

    def scalar_one(self):
        return self.value

    def scalars(self):
        return self

    def mappings(self):
        return self

    def all(self):
        return list(self.rows)


class Connection:
    def __init__(self, inventory, grants=None, inventory_error=None):
        self.inventory = inventory
        self.grants = grants if grants is not None else ["GRANT ALL PRIVILEGES ON *.* TO `root`@`%`"]
        self.inventory_error = inventory_error

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, statement, *_args):
        sql = str(statement).upper()
        if "SELECT DATABASE" in sql:
            return Result(value="court_test")
        if "SHOW GRANTS" in sql:
            return Result(rows=self.grants)
        if self.inventory_error:
            raise self.inventory_error
        return Result(rows=self.inventory)


class Engine:
    def __init__(self, connection):
        self.connection = connection

    def connect(self):
        return self.connection


def configure(monkeypatch, inventory=(), grants=None, inventory_error=None):
    engine = Engine(Connection(inventory, grants, inventory_error))
    monkeypatch.setattr(init_db, "engine", engine)
    create = Mock()
    monkeypatch.setattr(init_db.Base.metadata, "create_all", create)
    return engine, create


def test_empty_schema_creates_tables(monkeypatch):
    engine, create = configure(monkeypatch)
    init_db.main()
    create.assert_called_once_with(engine)


def test_matching_schema_is_left_untouched(monkeypatch):
    engine, create = configure(monkeypatch, [{"object_type": "TABLE", "object_name": "sports"}])
    monkeypatch.setattr(init_db.MigrationContext, "configure", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(init_db, "compare_metadata", lambda *_args: [])
    init_db.main()
    create.assert_not_called()


def test_schema_differences_stop_before_ddl(monkeypatch):
    _engine, create = configure(monkeypatch, [{"object_type": "TABLE", "object_name": "sports"}])
    monkeypatch.setattr(init_db.MigrationContext, "configure", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(init_db, "compare_metadata", lambda *_args: [("modify_type",)])
    with pytest.raises(RuntimeError, match="differs from the current models"):
        init_db.main()
    create.assert_not_called()


@pytest.mark.parametrize("object_type", ["VIEW", "TRIGGER", "PROCEDURE", "FUNCTION", "EVENT"])
def test_non_table_objects_are_rejected(monkeypatch, object_type):
    _engine, create = configure(monkeypatch, [{"object_type": object_type, "object_name": "unexpected"}])
    with pytest.raises(RuntimeError, match="outside the modeled tables"):
        init_db.main()
    create.assert_not_called()


def test_inventory_error_stops_without_ddl(monkeypatch):
    _engine, create = configure(monkeypatch, inventory_error=PermissionError("denied"))
    with pytest.raises(RuntimeError, match="Could not safely inspect"):
        init_db.main()
    create.assert_not_called()


def test_insufficient_grants_stop_without_ddl(monkeypatch):
    _engine, create = configure(monkeypatch, grants=["GRANT SELECT ON `court_test`.* TO `user`@`%`"])
    with pytest.raises(RuntimeError, match="Could not safely inspect"):
        init_db.main()
    create.assert_not_called()


def test_comparison_error_stops_without_ddl(monkeypatch):
    _engine, create = configure(monkeypatch, [{"object_type": "TABLE", "object_name": "sports"}])
    monkeypatch.setattr(init_db.MigrationContext, "configure", lambda *_args, **_kwargs: object())

    def fail_comparison(*_args):
        raise PermissionError("denied")

    monkeypatch.setattr(init_db, "compare_metadata", fail_comparison)
    with pytest.raises(RuntimeError, match="Could not compare"):
        init_db.main()
    create.assert_not_called()
