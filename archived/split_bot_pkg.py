#!/usr/bin/env python3
"""
split_bot_pkg.py
═════════════════
Splits the monolithic bot file into a REAL, importable Python PACKAGE
(real folders, real `import` statements, real per-file tracebacks) —
while still preserving the "later sections monkey-patch earlier
sections" behavior your bot relies on (EXPANSION PATCH / UX PATCH
redefining dispatch / new_player / market_keypad / etc).

WHY THIS WORKS
──────────────
Plain `from x import y` binds a name ONCE, at import time. If some
later module reassigns `x.y`, everyone who did `from x import y`
still has the OLD function — silent bug.

So instead, every top-level name (function, class, or module-level
variable) from every section is registered as an attribute on one
shared object: `registry.registry`. Every cross-section reference in
the generated code is rewritten to go through that object, e.g.
`dispatch(...)`  ->  `registry.dispatch(...)`.

Attribute access is looked up FRESH every single call. So when the
"UX PATCH" module later does `registry.dispatch = new_dispatch`,
every other file that calls `registry.dispatch(...)` automatically
starts calling the new one — exactly the behavior your monolithic
file had, but now with real files, real folders, and tracebacks that
point at the correct file + line.

This is a best-effort AUTOMATED source-to-source rewrite using the
`ast` module. It is NOT guaranteed to be 100% correct for every
possible Python construct (e.g. `globals()`/`eval`/`exec` tricks,
`nonlocal`, metaclass magic). Always smoke-test the generated package
before relying on it. See the generated SPLIT_README.md for details
and a checklist.

USAGE
─────
    python split_bot_pkg.py path/to/waste_syndicate_bot_v4_seasonal.py -o out_dir --pkg bot_pkg

Then:
    cd out_dir
    python run_bot.py
"""

from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path

BANNER_LINE = re.compile(r"^#\s*═{10,}\s*$")

KNOWN_SLUGS = {
    "CONFIG": "config",
    "TEXT SYSTEM": "texts",
    "GAME TABLES": "gamedata",
    "GLOBAL GAME STATE": "state",
    "UTILITIES": "utils",
    "SAVE / LOAD / MIGRATION": "persistence",
    "RUBIKA API": "rubika_api",
    "PLAYER HELPERS": "player",
    "ALLIANCE ECONOMY": "alliance_economy",
    "WOW FEATURES: NEWS / MISSIONS / CACHES / BOSS / MAP / GROUP RAID": "world_features",
    "MARKET": "market_core",
    "HANDLERS: REGISTRATION": "h_registration",
    "HANDLERS: MAIN / PROFILE": "h_profile",
    "HANDLERS: SCAVENGE": "h_scavenge",
    "HANDLERS: MARKET": "h_market",
    "HANDLERS: BUILDINGS / CRAFT": "h_buildings_craft",
    "HANDLERS: RAID / SHIELD": "h_raid_shield",
    "HANDLERS: ALLIANCE": "h_alliance",
    "HANDLERS: INVENTORY / DAILY / INVITE / SEASON / LEADERBOARD / HELP": "h_misc",
    "HANDLERS: PLAYER MESSAGES": "h_messages",
    "HANDLERS: ADMIN": "h_admin",
    "STATE HANDLER / DISPATCHER": "dispatcher",
    "UPDATE PROCESSING": "update_processing",
    "EXPANSION PATCH: SEASON / SMUGGLER / REVENGE / BOUNTY / CACHES / TERRITORIES": "expansion_patch",
    "UX PATCH: SAFE STATE ESCAPE + CLEAN MAIN MENU": "ux_patch",
    "MAIN LOOP": "main_loop",
}


# ─────────────────────────────────────────────────────────────────────────
# 1. Banner-based splitting (same idea as before)
# ─────────────────────────────────────────────────────────────────────────


def slugify(title: str, index: int) -> str:
    key = re.sub(r"\s+", " ", title.strip())
    base = KNOWN_SLUGS.get(key)
    if base is None:
        base = (
            re.sub(r"[^a-zA-Z0-9]+", "_", key.lower()).strip("_") or f"section{index}"
        )
        base = base[:40]
    return f"s{index:02d}_{base}"


def find_sections(lines: list[str]) -> list[tuple[str, int]]:
    sections = []
    i, n = 0, len(lines)
    while i < n - 2:
        if (
            BANNER_LINE.match(lines[i])
            and lines[i + 1].lstrip().startswith("#")
            and BANNER_LINE.match(lines[i + 2])
        ):
            title = lines[i + 1].lstrip("#").strip()
            sections.append((title, i))
            i += 3
        else:
            i += 1
    return sections


