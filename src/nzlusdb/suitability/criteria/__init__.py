"""Module defining suitability criteria for lSA."""

import importlib
import pkgutil

__all__ = []

# Dynamically import all modules in this package
for _loader, module_name, _is_pkg in pkgutil.iter_modules(__path__):
    module = importlib.import_module(f"{__name__}.{module_name}")
    if hasattr(module, "__all__"):
        # Import all symbols listed in __all__ of the module
        for symbol in module.__all__:
            globals()[symbol] = getattr(module, symbol)
        __all__.extend(module.__all__)
