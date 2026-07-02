"""Materialize a spec's optional `runtime` block (storage/memory/routines) into a built plugin tree.
Pure filesystem; called during/after assembly, before packaging. No-op when runtime is empty."""
from __future__ import annotations
from pathlib import Path


def materialize_runtime(runtime: dict, tree: Path) -> list[str]:
    runtime = runtime or {}
    tree = Path(tree)
    touched: list[str] = []
    readme_chunks: list[str] = []

    # Only storage entries with a `where` create a dir AND get a README line — an entry
    # without one has nothing to materialize, so it must not render a bogus `None` bullet.
    storage = [s for s in (runtime.get("storage") or []) if s.get("where")]
    for s in storage:
        (tree / s["where"]).mkdir(parents=True, exist_ok=True)
        touched.append(str(tree / s["where"]))
    if storage:
        readme_chunks.append("## Storage\n" + "\n".join(
            f"- `{s['where']}` — {s.get('what')} ({s.get('kind')})" for s in storage))

    memory = runtime.get("memory") or []
    if memory:
        readme_chunks.append("## Memory\nThis plugin persists facts under `memory/`:\n" + "\n".join(
            f"- **{m.get('fact_type')}** — {m.get('note')}" for m in memory))

    routines = runtime.get("routines") or []
    if routines:
        readme_chunks.append("## Scheduling\nRegister these with `/schedule`:\n" + "\n".join(
            f"- `{r.get('name')}` (`{r.get('schedule')}`) — {r.get('does')}" for r in routines))

    if readme_chunks:
        readme = tree / "README.md"
        prefix = (readme.read_text(encoding="utf-8") + "\n\n") if readme.exists() else ""
        readme.write_text(prefix + "\n\n".join(readme_chunks) + "\n", encoding="utf-8")
        touched.append(str(readme))
    return touched


if __name__ == "__main__":
    import json, sys
    spec = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8")) if len(sys.argv) > 2 else {}
    print(materialize_runtime(spec.get("runtime", {}), Path(sys.argv[1])))
