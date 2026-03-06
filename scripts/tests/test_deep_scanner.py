import importlib

import pytest


def test_deep_scanner_module_has_been_removed():
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("etl.deep_scanner")
