"""
Shared registry — replaces the implicit shared module-namespace that
the original single-file script relied on for its monkey-patch
sections. Every module-level name (function, class, or variable) from
every split file lives here as an attribute. Because attribute lookup
happens fresh on every call, later sections reassigning
`registry.dispatch = new_dispatch` correctly affects every caller —
this is what keeps EXPANSION PATCH / UX PATCH working.
"""


class _Registry:
    pass


registry = _Registry()
