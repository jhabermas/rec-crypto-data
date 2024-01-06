import json
import logging
import os
from collections import defaultdict
from functools import partial

import jsonschema
import pytest

from rcd.util.mapping import map_api_data, map_ccxt_data, map_cryptofeed_data


def test_map_real_data():
    test_data_dir = os.path.abspath(os.path.join(".", "test_data"))
    schemas_dir = os.path.abspath(os.path.join(".", "schemas"))
    test_data = _load_exchange_data(test_data_dir)
    schemas = _load_json_schemas(schemas_dir)
    for source, exchanges in test_data.items():
        mapping_method = None
        match source:
            case "ccxt":
                mapping_method = map_ccxt_data
            case "cryptofeed":
                mapping_method = map_cryptofeed_data
            case "api":
                mapping_method = lambda a, b, c: map_api_data(a, b, "BTC/USDT", c)
            case _:
                raise RuntimeError(f"No mapping method for {source}")

        for exchange, channels in exchanges.items():
            for channel, data in channels.items():
                mapped_data = mapping_method(exchange, channel, data)[0]
                try:
                    jsonschema.validate(mapped_data, schemas[channel])
                    logging.info(f"Validating {source} {exchange} {channel}: PASS")
                except jsonschema.exceptions.ValidationError as e:
                    logging.error(
                        f"Failed validation of {source} {exchange} {channel} data: {e}"
                    )
                    logging.info(f"Mapped data: {mapped_data}")
                    raise


def _load_exchange_data(directory):
    data_dict = defaultdict(lambda: defaultdict(dict))

    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            try:
                exchange, channel, source = filename[:-5].split("_")
                with open(os.path.join(directory, filename), "r") as file:
                    data_dict[source][exchange][channel] = json.load(file)
            except json.JSONDecodeError:
                logging.error(f"Error parsing JSON file: {filename}")
            except ValueError:
                logging.error(f"Filename format error: {filename}")
            except Exception as e:
                logging.error(f"Error loading data from {filename}: {e}")
                raise

    return data_dict


def _load_json_schemas(directory):
    schemas = {}
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            file_path = os.path.join(directory, filename)
            with open(file_path, "r") as file:
                try:
                    schema = json.load(file)
                    schema_key = filename[:-5]
                    schemas[schema_key] = schema
                except json.JSONDecodeError:
                    logging.error(f"Error parsing JSON file: {filename}")

    return schemas
