#!/opt/homebrew/bin/python3

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


TODO_PATH = Path(__file__).with_name("TODO.md")
BLOCKED_DELIMITER = " | blocked-by: "
RELEASED_PREFIX = " <!-- released-by: "
RELEASED_SUFFIX = " -->"

APPLICATION_TARGETS = {
    "applications",
    "apply to any jobs",
    "apply to more jobs",
    "apply to jobs",
    "applying to any jobs",
    "applying to more jobs",
    "applying to jobs",
    "job applications",
    "sending in more requests",
    "sending more requests",
}
FOLLOW_UP_TARGETS = {"follow ups", "follow-up tasks", "follow-ups", "followups"}
REFERRAL_TARGETS = {"referral tasks", "referrals"}
APPLICATION_PREFIXES = ("apply to ", "send application", "submit application")
FOLLOW_UP_PREFIXES = ("follow up",)
LEADING_BLOCKER_PHRASES = (
    "i want to ",
    "i need to ",
    "i should ",
    "please ",
    "to ",
)


class TodoError(Exception):
    """Raised when a todo command cannot be applied deterministically."""


@dataclass(frozen=True, slots=True)
class TaskItem:
    text: str
    released_by: str | None = None


@dataclass(frozen=True, slots=True)
class BlockedItem:
    text: str
    blocker: str


def parse_todo_file(
    path: Path = TODO_PATH,
) -> tuple[list[TaskItem], list[BlockedItem], list[TaskItem]]:
    active: list[TaskItem] = []
    blocked: list[BlockedItem] = []
    done: list[TaskItem] = []
    section: str | None = None

    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped == "## Active":
            section = "active"
            continue
        if stripped == "## Blocked":
            section = "blocked"
            continue
        if stripped == "## Done":
            section = "done"
            continue
        if stripped.startswith("- [ ] ") and section == "active":
            active.append(parse_task_item(stripped[6:]))
        elif stripped.startswith("- [ ] ") and section == "blocked":
            blocked.append(parse_blocked_item(stripped[6:]))
        elif stripped.startswith("- [x] ") and section == "done":
            done.append(parse_task_item(stripped[6:]))

    return active, blocked, done


def write_todo_file(
    active: list[TaskItem],
    blocked: list[BlockedItem],
    done: list[TaskItem],
    path: Path = TODO_PATH,
) -> None:
    lines = ["# Todo", "", "## Active", ""]
    lines.extend(f"- [ ] {format_task_item(item)}" for item in active)
    lines.extend(["", "## Blocked", ""])
    lines.extend(f"- [ ] {format_blocked_item(item)}" for item in blocked)
    lines.extend(["", "## Done", ""])
    lines.extend(f"- [x] {format_task_item(item)}" for item in done)
    lines.append("")
    path.write_text("\n".join(lines))


def add_item(text: str, path: Path = TODO_PATH) -> dict[str, object]:
    clean_text = text.strip()
    if not clean_text:
        raise TodoError("Text is required.")

    active, blocked, done = parse_todo_file(path)
    active.append(TaskItem(clean_text))
    write_todo_file(active, blocked, done, path)
    return {"action": "add", "message": f'Added "{clean_text}".'}


def apply_text_command(text: str, path: Path = TODO_PATH) -> dict[str, object]:
    clean_text = text.strip()
    if not clean_text:
        raise TodoError("Text is required.")

    if match := re.fullmatch(
        r"(?is)^do\s+(?P<blocker>.+?)\s+before\s+(?P<target>.+)$",
        clean_text,
    ):
        return block_matching_tasks(match.group("blocker"), match.group("target"), path)
    if match := re.fullmatch(
        r"(?is)^(?P<blocker>.+?)\s+before\s+(?P<target>.+)$",
        clean_text,
    ):
        return block_matching_tasks(match.group("blocker"), match.group("target"), path)
    if match := re.fullmatch(
        r"(?is)^don'?t\s+(?:do\s+)?(?P<target>.+?)\s+until\s+(?P<blocker>.+)$",
        clean_text,
    ):
        return block_matching_tasks(match.group("blocker"), match.group("target"), path)
    if match := re.fullmatch(
        r"(?is)^block\s+(?P<target>.+?)\s+on\s+(?P<blocker>.+)$",
        clean_text,
    ):
        return block_matching_tasks(match.group("blocker"), match.group("target"), path)
    if match := re.fullmatch(r"(?is)^unblock\s+(?P<target>.+)$", clean_text):
        return unblock_matching_tasks(match.group("target"), path)
    if match := re.fullmatch(
        r"(?is)^i\s+(?:did|finished|completed)\s+(?P<blocker>.+)$",
        clean_text,
    ):
        return complete_blocker(match.group("blocker"), path)

    return add_item(clean_text, path)


