# path: policylens/manage.py
"""
Django management entrypoint for PolicyLens.

This file is intentionally kept close to Django defaults to reduce surprises
when running management commands locally, in Docker, and in CI.
"""

import os
import sys


def main() -> None:
    """Run Django management commands."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line  # noqa: WPS433

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
