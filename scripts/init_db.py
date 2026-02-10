#!/usr/bin/env python3
"""Run Alembic migrations programmatically.

Usage:
    python -m scripts.init_db

Equivalent to: alembic upgrade head
"""

import sys

sys.path.insert(0, ".")

from alembic import command
from alembic.config import Config


def main() -> None:
    alembic_cfg = Config("alembic.ini")
    print("Running database migrations...")
    command.upgrade(alembic_cfg, "head")
    print("Migrations complete.")


if __name__ == "__main__":
    main()
