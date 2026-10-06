"""Interactive REPL for the variant 30 RPC client."""

import json

from .client import RPCClient

HELP = """Commands:
  help
  call <method> <json>
  state
  quit

Example:
  call create_person {"record": {
    "key": 1, "datetime": 1, "platform": "web",
    "user_agent": "Chrome"
  }}
"""


def _print_state(client: RPCClient) -> None:
    """Print all three entity tables."""
    print(json.dumps(client.get_all_persons(), ensure_ascii=False))
    print(json.dumps(client.get_all_messages(), ensure_ascii=False))
    print(json.dumps(client.get_all_feedbacks(), ensure_ascii=False))


def _run_call(client: RPCClient, line: str) -> None:
    """Parse and execute one call command."""
    parts = line.split(maxsplit=2)
    if len(parts) != 3:
        print("ERROR: use call <method> <json>")
        return
    method_name, raw_json = parts[1], parts[2]
    try:
        payload = json.loads(raw_json)
        result = getattr(client, method_name)(**payload)
        print(json.dumps(result, ensure_ascii=False))
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")


def _run_command(client: RPCClient, line: str) -> bool:
    """Execute one REPL command and return whether to continue."""
    if line in {"quit", "exit"}:
        return False
    if line == "help":
        print(HELP)
        return True
    if line == "state":
        try:
            _print_state(client)
        except Exception as exc:
            print(f"ERROR: {exc}")
        return True
    if line.startswith("call "):
        _run_call(client, line)
        return True
    print("Unknown command. Type 'help'.")
    return True


def main() -> None:
    """Run the interactive client loop."""
    client = RPCClient()
    print("Variant 30 REPL. Type 'help' for commands.")
    while True:
        try:
            line = input("v30> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if line and not _run_command(client, line):
            return


if __name__ == "__main__":
    main()
