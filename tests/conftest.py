import os
import sys
import pytest
import logging

from dynaconf import Dynaconf

from hydra.ingestion.crypto.historical import initialize_exchange
from hydra.config.validation import is_supported_exchange

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def pytest_collection_modifyitems(config, items):
    settings = Dynaconf(settings_files=["config/config.toml"])

    if not settings.run_integration_tests:
        skip_integration = pytest.mark.skip(reason=f"Skipping integration test")
        for item in items:
            if 'integration' in item.keywords:
                item.add_marker(skip_integration)


@pytest.fixture(scope="session")
def settings():
    return Dynaconf(
        envvar_prefix="DYNACONF",
        settings_files=["config/config.toml"]
        # environments=True,
        # env="testing"
    )


def validate_exchange(exchange_id):
    assert is_supported_exchange(exchange_id)


@pytest.fixture(scope="session")
def exchange_instances(settings):
    instances = {}
    logging.info(f"Crating exchange instances from settings: {settings.to_dict()}")
    for exchange, config in settings.exchanges.items():
        exchange_id = config.id
        validate_exchange(exchange_id)
        instances[exchange_id] = initialize_exchange(
            exchange_id,
            settings.rate_limit,
            settings.enable_rate_limit
        )
    return instances


@pytest.fixture(scope="session")
def exchange_instance(exchange_instances):
    test_exchage = 'binance'
    logging.info(f"Using {test_exchage} as test exchange")
    return exchange_instances[test_exchage]


# Note: fixtures are also good for loading data from files for tests
# They can also be scoped by placing conftest.py in subdirectories
