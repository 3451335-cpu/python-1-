from __future__ import annotations

import json

from .client import RPCClient


HELP = """Commands:
  help
  call <method> <json>
  state
  quit

Examples:
  call create_person {"record":{"key":1,"datetime":1,"platform":"web","user_agent":"Chrome"}}
  call get_person {"key":1}
  call get_all_persons {}
  call recent_message_data {}
"""


def main() -> None:
    client = RPCClient()
    print("Variant 30 REPL. Type 'help' for commands.")

    while True:
        try:
            line = input("v30> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if not line:
            continue
        if line in {"quit", "exit"}:
            return
        if line == "help":
            print(HELP)
            continue

        if line == "state":
            try:
                print("Person:", json.dumps(client.get_all_persons(), ensure_ascii=False))
                print("Message:", json.dumps(client.get_all_messages(), ensure_ascii=False))
                print("Feedback:", json.dumps(client.get_all_feedbacks(), ensure_ascii=False))
            except Exception as exc:
                print(f"ERROR: {exc}")
            continue

        if line.startswith("call "):
            parts = line.split(maxsplit=2)
            if len(parts) != 3:
                print("ERROR: use call <method> <json>")
                continue
            method_name, raw_json = parts[1], parts[2]
            try:
                payload = json.loads(raw_json)
                method = getattr(client, method_name)
                result = method(**payload)
                print(json.dumps(result, ensure_ascii=False))
            except Exception as exc:
                print(f"ERROR: {type(exc).__name__}: {exc}")
            continue

        print("Unknown command. Type 'help'.")


if __name__ == "__main__":
    main()
