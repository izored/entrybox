# DEMO — EntryBox

Entry tracking for Demo Project. Managed by EntryBox.

Sample data for screenshots and demos. Copy this to a project's
`.entrybox/entries.md` (or register a project pointed at a folder containing
it) to get a populated UI without touching real data.

## DEMO-0001 · 2026-05-20 09:14 · fix · logged — Dark theme flickers white on first paint

The page flashes the light background for a frame before the dark theme vars
are injected. Inject the theme synchronously in the document head.

## DEMO-0002 · 2026-05-20 10:02 · improve · review — Keyboard shortcut to log an entry

Pressing "n" anywhere should focus the new-entry title field. Small thing,
saves a mouse trip every time.

## DEMO-0003 · 2026-05-20 11:30 · idea · wip — Quick filter by type and state

A row of toggle chips above the entry list to filter the visible entries.
No search box yet — just the chips.

## DEMO-0004 · 2026-05-19 16:45 · docs · done · 2026-05-20 12:10 — Write the REST API section of the README

Documented every /api endpoint with a curl example for entries. Done.

## DEMO-0005 · 2026-05-20 13:05 · roadmap · logged — Single-file HTML mode

A zero-dependency build that runs from one .html file with localStorage as the
backend. No server. Good for quick personal use and offline.

## DEMO-0006 · 2026-05-20 14:22 · fix · error — Webhook retries hammer a dead endpoint

When the webhook URL is unreachable EntryBox retries with no backoff. Needs a
decision: drop after N tries, or queue. Blocked pending that call.
