"""Configuration boundary regressions."""

from app.core.config import Settings


def test_mysql_url_uses_the_audited_async_driver() -> None:
    settings = Settings(
        database_url=None,
        db_user="app",
        db_password="safe-password",
        db_host="mysql",
        db_port=3306,
        db_name="platform",
    )

    assert settings.sqlalchemy_database_uri == (
        "mysql+aiomysql://app:safe-password@mysql:3306/platform?charset=utf8mb4"
    )
