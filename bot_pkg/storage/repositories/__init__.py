"""Repository layer — the ONLY place in this codebase that should hold a
Mongo `Collection` handle or call `find`/`update_one`/etc. directly.

Everything above this layer (services, handlers) works with plain dicts
and calls repository methods, never `db.<collection>` directly. That's
what makes it possible to unit-test services without a real Mongo, and to
change how something is stored without touching the code that uses it.
"""