def move_by_query(query: str, source: str, path: Path = TODO_PATH) -> dict[str, object]:
    active, blocked, done = parse_todo_file(path)
    if source == "active":
        index = find_index(active, query)
        return complete_active_item(index, active, blocked, done, path)
    if source == "blocked":
        index = find_index(blocked, query)
        return unblock_blocked_item(index, active, blocked, done, path)
    if source == "done":
        index = find_index(done, query)
        return undo_done_item(index, active, blocked, done, path)
    raise ValueError(f"Unsupported source section: {source}")


def move_by_index(section: str, index: int, path: Path = TODO_PATH) -> dict[str, object]:
    active, blocked, done = parse_todo_file(path)
    if section == "active":
        if index < 0 or index >= len(active):
            raise IndexError("Active item index out of range.")
        return complete_active_item(index, active, blocked, done, path)
    if section == "blocked":
        if index < 0 or index >= len(blocked):
            raise IndexError("Blocked item index out of range.")
        return unblock_blocked_item(index, active, blocked, done, path)
    if section == "done":
        if index < 0 or index >= len(done):
            raise IndexError("Done item index out of range.")
        return undo_done_item(index, active, blocked, done, path)
    raise ValueError(f"Unsupported section: {section}")


def block_matching_tasks(
    blocker_input: str,
    target_query: str,
    path: Path = TODO_PATH,
) -> dict[str, object]:
    active, blocked, done = parse_todo_file(path)
    blocker_title = canonicalize_blocker_title(blocker_input)
    if not blocker_title:
        raise TodoError("Blocker text is required.")

    existing_active = find_item_by_title(active, blocker_title)
    existing_done = find_item_by_title(done, blocker_title)
    blocker_is_new = False

    if existing_done is not None:
        blocked, restored = release_tasks_for_blocker(blocked, existing_done.text)
        active.extend(restored)
        write_todo_file(active, blocked, done, path)
        message = (
            f'Blocker "{existing_done.text}" is already done, so matching tasks stayed active.'
        )
        if restored:
            message = (
                f'Blocker "{existing_done.text}" was already done and unblocked '
                f"{len(restored)} task{pluralize(restored)}."
            )
        return {"action": "block-satisfied", "message": message}

    if existing_active is None:
        active.append(TaskItem(blocker_title))
        blocker_is_new = True
    else:
        blocker_title = existing_active.text

    match_indices = find_matching_indices(
        active,
        target_query,
        allow_empty=True,
        exclude_normalized={normalize_for_match(blocker_title)},
    )
    if not match_indices:
        write_todo_file(active, blocked, done, path)
        if blocker_is_new:
            return {
                "action": "block",
                "message": (
                    f'Added blocker "{blocker_title}", but found no matching tasks to block.'
                ),
            }
        return {
            "action": "block",
            "message": f'No matching active tasks found for "{target_query.strip()}".',
        }

    match_set = set(match_indices)
    moved: list[TaskItem] = []
    remaining_active: list[TaskItem] = []
    for i, item in enumerate(active):
        if i in match_set:
            moved.append(item)
        else:
            remaining_active.append(item)

    blocked.extend(BlockedItem(text=item.text, blocker=blocker_title) for item in moved)
    write_todo_file(remaining_active, blocked, done, path)

    blocker_message = "Added blocker" if blocker_is_new else "Using blocker"
    return {
        "action": "block",
        "message": (
            f'{blocker_message} "{blocker_title}" and blocked '
            f"{len(moved)} task{pluralize(moved)}."
        ),
    }


def unblock_matching_tasks(target_query: str, path: Path = TODO_PATH) -> dict[str, object]:
    active, blocked, done = parse_todo_file(path)
    indices = find_matching_indices(blocked, target_query)
    restored: list[TaskItem] = []
    remaining_blocked: list[BlockedItem] = []
    match_set = set(indices)

    for i, item in enumerate(blocked):
        if i in match_set:
            restored.append(TaskItem(text=item.text))
        else:
            remaining_blocked.append(item)

    active.extend(restored)
    write_todo_file(active, remaining_blocked, done, path)
    return {
        "action": "unblock",
        "message": f'Unblocked {len(restored)} task{pluralize(restored)}.',
    }


def complete_blocker(blocker_query: str, path: Path = TODO_PATH) -> dict[str, object]:
    active, blocked, done = parse_todo_file(path)
    try:
        index = find_index(active, blocker_query)
    except TodoError:
        blocker_title = find_matching_blocker_title(blocked, blocker_query)
        if blocker_title is None:
            if find_item_by_title(done, blocker_query) is not None:
                return {
                    "action": "complete",
                    "message": f'Blocker "{blocker_query.strip()}" is already done.',
                }
            raise

        blocked, restored = release_tasks_for_blocker(blocked, blocker_title)
        if find_item_by_title(done, blocker_title) is None:
            done.append(TaskItem(blocker_title))
        active.extend(restored)
        write_todo_file(active, blocked, done, path)
        return {
            "action": "complete",
            "message": (
                f'Completed "{blocker_title}" and unblocked '
                f"{len(restored)} task{pluralize(restored)}."
            ),
        }

    return complete_active_item(index, active, blocked, done, path)


