# Asset shot list

Images the README, landing page, and press kit reference. Capture these before
the public release. The repo ships with `logo.svg` (the wordmark) already;
everything below needs a capture or design pass.

## How to get a populated UI

1. Start EntryBox: `python -m uvicorn app.main:app --port 3859`
2. Register a project pointed at any folder; copy `demo/entries.sample.md` into
   that folder's `.entrybox/entries.md` so the list is full and varied.
3. Reload. You now have six entries spanning every type and state.

## Screenshots

Save each as PNG in this folder with the exact filename given.

| Filename | Size (px) | Contents |
|----------|-----------|----------|
| `screenshot-main.png` | 1600×1000 | Main UI, **dark** theme, sidebar with 2–3 projects, demo entries visible. Primary README hero shot. |
| `screenshot-light.png` | 1600×1000 | Same view, **default (light)** theme. |
| `screenshot-onboarding.png` | 1600×1000 | An onboarding slide: slide 6 (AI tool selector) or slide 7 (editable agent block). |
| `screenshot-register.png` | 1600×1000 | The Register Project modal open, agent config preview visible. |
| `screenshot-themes.png` | 1600×1000 | 2×2 grid composite of the four built-in themes (default, dark, minimal, ocean). |
| `screenshot-embed.png` | 1200×800 | Embed mode (`?embed=1&project=…`): single project, no chrome. |

## Brand / marketing images

| Filename | Size (px) | Notes |
|----------|-----------|-------|
| `social-preview.png` | 1280×640 | GitHub social preview / OG image. Logo + tagline "The idea board that lives in your repo." on the dark background `#0f1117`. Set under repo Settings → Social preview. |
| `favicon.png` | 512×512 | Square mark only (the diamond from `logo.svg`), centered. Export down to 32×32 as needed. **Interim version shipped 2026-07-10** (generated tray-and-arrow glyph in brand colors, plus `entrybox.ico` for the Windows shortcut); replace both when the real diamond mark is derived. |
| `logo-mark.svg` | n/a | Optional: the diamond mark alone, no wordmark, for square contexts. Derive from `logo.svg`. |

## Optional

| Filename | Notes |
|----------|-------|
| `demo.gif` | Short loop: log an entry → move it through states → switch theme. Keep under ~5 MB for README embedding. |

## Conventions

- Dark background for brand images: `#0f1117`.
- Accent: `#3b9eff`. Type/state colors per `../../BRAND.md`.
- No OS chrome in screenshots. Crop to the EntryBox viewport.
- Keep `logo.svg` the single source of truth for the wordmark; do not redraw it.
