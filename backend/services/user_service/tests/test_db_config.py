from __future__ import annotations

from app.db_config import user_database_url


def test_explicit_environment_url_wins_over_conflicting_dotenv(monkeypatch):
    expected = "mysql+pymysql://root:local@localhost:3306/sports_user_db"
    conflicting = "mysql+pymysql://root:dev@mysql-dev:3306/sports_user_db"
    monkeypatch.setenv("USER_DATABASE_URL", expected)
    dotenv_calls = []

    def conflicting_dotenv(*_args, **_kwargs):
        dotenv_calls.append(True)
        monkeypatch.setenv("USER_DATABASE_URL", conflicting)

    monkeypatch.setattr("app.db_config.load_dotenv", conflicting_dotenv)

    assert user_database_url() == expected
    assert user_database_url() != conflicting
    assert dotenv_calls == []
