# EntryBox roadmap

Where EntryBox is going. The order can shift, the promises can't:
**local-first, no SaaS, no account, no database.** Entries stay in
`.entrybox/entries.md` inside each project, as plain markdown your AI agent
can read.

Have an opinion on any of this? Open an issue, or log it as an `idea` entry
in your own EntryBox and send it as an issue later. That loop is the product.

---

## Now (next release)

- **File-tree browser.** The backend already serves a sandboxed project tree
  and file previews. The UI for it comes next: browse the project, attach a
  file reference to an entry.
- **Search and filter.** Filter entries by text, type, and state within a
  project. The flat list stops scaling around fifty entries; this fixes that.

## Next

- **Chrome extension.** Quick-add from any tab: popup, context menu, and
  screenshot straight to an attachment.
- **Per-project custom types.** Your project, your vocabulary. `fix` and
  `idea` fit me; maybe they don't fit you.
- **Resurfacing.** Old `logged` entries get a stale badge and a gentle
  nudge instead of sinking forever.
- **Resolution links.** Mark an entry `done` with a commit, PR, or file
  reference attached, so "done" points at proof.
- **Richer webhooks.** Payload versioning, per-event filtering, retry with
  backoff (today it fires once and forgets).
- **`pipx install entrybox`.** Proper packaging so the clone-and-venv dance
  becomes one command.

## Later

- **Single binary and installers.** Bundle the server so it runs without a
  Python install: one executable, then `.msi` / `.dmg` / AppImage.
- **VS Code extension.** Log from the command palette, see state badges
  inline.
- **GitHub Issues sync.** Bidirectional and state-mapped, opt-in per
  project.
- **Remote capture.** Drop an entry from your phone (a Telegram bot, a
  webhook) and have it land in the right project. Gated on optional API
  token auth first: EntryBox stays local-only and unauthenticated by
  default, and nothing remote ships before that boundary is solid.
- **Single-HTML zero-dependency mode.** One `.html` file that reads and
  writes `entries.md` directly via the File System Access API. No server,
  no Python.
- **Community themes gallery.** Themes are already single-JSON drop-ins;
  a gallery makes them shareable.

## Shipped

The full history lives in [CHANGELOG.md](CHANGELOG.md). Short version:
v1.0 shipped the core (server, markdown storage, 5 types, 5 states,
multi-project, agent annotation, themes, onboarding, embed mode, REST, CLI,
webhooks). Since then: pagination, rich entry rendering, the Quick Drop
desktop window, attachments, priority/due/recurrence fields, syntax
highlighting, vendored offline assets, and the v1.5.2 hardening pass
(crash-safe writes, annotation marker safety, CI).
