"""Pure game-logic layer.

Rules for anything in this package:
  - No `registry` import.
  - No I/O: no `send`, no `save_game`, no Mongo, no Rubika API calls.
  - No text formatting / i18n (`registry.T(...)`) — that belongs to the
    handler, which turns a service's result into a message.
  - Randomness comes in through a `random.Random` parameter (defaults to
    a fresh one), never the bare `random` module, so outcomes are
    reproducible in tests.

A function here should be callable from a plain pytest test with plain
dicts, no mocking of `registry` required. If you find yourself reaching
for `registry.something()` inside a service function, that dependency
either needs to be passed in as a parameter, or the function belongs in
the handler instead.
"""
