#!/usr/bin/env python3
"""EntryBox CLI. Interact with a running EntryBox instance."""

import argparse
import json
import sys
import urllib.request
import urllib.error


def _req(method: str, url: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            err = json.loads(body)
            print(f"Error: {err.get('error', body)}", file=sys.stderr)
        except Exception:
            print(f"HTTP {e.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Cannot reach EntryBox at {url}: {e.reason}", file=sys.stderr)
        print("Is the server running? Try: python -m uvicorn app.main:app --port 3859", file=sys.stderr)
        sys.exit(1)


def cmd_list(args):
    url = f"{args.host}/api/projects/{args.project}/entries"
    data = _req("GET", url)
    entries = data.get("entries", [])
    if not entries:
        print("No entries.")
        return
    for e in entries:
        done_at = f" (done {e['done_at']})" if e.get("done_at") else ""
        print(f"  [{e['state']:8}] {e['id']}  {e['type']:8}  {e['title']}{done_at}")


def cmd_add(args):
    url = f"{args.host}/api/projects/{args.project}/entries"
    data = _req("POST", url, {"title": args.title, "body": args.body or "", "type": args.type})
    print(f"Created: {data.get('id')}  [{data.get('state')}]  {data.get('title')}")


def cmd_update_state(args):
    url = f"{args.host}/api/projects/{args.project}/entries"
    _req("PATCH", url, {"id": args.id, "state": args.state})
    print(f"Updated {args.id} → {args.state}")


def cmd_edit(args):
    url = f"{args.host}/api/projects/{args.project}/entries"
    payload = {"id": args.id}
    if args.title is not None:
        payload["title"] = args.title
    if args.body is not None:
        payload["body"] = args.body
    if args.type is not None:
        payload["type"] = args.type
    if len(payload) == 1:
        print("Nothing to edit. Pass at least one of --title, --body, --type.", file=sys.stderr)
        sys.exit(1)
    data = _req("PATCH", url, payload)
    e = data.get("entry", {})
    print(f"Edited {e.get('id')}  [{e.get('state')}]  {e.get('type')}  {e.get('title')}")


def cmd_projects(args):
    url = f"{args.host}/api/projects"
    data = _req("GET", url)
    projects = data.get("projects", [])
    if not projects:
        print("No projects registered.")
        return
    for p in projects:
        status = "⚠" if p.get("status") == "unreachable" else "●"
        print(f"  {status} {p['id']:20} {p['name']:30} prefix={p['prefix']}")


def cmd_add_project(args):
    url = f"{args.host}/api/projects"
    payload = {
        "name": args.name,
        "root_dir": args.root_dir,
        "prefix": args.prefix.upper(),
        "id": args.id or args.prefix.lower(),
        "color": args.color,
        "agent_ids": args.agents.split(",") if args.agents else [],
        "auto_write": not args.skip_agent_config,
    }
    if args.migrate_from:
        payload["migrate_from"] = args.migrate_from

    # Show annotation preview and confirm
    if not args.yes and payload["agent_ids"]:
        print("\nEntryBox will write to these agent config files:")
        for aid in payload["agent_ids"]:
            agents = _req("GET", f"{args.host}/api/agents").get("agents", [])
            agent = next((a for a in agents if a["id"] == aid), None)
            if agent:
                print(f"  → {agent['config_file']}  ({agent['name']})")
        confirm = input("\nProceed? [y/N] ").strip().lower()
        if confirm != "y":
            print("Cancelled.")
            sys.exit(0)

    data = _req("POST", url, payload)
    if data.get("ok"):
        p = data["project"]
        print(f"Registered {p['id']}: {p['name']} (prefix: {p['prefix']})")


def cmd_themes(args):
    url = f"{args.host}/api/themes"
    data = _req("GET", url)
    active = data.get("active", "")
    for t in data.get("themes", []):
        marker = "●" if t["id"] == active else " "
        print(f"  {marker} {t['id']:16} {t['name']}")


def cmd_set_theme(args):
    url = f"{args.host}/api/themes/active"
    _req("POST", url, {"id": args.theme})
    print(f"Theme set to: {args.theme}")


def main():
    parser = argparse.ArgumentParser(prog="entrybox", description="EntryBox CLI")
    parser.add_argument("--host", default="http://localhost:3859", help="EntryBox server URL")
    parser.add_argument("--project", "-p", default=None, help="Project ID")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # list
    p_list = sub.add_parser("list", help="List entries for a project")
    p_list.set_defaults(fn=cmd_list)

    # add
    p_add = sub.add_parser("add", help="Log a new entry")
    p_add.add_argument("title", help="Entry title")
    p_add.add_argument("--body", default="", help="Entry body/description")
    p_add.add_argument("--type", default="idea", choices=["fix","improve","docs","idea","roadmap"])
    p_add.set_defaults(fn=cmd_add)

    # update-state
    p_us = sub.add_parser("update-state", help="Update an entry's state")
    p_us.add_argument("--id", required=True, help="Entry ID, e.g. ENTRY-0001")
    p_us.add_argument("--state", required=True, choices=["logged","review","wip","done","error"])
    p_us.set_defaults(fn=cmd_update_state)

    # edit
    p_ed = sub.add_parser("edit", help="Edit an entry's title, body, and/or type")
    p_ed.add_argument("--id", required=True, help="Entry ID, e.g. ENTRY-0001")
    p_ed.add_argument("--title", default=None, help="New title")
    p_ed.add_argument("--body", default=None, help="New body/description")
    p_ed.add_argument("--type", default=None, choices=["fix","improve","docs","idea","roadmap"])
    p_ed.set_defaults(fn=cmd_edit)

    # projects
    p_projs = sub.add_parser("projects", help="List registered projects")
    p_projs.set_defaults(fn=cmd_projects)

    # add-project
    p_ap = sub.add_parser("add-project", help="Register a project with EntryBox")
    p_ap.add_argument("--name", required=True)
    p_ap.add_argument("--root-dir", required=True, dest="root_dir")
    p_ap.add_argument("--prefix", default="ENTRY")
    p_ap.add_argument("--id", default=None)
    p_ap.add_argument("--color", default="#3b9eff")
    p_ap.add_argument("--agents", default=None, help="Comma-separated agent IDs, e.g. claude-code,cursor")
    p_ap.add_argument("--migrate-from", default=None, dest="migrate_from", help="Path to existing entries.md to import")
    p_ap.add_argument("--skip-agent-config", action="store_true", dest="skip_agent_config")
    p_ap.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    p_ap.set_defaults(fn=cmd_add_project)

    # themes
    p_themes = sub.add_parser("themes", help="List available themes")
    p_themes.set_defaults(fn=cmd_themes)

    # set-theme
    p_st = sub.add_parser("set-theme", help="Set active theme")
    p_st.add_argument("theme", help="Theme ID, e.g. ocean")
    p_st.set_defaults(fn=cmd_set_theme)

    args = parser.parse_args()

    if hasattr(args, "fn"):
        if args.cmd in ("list", "add", "update-state", "edit") and not args.project:
            print("Error: --project/-p required for this command", file=sys.stderr)
            sys.exit(1)
        args.fn(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
