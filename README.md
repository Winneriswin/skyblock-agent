# skyblock-agent

Portable Hypixel SkyBlock info collector and assistant.

## One-click start (Windows)

Double-click `start.bat` or run:

```powershell
.\start.ps1
```

This creates a venv, installs dependencies, opens the GUI in your browser, and starts the server.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e ".[gui]"

copy .env.example .env
# Edit .env and set HYPIXEL_API_KEY (use /api new in-game)

skyblock-agent lookup <username>
skyblock-agent lookup <username> --profile Apple
skyblock-agent players
skyblock-agent gui
```

## Lookup & auto-import

`lookup` resolves a Minecraft username, fetches Hypixel API data, and saves it under `data/`:

| File | Location |
|------|----------|
| Player payload | `data/raw/hypixel_api/player/{uuid}.json` |
| All profiles | `data/raw/hypixel_api/profiles/{uuid}.json` |
| Selected profile | `data/raw/hypixel_api/selected_profile/{profile_id}.json` |
| Player index | `data/processed/players/index.json` |

## API key

Run `/api new` on Hypixel and put the key in `.env` as `HYPIXEL_API_KEY`.

## GUI

Install GUI dependencies and launch the local web UI:

```bash
pip install -e ".[gui]"
skyblock-agent gui
# open http://127.0.0.1:8765
```

## API recognition test

Validate which Hypixel API fields are present and parsed:

```bash
skyblock-agent test-api <username>
skyblock-agent test-api <username> --json
```

## License

[LGPL-3.0-or-later](LICENSE) — aligned with SkyBlock community projects such as [Skyblocker](https://github.com/SkyblockerMod/Skyblocker) and [NotEnoughUpdates](https://github.com/NotEnoughUpdates/NotEnoughUpdates).