def slice_into_chunks(
    lines: list[str], sections: list[tuple[str, int]]
) -> list[tuple[str, int, int]]:
    """Returns list of (modname, start_line, end_line) covering the WHOLE file."""
    chunks = []
    header_end = sections[0][1] if sections else len(lines)
    if header_end > 0:
        chunks.append(("s00_header", 0, header_end))
    for idx, (title, start) in enumerate(sections, start=1):
        end = sections[idx][1] if idx < len(sections) else len(lines)
        chunks.append((slugify(title, idx), start, end))
    return chunks


# ─────────────────────────────────────────────────────────────────────────
# 2. Collect every "program-global" name (defined at true module scope,
#    anywhere in the whole file, in any section) — these are the names
#    that must be routed through the shared registry so cross-section
#    references and monkey-patches keep working.
# ─────────────────────────────────────────────────────────────────────────


class _TopLevelNameCollector(ast.NodeVisitor):
    """Collects Name(Store) targets that live at true module scope,
    i.e. not inside any function/class body. Descends into if/for/
    while/try/with at top level (those share module scope)."""

    def __init__(self):
        self.names: set[str] = set()

    def visit_FunctionDef(self, node):
        self.names.add(node.name)
        # do not descend: body is a new scope

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self.names.add(node.name)
        # do not descend into class body

    def visit_Lambda(self, node):
        return  # lambdas never introduce module-scope names

    def visit_Name(self, node):
        if isinstance(node.ctx, (ast.Store,)):
            self.names.add(node.id)

    def visit_For(self, node):
        self.visit(node.target)
        for n in node.iter, *node.body, *node.orelse:
            self.generic_visit_one(n)

    def generic_visit_one(self, node):
        if isinstance(node, ast.AST):
            self.visit(node)

    def visit_With(self, node):
        for item in node.items:
            if item.optional_vars:
                self.visit(item.optional_vars)
        for n in node.body:
            self.visit(n)

    def visit_Try(self, node):
        for n in node.body:
            self.visit(n)
        for h in node.handlers:
            if h.name:
                self.names.add(h.name)
            for n in h.body:
                self.visit(n)
        for n in node.orelse:
            self.visit(n)
        for n in node.finalbody:
            self.visit(n)


class _GlobalStmtCollector(ast.NodeVisitor):
    """Collects every name mentioned in any `global x` statement,
    anywhere in the file (these are program-globals too, even if a
    section never assigns them at true top level)."""

    def __init__(self):
        self.names: set[str] = set()

    def visit_Global(self, node):
        self.names.update(node.names)


def collect_exported_names(tree: ast.Module) -> set[str]:
    top = _TopLevelNameCollector()
    for stmt in tree.body:
        top.visit(stmt)
    glob = _GlobalStmtCollector()
    glob.visit(tree)
    return top.names | glob.names


# ─────────────────────────────────────────────────────────────────────────
# 3. Scope-aware rewrite: replace references to exported names with
#    `registry.<name>`, but leave genuine local variables alone.
# ─────────────────────────────────────────────────────────────────────────


class _FuncLocalsCollector(ast.NodeVisitor):
    """For one function body: collect (a) every locally-bound name
    (params + any Store target), (b) every name declared `global`.
    Does NOT descend into nested function/class bodies (their own
    scope) except to note their def-name as a local binding here."""

    def __init__(self):
        self.locals: set[str] = set()
        self.globals: set[str] = set()

    def visit_FunctionDef(self, node):
        self.locals.add(node.name)  # nested def name is local here

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self.locals.add(node.name)

    def visit_Lambda(self, node):
        return

    def visit_Global(self, node):
        self.globals.update(node.names)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self.locals.add(node.id)

    def visit_comprehension(self, node):
        self.visit(node.target)
        for n in [node.iter, *node.ifs]:
            self.visit(n)

    def visit_ExceptHandler(self, node):
        if node.name:
            self.locals.add(node.name)
        for n in node.body:
            self.visit(n)

    def visit_withitem(self, node):
        if node.optional_vars:
            self.visit(node.optional_vars)


