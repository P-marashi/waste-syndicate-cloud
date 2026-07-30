#!/usr/bin/env python3
"""Entry point. Importing bot_pkg runs every split module in order and
populates the registry; `main` was defined in the MAIN LOOP section.

Note: `bot_pkg.registry` is the shared registry INSTANCE (see
bot_pkg/__init__.py), not the `registry.py` submodule -- the instance
import shadows the submodule name on purpose, so this is just
`registry.main()`, not `registry.registry.main()`."""

from dotenv import load_dotenv

load_dotenv()


from bot_pkg import registry

if __name__ == "__main__":
    registry.main()
