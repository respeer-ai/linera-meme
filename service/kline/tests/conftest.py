import sys


STUBBABLE_MODULES = (
    'async_request',
    'db',
    'fastapi',
    'fastapi.responses',
    'mysql',
    'mysql.connector',
    'numpy',
    'pandas',
    'swap',
    'uvicorn',
)


def _remove_stubbed_modules():
    for module_name in STUBBABLE_MODULES:
        module = sys.modules.get(module_name)
        if module is not None and not getattr(module, '__file__', None):
            sys.modules.pop(module_name, None)


def pytest_pycollect_makemodule(module_path, parent):
    _remove_stubbed_modules()
    return None