def _collect_func_scope(func_node) -> tuple[set[str], set[str]]:
    c = _FuncLocalsCollector()
    for stmt in func_node.body:
        c.visit(stmt)
    args = func_node.args
    for a in list(args.args) + list(args.posonlyargs) + list(args.kwonlyargs):
        c.locals.add(a.arg)
    if args.vararg:
        c.locals.add(args.vararg.arg)
    if args.kwarg:
        c.locals.add(args.kwarg.arg)
    return c.locals, c.globals


class RegistryRewriter(ast.NodeTransformer):
    """Rewrites Name(Load/Store) references to exported/global names
    into `registry.<name>` attribute access, everywhere EXCEPT inside
    a scope where that name is a genuine local variable."""

    def __init__(self, exported: set[str]):
        self.exported = exported
        self.scopes: list[set[str]] = [set()]  # stack of locally-shadowed names

    # -- scope-introducing nodes -------------------------------------
    def _visit_func(self, node):
        local_names, global_decls = _collect_func_scope(node)
        shadow = local_names - global_decls
        node.args = self.generic_visit(node.args)
        self.scopes.append(shadow)
        new_body = []
        for stmt in node.body:
            if isinstance(stmt, ast.Global):
                # names declared global-and-exported are handled via
                # registry attribute access instead; drop the decl.
                remaining = [n for n in stmt.names if n not in self.exported]
                if remaining:
                    stmt.names = remaining
                    new_body.append(stmt)
                continue
            new_body.append(self.visit(stmt))
        node.body = new_body
        node.decorator_list = [self.visit(d) for d in node.decorator_list]
        if node.returns:
            node.returns = self.visit(node.returns)
        self.scopes.pop()
        return node

    def visit_FunctionDef(self, node):
        return self._visit_func(node)

    def visit_AsyncFunctionDef(self, node):
        return self._visit_func(node)

    def visit_Lambda(self, node):
        params = {
            a.arg
            for a in list(node.args.args)
            + list(node.args.posonlyargs)
            + list(node.args.kwonlyargs)
        }
        if node.args.vararg:
            params.add(node.args.vararg.arg)
        if node.args.kwarg:
            params.add(node.args.kwarg.arg)
        self.scopes.append(params)
        node.body = self.visit(node.body)
        self.scopes.pop()
        return node

    def visit_ClassDef(self, node):
        self.scopes.append(set())
        node.bases = [self.visit(b) for b in node.bases]
        node.keywords = [self.visit(k) for k in node.keywords]
        node.decorator_list = [self.visit(d) for d in node.decorator_list]
        node.body = [self.visit(s) for s in node.body]
        self.scopes.pop()
        return node

    def visit_ListComp(self, node):
        return self._visit_comp(node)

    def visit_SetComp(self, node):
        return self._visit_comp(node)

    def visit_DictComp(self, node):
        return self._visit_comp(node)

    def visit_GeneratorExp(self, node):
        return self._visit_comp(node)

    def _visit_comp(self, node):
        targets = set()
        for gen in node.generators:
            for n in ast.walk(gen.target):
                if isinstance(n, ast.Name):
                    targets.add(n.id)
        self.scopes.append(targets)
        self.generic_visit(node)
        self.scopes.pop()
        return node

    # -- the actual rewrite -------------------------------------------
    def _is_shadowed(self, name: str) -> bool:
        return any(name in s for s in self.scopes)

    def visit_Name(self, node):
        name = node.id
        if name in self.exported and not self._is_shadowed(name):
            if isinstance(node.ctx, ast.Del):
                return node  # leave `del x` alone (rare / edge case)
            new = ast.Attribute(
                value=ast.Name(id="registry", ctx=ast.Load()),
                attr=name,
                ctx=node.ctx,
            )
            return ast.copy_location(new, node)
        return node


# ─────────────────────────────────────────────────────────────────────────
# 4. Emit the package
# ─────────────────────────────────────────────────────────────────────────

REGISTRY_MODULE = '''# -*- coding: utf-8 -*-
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
'''

INIT_TEMPLATE = '''# -*- coding: utf-8 -*-
"""Auto-generated package __init__.

Imports every split module IN ORIGINAL ORDER. Import order matters:
later modules intentionally overwrite names on `registry` that were
set by earlier modules (that's how the EXPANSION PATCH / UX PATCH
sections work).
"""
from .registry import registry  # noqa: F401

{imports}

__all__ = ["registry"]
'''

RUN_TEMPLATE = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entry point. Importing {pkg} runs every split module in order and
populates the registry; `main` was defined in the MAIN LOOP section.