def complete_active_item(
    index: int,
    active: list[TaskItem],
    blocked: list[BlockedItem],
    done: list[TaskItem],
    path: Path,
) -> dict[str, object]:
    task = active.pop(index)
    blocked, restored = release_tasks_for_blocker(blocked, task.text)
    done.append(task)
    active.extend(restored)
    write_todo_file(active, blocked, done, path)

    if restored:
        return {
            "action": "complete",
            "message": (
                f'Completed "{task.text}" and unblocked '
                f"{len(restored)} task{pluralize(restored)}."
            ),
        }
    return {"action": "complete", "message": f'Completed "{task.text}".'}


def undo_done_item(
    index: int,
    active: list[TaskItem],
    blocked: list[BlockedItem],
    done: list[TaskItem],
    path: Path,
) -> dict[str, object]:
    item = done.pop(index)

    if item.released_by is not None and not blocker_is_done(done, item.released_by):
        blocked.append(BlockedItem(text=item.text, blocker=item.released_by))
        write_todo_file(active, blocked, done, path)
        return {
            "action": "undo",
            "message": (
                f'Moved "{item.text}" back to Blocked because '
                f'"{item.released_by}" is not done.'
            ),
        }

    active.append(item)
    active, reblocked = reblock_tasks_for_blocker(active, item.text)
    blocked.extend(reblocked)
    write_todo_file(active, blocked, done, path)

    if reblocked:
        return {
            "action": "undo",
            "message": (
                f'Moved "{item.text}" back to Active and re-blocked '
                f"{len(reblocked)} task{pluralize(reblocked)}."
            ),
        }
    return {"action": "undo", "message": f'Moved "{item.text}" back to Active.'}


def unblock_blocked_item(
    index: int,
    active: list[TaskItem],
    blocked: list[BlockedItem],
    done: list[TaskItem],
    path: Path,
) -> dict[str, object]:
    item = blocked.pop(index)
    active.append(TaskItem(text=item.text))
    write_todo_file(active, blocked, done, path)
    return {
        "action": "unblock",
        "message": f'Unblocked "{item.text}" from "{item.blocker}".',
    }


def release_tasks_for_blocker(
    blocked: list[BlockedItem],
    blocker_title: str,
) -> tuple[list[BlockedItem], list[TaskItem]]:
    restored: list[TaskItem] = []
    remaining: list[BlockedItem] = []
    blocker_key = normalize_for_match(blocker_title)

    for item in blocked:
        if normalize_for_match(item.blocker) == blocker_key:
            restored.append(TaskItem(text=item.text, released_by=item.blocker))
        else:
            remaining.append(item)

    return remaining, restored


def reblock_tasks_for_blocker(
    active: list[TaskItem],
    blocker_title: str,
) -> tuple[list[TaskItem], list[BlockedItem]]:
    remaining: list[TaskItem] = []
    reblocked: list[BlockedItem] = []
    blocker_key = normalize_for_match(blocker_title)

    for item in active:
        if item.released_by is not None and normalize_for_match(item.released_by) == blocker_key:
            reblocked.append(BlockedItem(text=item.text, blocker=item.released_by))
        else:
            remaining.append(item)

    return remaining, reblocked


def parse_task_item(text: str) -> TaskItem:
    raw = text.strip()
    if raw.endswith(RELEASED_SUFFIX) and RELEASED_PREFIX in raw:
        task_text, released_by = raw.rsplit(RELEASED_PREFIX, 1)
        task_text = task_text.strip()
        released_by = released_by[: -len(RELEASED_SUFFIX)].strip()
        if not task_text or not released_by:
            raise TodoError("Released task metadata must include both task text and blocker.")
        return TaskItem(text=task_text, released_by=released_by)
    return TaskItem(text=raw)


def format_task_item(item: TaskItem) -> str:
    if item.released_by is None:
        return item.text
    return f"{item.text}{RELEASED_PREFIX}{item.released_by}{RELEASED_SUFFIX}"


def parse_blocked_item(text: str) -> BlockedItem:
    if BLOCKED_DELIMITER not in text:
        raise TodoError(
            f'Blocked items must use the "{BLOCKED_DELIMITER.strip()}" format.'
        )

    task, blocker = text.rsplit(BLOCKED_DELIMITER, 1)
    task = task.strip()
    blocker = blocker.strip()
    if not task or not blocker:
        raise TodoError("Blocked items must include both a task and a blocker.")
    return BlockedItem(text=task, blocker=blocker)


