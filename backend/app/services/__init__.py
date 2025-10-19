"""
Services package init. Avoid importing heavy modules (like ai_services)
at package import time so tests that only need lightweight modules (e.g. nlu)
can run without loading full configuration/dependencies.
"""

from importlib import import_module


def get(service_name: str):
	"""Dynamically import and return a service module by name."""
	return import_module(f"app.services.{service_name}")

# Convenience: try to import nlu and memory for common lightweight usage
from . import nlu  # noqa: F401
from . import memory  # noqa: F401