Note: `{pkg}.registry` is the shared registry INSTANCE (see
{pkg}/__init__.py), not the `registry.py` submodule -- the instance
import shadows the submodule name on purpose, so this is just
`registry.main()`, not `registry.registry.main()`."""
from {pkg} import registry

if __name__ == "__main__":
    registry.main()
'''


def build_module_source(
    header_imports: str, module_name: str, exported: set[str], stmt_src: str
) -> str:
    body = (
        f"from .registry import registry  # noqa: F401\n{header_imports}\n\n{stmt_src}"
    )
    return body


def _inject_exports(stmts: list[ast.stmt]) -> list[ast.stmt]:
    """After every top-level `def foo` / `class Foo`, insert
    `registry.foo = foo` so the registry actually gets populated.
    (Plain top-level variable assigns don't need this: the
    RegistryRewriter already turns `PLAYERS = {}` directly into
    `registry.PLAYERS = {}` via Store-context rewriting.)"""
    out: list[ast.stmt] = []
    for stmt in stmts:
        out.append(stmt)
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            export = ast.Assign(
                targets=[
                    ast.Attribute(
                        value=ast.Name(id="registry", ctx=ast.Load()),
                        attr=stmt.name,
                        ctx=ast.Store(),
                    )
                ],
                value=ast.Name(id=stmt.name, ctx=ast.Load()),
            )
            for n in ast.walk(export):
                ast.copy_location(n, stmt)
            out.append(export)
    return out


def render(tree_body_slice, exported: set[str]) -> str:
    # 1) Rewrite cross-section references to `registry.<name>` FIRST.
    #    (Top-level `def foo` keeps binding a plain local `foo`, since
    #    FunctionDef.name is not a Name node the rewriter touches.)
    mod = ast.Module(body=list(tree_body_slice), type_ignores=[])
    rewritten = RegistryRewriter(exported).visit(mod)
    # 2) THEN inject `registry.foo = foo` after each top-level def/class,
    #    using the still-plain local `foo` on the right-hand side. Doing
    #    this after the rewrite avoids the injected line itself being
    #    turned into a no-op `registry.foo = registry.foo`.
    rewritten.body = _inject_exports(rewritten.body)
    ast.fix_missing_locations(rewritten)
    return ast.unparse(rewritten)


def collect_header_imports(header_tree_body) -> str:
    """Pull out `import ...` / `from ... import ...` statements from the
    header section so we can prepend them to EVERY generated module
    (simplest way to guarantee every file has the stdlib/3rd-party
    names it needs, without doing full per-name import analysis)."""
    lines = []
    for stmt in header_tree_body:
        if isinstance(stmt, ast.ImportFrom) and stmt.module == "__future__":
            continue
        if isinstance(stmt, (ast.Import, ast.ImportFrom)):
            lines.append(ast.unparse(stmt))
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("source", type=Path, help="Path to the original bot .py file")
    ap.add_argument(
        "-o", "--out", type=Path, default=Path("bot_pkg_out"), help="Output directory"
    )
    ap.add_argument(
        "--pkg", default="bot_pkg", help="Python package name (folder inside --out)"
    )
    args = ap.parse_args()

    if not args.source.exists():
        raise SystemExit(f"Source file not found: {args.source}")

    text = args.source.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    sections = find_sections(lines)
    if not sections:
        raise SystemExit(
            "No section banners found (expected the '# ══...' / '#  TITLE' / '# ══...' style)."
        )

    chunks = slice_into_chunks(lines, sections)

    full_tree = ast.parse(text, filename=str(args.source))
    exported = collect_exported_names(full_tree)

    # Map each top-level statement (by line number) to its chunk.
    def chunk_for_lineno(lineno: int) -> int:
        # lineno is 1-based; chunk ranges are 0-based [start,end)
        for i, (_, start, end) in enumerate(chunks):
            if start < lineno <= end:
                return i
        return len(chunks) - 1

    per_chunk_stmts: list[list[ast.stmt]] = [[] for _ in chunks]
    for stmt in full_tree.body:
        per_chunk_stmts[chunk_for_lineno(stmt.lineno)].append(stmt)

    header_imports = (
        collect_header_imports(per_chunk_stmts[0])
        if chunks[0][0] == "s00_header"
        else ""
    )

    pkg_dir = args.out / args.pkg
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "registry.py").write_text(REGISTRY_MODULE, encoding="utf-8")
    print("  wrote registry.py")

    written_modnames = []
    for (modname, _, _), stmts in zip(chunks, per_chunk_stmts):
        if not stmts:
            continue
        body_src = render(stmts, exported)
        # Header module: keep its imports as real imports (not registry-routed
        # since they're `import x` statements, ast.unparse already emits them
        # normally); everything else is prefixed with `from .registry import registry`.
        if modname == "s00_header":
            future_lines = []
            rest_stmts = []
            for s in stmts:
                if isinstance(s, ast.ImportFrom) and s.module == "__future__":
                    future_lines.append(ast.unparse(s))
                else:
                    rest_stmts.append(s)
            rest_src = render(rest_stmts, exported) if rest_stmts else ""
            future_block = ("\n".join(future_lines) + "\n\n") if future_lines else ""
            file_src = f'{future_block}# -*- coding: utf-8 -*-\n"""Original header: shebang/docstring/imports."""\nfrom .registry import registry  # noqa: F401\n{rest_src}\n'
        else:
            file_src = f"# -*- coding: utf-8 -*-\nfrom .registry import registry  # noqa: F401\n{header_imports}\n\n{body_src}\n"

        path = pkg_dir / f"{modname}.py"
        try:
            compile(file_src, str(path), "exec")
        except SyntaxError as e:
            raise SystemExit(
                f"\nGENERATION FAILED for {modname}.py: {e}\nThis usually means a construct the AST "
                f"rewriter doesn't handle yet — please share that section so it can be special-cased."
            )
        path.write_text(file_src, encoding="utf-8")
        written_modnames.append(modname)
        print(f"  wrote {args.pkg}/{modname}.py")

    imports_block = "\n".join(
        f"from . import {m}  # noqa: F401"
        for m in written_modnames
        if m != "s00_header"
    )
    (pkg_dir / "__init__.py").write_text(
        INIT_TEMPLATE.format(imports=imports_block), encoding="utf-8"
    )
    print("  wrote __init__.py")

    (args.out / "run_bot.py").write_text(
        RUN_TEMPLATE.format(pkg=args.pkg), encoding="utf-8"
    )
    print("  wrote run_bot.py")

    readme = f"""# {args.pkg} — real package layout

