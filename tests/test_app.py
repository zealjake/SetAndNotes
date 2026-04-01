from importlib import import_module


def test_app_module_exposes_main_entrypoint():
    module = import_module("setandnotes.app")

    assert callable(module.main)


def test_package_main_module_exposes_main_entrypoint():
    module = import_module("setandnotes.__main__")

    assert callable(module.main)
