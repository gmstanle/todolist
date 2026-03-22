import argparse

from todo_lib import BlockedItem, TaskItem, TodoError, apply_text_command, move_by_query, parse_todo_file


def cmd_list(active: list[TaskItem], blocked: list[BlockedItem], done: list[TaskItem]) -> None:
    print("Active:")
    if active:
        for item in active:
            print(f"  [ ] {item.text}")
    else:
        print("  (none)")

    print("\nBlocked:")
    if blocked:
        for item in blocked:
            print(f"  [ ] {item.text} | blocked-by: {item.blocker}")
    else:
        print("  (none)")

    print("\nDone:")
    if done:
        for item in done:
            print(f"  [x] {item.text}")
    else:
        print("  (none)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage the shared TODO.md file.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser(
        "add",
        help="Add a task or execute a natural-language dependency command",
    )
    add_parser.add_argument("text")

    done_parser = subparsers.add_parser("done", help="Move an item from active to done")
    done_parser.add_argument("query")

    undo_parser = subparsers.add_parser("undo", help="Move an item from done back to active")
    undo_parser.add_argument("query")

    unblock_parser = subparsers.add_parser(
        "unblock",
        help="Move a blocked item back to active",
    )
    unblock_parser.add_argument("query")

    subparsers.add_parser("list", help="Show active, blocked, and done items")

    args = parser.parse_args()

    try:
        if args.command == "add":
            result = apply_text_command(args.text)
            print(result["message"])
            return
        if args.command == "done":
            result = move_by_query(args.query, "active")
            print(result["message"])
            return
        if args.command == "undo":
            result = move_by_query(args.query, "done")
            print(result["message"])
            return
        if args.command == "unblock":
            result = move_by_query(args.query, "blocked")
            print(result["message"])
            return
        if args.command == "list":
            active, blocked, done = parse_todo_file()
            cmd_list(active, blocked, done)
            return
    except TodoError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
