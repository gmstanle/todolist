#!/opt/homebrew/bin/python3

from __future__ import annotations

from pathlib import Path


TODO_PATH = Path(__file__).with_name("TODO.md")


def parse_todo_file(path: Path = TODO_PATH) -> tuple[list[str], list[str]]:
    active: list[str] = []
    done: list[str] = []
    section: str | None = None

    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped == "## Active":
            section = "active"
            continue
        if stripped == "## Done":
            section = "done"
            continue
        if stripped.startswith("- [ ] ") and section == "active":
            active.append(stripped[6:])
        elif stripped.startswith("- [x] ") and section == "done":
            done.append(stripped[6:])

    return active, done


def write_todo_file(active: list[str], done: list[str], path: Path = TODO_PATH) -> None:
    lines = ["# Todo", "", "## Active", ""]
    lines.extend(f"- [ ] {item}" for item in active)
    lines.extend(["", "## Done", ""])
    lines.extend(f"- [x] {item}" for item in done)
    lines.append("")
    path.write_text("\n".join(lines))


def find_index(items: list[str], query: str) -> int:
    lowered = query.casefold()
    exact = [i for i, item in enumerate(items) if item.casefold() == lowered]
    if exact:
        return exact[0]

    partial = [i for i, item in enumerate(items) if lowered in item.casefold()]
    if len(partial) == 1:
        return partial[0]
    if not partial:
        raise SystemExit(f'No matching item found for "{query}".')
    raise SystemExit(f'Ambiguous match for "{query}".')


def add_item(text: str) -> None:
    active, done = parse_todo_file()
    active.append(text)
    write_todo_file(active, done)


def move_by_query(query: str, source: str) -> None:
    active, done = parse_todo_file()
    if source == "active":
        index = find_index(active, query)
        done.append(active.pop(index))
    elif source == "done":
        index = find_index(done, query)
        active.append(done.pop(index))
    else:
        raise ValueError(f"Unsupported source section: {source}")
    write_todo_file(active, done)


def move_by_index(section: str, index: int) -> None:
    active, done = parse_todo_file()
    if section == "active":
        if index < 0 or index >= len(active):
            raise IndexError("Active item index out of range.")
        done.append(active.pop(index))
    elif section == "done":
        if index < 0 or index >= len(done):
            raise IndexError("Done item index out of range.")
        active.append(done.pop(index))
    else:
        raise ValueError(f"Unsupported section: {section}")
    write_todo_file(active, done)
