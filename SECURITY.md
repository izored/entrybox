# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes       |
| < 1.0   | No        |

## Threat model

EntryBox is a **single-user, local-first tool**. It has **no authentication**
and no user accounts by design.

- It binds to `127.0.0.1` by default, reachable only from the local machine.
- Entry content, project paths, and the registry stay on disk in plain files.
  Nothing is sent to any external service. There is no telemetry.
- Anyone who can reach the server port can read and modify every entry in every
  registered project, and can trigger writes to agent config files.

### Running it safely

- Keep `ENTRYBOX_BIND` at `127.0.0.1`. Do **not** set it to `0.0.0.0`.
- Do **not** expose port 3859 to a LAN or the internet. If you must, place a
  reverse proxy with authentication (and HTTPS) in front of it.
- Treat `data/entrybox.json` and every `.entrybox/entries.md` as ordinary
  project files when deciding what to commit or share.

## Reporting a vulnerability

Please report security issues **privately**. Do not open a public issue.

Email **dev@izo.red** with:

1. A description of the issue and its impact.
2. Steps to reproduce.
3. The EntryBox version and your environment.

You will get an acknowledgement within a few days. Once a fix is available it
will be released and credited (unless you prefer to stay anonymous).
