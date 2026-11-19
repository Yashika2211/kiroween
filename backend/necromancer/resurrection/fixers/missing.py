"""Detect `ModuleNotFoundError` in sandbox output and map the module to a PyPI package."""

from __future__ import annotations

import re
import sys

# import name → PyPI distribution, for the common cases where they differ.
IMPORT_TO_PACKAGE: dict[str, str] = {
    "yaml": "PyYAML",
    "PIL": "pillow",
    "dateutil": "python-dateutil",
    "bs4": "beautifulsoup4",
    "sklearn": "scikit-learn",
    "cv2": "opencv-python",
    "Crypto": "pycryptodome",
    "OpenSSL": "pyOpenSSL",
    "jwt": "PyJWT",
    "magic": "python-magic",
    "dotenv": "python-dotenv",
    "serial": "pyserial",
    "usb": "pyusb",
    "git": "GitPython",
    "MySQLdb": "mysqlclient",
    "psycopg2": "psycopg2-binary",
    "google.protobuf": "protobuf",
    "zmq": "pyzmq",
    "lxml": "lxml",
    "attr": "attrs",
    "pkg_resources": "setuptools",
    "setuptools": "setuptools",
}

_PATTERN = re.compile(r"ModuleNotFoundError: No module named '([A-Za-z0-9_.]+)'")


def missing_modules(output: str) -> list[str]:
    seen: list[str] = []
    for name in _PATTERN.findall(output):
        top = name.split(".")[0]
        if top not in seen:
            seen.append(top)
    return seen


def package_for(module: str, local_modules: set[str]) -> str | None:
    """PyPI package for a missing top-level module, or None if it's local or stdlib-removed."""
    if module in local_modules:
        return None
    if module in sys.stdlib_module_names:
        return None
    return IMPORT_TO_PACKAGE.get(module, module)
