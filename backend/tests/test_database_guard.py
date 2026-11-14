"""The tests empty their database, so they must never be pointed at real data."""

import pytest

from conftest import TEST_DATABASE_URL, refuse_unsafe_test_database
from marinescope import config

APP = "postgresql+psycopg://marinescope:pw@127.0.0.1:5432/marinescope"


def test_default_test_database_is_accepted():
    refuse_unsafe_test_database(TEST_DATABASE_URL, config.database_url())


@pytest.mark.parametrize(
    "test_url",
    [
        APP,  # exactly the application database
        "postgresql+psycopg://other:pw@127.0.0.1/marinescope",  # same database, other user, default port
        "postgresql+psycopg://marinescope:pw@127.0.0.1:5432/production",  # not named *_test
        "postgresql+psycopg://marinescope:pw@127.0.0.1:5432/postgres",
    ],
)
def test_unsafe_test_database_is_refused(test_url):
    with pytest.raises(pytest.UsageError, match="Refusing to run"):
        refuse_unsafe_test_database(test_url, APP)


def test_application_database_is_refused_even_if_named_like_a_test_database():
    url = "postgresql+psycopg://marinescope:pw@127.0.0.1:5432/app_test"
    with pytest.raises(pytest.UsageError):
        refuse_unsafe_test_database(url, url)