def format_blocked_item(item: BlockedItem) -> str:
    return f"{item.text}{BLOCKED_DELIMITER}{item.blocker}"


def find_matching_indices(
    items: list[object],
    query: str,
    *,
    allow_empty: bool = False,
    exclude_normalized: set[str] | None = None,
    text_getter=None,
) -> list[int]:
    if text_getter is None:
        text_getter = item_text
    normalized_query = normalize_query(query)
    if not normalized_query:
        raise TodoError("Target text is required.")

    exclude_normalized = exclude_normalized or set()
    matcher = target_matcher(normalized_query)
    if matcher is not None:
        matches = [
            i
            for i, item in enumerate(items)
            if normalize_for_match(text_getter(item)) not in exclude_normalized
            and matcher(text_getter(item))
        ]
        if matches or allow_empty:
            return matches
        raise TodoError(f'No matching item found for "{query.strip()}".')

    exact = [
        i
        for i, item in enumerate(items)
        if normalize_for_match(text_getter(item)) not in exclude_normalized
        and normalize_for_match(text_getter(item)) == normalized_query
    ]
    if exact:
        return exact

    partial = [
        i
        for i, item in enumerate(items)
        if normalize_for_match(text_getter(item)) not in exclude_normalized
        and normalized_query in normalize_for_match(text_getter(item))
    ]
    if len(partial) == 1:
        return partial
    if not partial and allow_empty:
        return []
    if not partial:
        raise TodoError(f'No matching item found for "{query.strip()}".')
    raise TodoError(f'Ambiguous match for "{query.strip()}".')


def target_matcher(normalized_query: str):
    if normalized_query in APPLICATION_TARGETS:
        return lambda text: normalized_startswith(text, APPLICATION_PREFIXES)
    if normalized_query in FOLLOW_UP_TARGETS:
        return lambda text: normalized_startswith(text, FOLLOW_UP_PREFIXES)
    if normalized_query in REFERRAL_TARGETS:
        return lambda text: "referral" in normalize_for_match(text)
    return None


def find_index(
    items: list[object],
    query: str,
    *,
    text_getter=None,
) -> int:
    if text_getter is None:
        text_getter = item_text
    lowered = normalize_query(query)
    exact = [
        i
        for i, item in enumerate(items)
        if normalize_for_match(text_getter(item)) == lowered
    ]
    if exact:
        return exact[0]

    partial = [
        i
        for i, item in enumerate(items)
        if lowered in normalize_for_match(text_getter(item))
    ]
    if len(partial) == 1:
        return partial[0]
    if not partial:
        raise TodoError(f'No matching item found for "{query.strip()}".')
    raise TodoError(f'Ambiguous match for "{query.strip()}".')


def find_matching_blocker_title(
    blocked: list[BlockedItem],
    query: str,
) -> str | None:
    blocker_titles = unique_preserving_order(item.blocker for item in blocked)
    if not blocker_titles:
        return None

    try:
        index = find_index(blocker_titles, query)
    except TodoError:
        return None
    return blocker_titles[index]


def find_item_by_title(
    items: list[object],
    query: str,
    *,
    text_getter=None,
) -> object | None:
    if text_getter is None:
        text_getter = item_text
    normalized_query = normalize_for_match(query)
    for item in items:
        if normalize_for_match(text_getter(item)) == normalized_query:
            return item
    return None


def blocker_is_done(done: list[TaskItem], blocker_title: str) -> bool:
    return find_item_by_title(done, blocker_title) is not None


def item_text(item: object) -> str:
    if isinstance(item, (TaskItem, BlockedItem)):
        return item.text
    return str(item)


def canonicalize_blocker_title(text: str) -> str:
    result = compact_whitespace(text)
    if not result:
        return result

    changed = True
    while changed:
        changed = False
        lowered = result.casefold()
        for prefix in LEADING_BLOCKER_PHRASES:
            if lowered.startswith(prefix):
                result = result[len(prefix) :].lstrip()
                changed = True
                break

    return result


def normalize_query(text: str) -> str:
    return normalize_for_match(text.strip().strip("\"'").rstrip(".!?"))


def normalize_for_match(text: str) -> str:
    return compact_whitespace(text).casefold()


def compact_whitespace(text: str) -> str:
    return " ".join(text.strip().split())


def normalized_startswith(text: str, prefixes: tuple[str, ...]) -> bool:
    lowered = normalize_for_match(text)
    return any(lowered.startswith(prefix) for prefix in prefixes)


def pluralize(items: list[object]) -> str:
    return "" if len(items) == 1 else "s"


def unique_preserving_order(items) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        normalized = normalize_for_match(item)
        if normalized in seen:
            continue
        seen.add(normalized)
        unique.append(item)
    return unique
