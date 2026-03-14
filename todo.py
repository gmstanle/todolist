import argparse
from todo_lib import add_item, move_by_query, parse_todo_file


def cmd_list(active: list[str], done: list[str]) -> None:
    print("Active:")
    if active:
        for item in active:
            print(f"  [ ] {item}")
    else:
        print("  (none)")

    print("\nDone:")
    if done:
        for item in done:
            print(f"  [x] {item}")
    else:
        print("  (none)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage the shared TODO.md file.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a new active item")
    add_parser.add_argument("text")

    done_parser = subparsers.add_parser("done", help="Move an item from active to done")
    done_parser.add_argument("query")

    undo_parser = subparsers.add_parser("undo", help="Move an item from done back to active")
    undo_parser.add_argument("query")

    subparsers.add_parser("list", help="Show active and done items")

    args = parser.parse_args()
    active, done = parse_todo_file()

    if args.command == "add":
        add_item(args.text)
    elif args.command == "done":
        move_by_query(args.query, "active")
    elif args.command == "undo":
        move_by_query(args.query, "done")
    elif args.command == "list":
        cmd_list(active, done)
        return


if __name__ == "__main__":
    main()
