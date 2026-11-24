import os
import django
from django.conf import settings
from django.db import connections
from django.db.backends.postgresql.creation import DatabaseCreation
from django.db.backends.utils import strip_quotes
import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("MEDORA_TESTING", "1")
os.environ.setdefault("DJANGO_SECRET_KEY", "isolated-test-key-which-is-never-used-in-production")


def pytest_configure(config):
    if not settings.TESTING:
        raise pytest.UsageError("Run tests with MEDORA_TESTING=1 and isolated PostgreSQL.")


@pytest.fixture(scope="session")
def django_db_modify_db_settings():
    django.setup()
    connection = connections["default"]
    original = connection.creation._create_test_db

    def create(verbosity, autoclobber, keepdb=False):
        name = original(verbosity, autoclobber, keepdb)
        params = connection.get_connection_params()
        params["dbname"] = strip_quotes(name)
        schema = settings.DATABASES["default"]["OPTIONS"]["options"].split("=")[1]
        with connection.Database.connect(**params, autocommit=True) as conn:
            conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
        return name

    assert isinstance(connection.creation, DatabaseCreation)
    connection.creation._create_test_db = create