Generated by `split_bot_pkg.py`. Run with:

```
cd {args.out}
python run_bot.py
```

## How this differs from the plain "exec files in order" splitter

Every module-level name (function, class, module variable) is stored on
one shared object, `registry.registry`, instead of a bare Python global.
Cross-section calls were rewritten from `foo(...)` to `registry.foo(...)`.
Because attribute lookups happen at CALL TIME, later sections (the old
EXPANSION PATCH / UX PATCH) can still safely do
`registry.dispatch = new_dispatch` and have it take effect everywhere —
same behavior as the original single file, but with:

- Real folders/files you can navigate and fold in your editor.
- Real per-file tracebacks (`{args.pkg}/s21_expansion_patch.py`, line N).
- A real debugger breakpoint experience (set breakpoints per file).
- A real `import {args.pkg}` you can use from a test script/REPL.

## Files, in execution/import order

{chr(10).join(f"- `{args.pkg}/{m}.py`" for m in written_modnames)}

## Known limitations of the automated rewrite — please smoke-test

This is an AST-based automated migration, not a hand review. It correctly
handles ordinary functions, classes, module-level variables, `global`
statements, comprehensions, and nested functions/lambdas. It does **not**
attempt to fix:

- Code that uses `globals()`, `eval()`, or `exec()` to look up names
  dynamically by string — these still refer to each file's own private
  namespace, not the registry.
- `nonlocal` inside deeply nested closures referring to something that
  used to be a true module global (rare, but worth grepping for).
- Any decorator or default-argument expression evaluated at class/def
  time that itself depends on a name defined later in the file — with
  a single file this worked by having already run top-to-bottom; if a
  decorator now references `registry.something` before that something
  is set, you'll get an AttributeError instead of a silent NameError,
  which is easy to spot and fix.

Run your bot's test suite (or at least start it and click through the
handlers you use most) after generating this package, before deploying.
Regenerate the whole folder any time by re-running `split_bot_pkg.py`
on the current source file — don't hand-edit both the source and the
generated package separately, or they'll drift.
"""
    (args.out / "SPLIT_README.md").write_text(readme, encoding="utf-8")
    print("  wrote SPLIT_README.md")

    print(f"\nDone. {len(written_modnames)} module(s) written under {pkg_dir}/")
    print(f"Copy your data/config files next to {args.out}/run_bot.py, then:")
    print(f"  cd {args.out} && python run_bot.py")


if __name__ == "__main__":
    main()
