# skyblock-agent

Portable Hypixel SkyBlock info collector and assistant.

## One-click start (Windows)

Double-click `start.bat` or run:

```powershell
.\start.ps1
```

This creates a venv, installs dependencies, opens the GUI in your browser, and starts the server.

**Note:** The GUI does not download the item catalog on startup. Run `sync-items.bat` once (or after game updates) to import item types locally.

## Item catalog sync (static resources)

Hypixel item definitions (~5500 items) are static and cached. Sync them manually:

```powershell
.\sync-items.ps1
# or: sync-items.bat
# or: skyblock-agent items import
```

Saved under:

| File | Location |
|------|----------|
| Raw API payload | `data/raw/hypixel_api/resources/items.json` |
| Searchable catalog | `data/processed/items/catalog.json` |
| Catalog metadata | `data/processed/items/meta.json` |

```bash
skyblock-agent items status
skyblock-agent items search diamond
skyblock-agent items search --category SWORD
```

No API key is required for the items resource endpoint.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e ".[gui]"

copy .env.example .env
# Edit .env and set HYPIXEL_API_KEY from https://developer.hypixel.net/dashboard/

skyblock-agent lookup <username>
skyblock-agent lookup <username> --profile Apple
skyblock-agent bazaar --search ENCHANTED_DIAMOND
skyblock-agent auctions --search "Aspect of" --bin
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

## Bazaar & Auction House

Fetch live market data from the [Hypixel Public API](https://api.hypixel.net/):

| Command | Endpoint | Saved to |
|---------|----------|----------|
| `bazaar` | `v2/skyblock/bazaar` | `data/raw/hypixel_api/bazaar/snapshot.json` |
| `auctions --page N` | `v2/skyblock/auctions` | `data/raw/hypixel_api/auctions/page_{N}.json` |

```bash
skyblock-agent bazaar
skyblock-agent bazaar --search ENCHANTED_DIAMOND --json
skyblock-agent auctions --page 0 --search "Hyperion" --bin
```

The GUI **Market** tab is a grid browser for Bazaar and Auction House:

- **Bazaar** — all products, paginated (48/page), search, category, sort
- **Auction House** — paginated API pages, category filter, BIN-only, sort
- Placeholder inventory icons + wiki-style minetip on hover

## Item tooltips (wiki-style)

Market rows use the same tooltip system as the [Hypixel SkyBlock Wiki](https://hypixel-skyblock.fandom.com/wiki/Hypixel_SkyBlock_Wiki:Style_Manual/UIs):

- `minetip.css` / `minetip.js` — port of `MediaWiki:Common.js/minetip.js`
- `data-minetip-title` + `data-minetip-text` with Minecraft `&` color codes
- `/` separates description lines (like in-game / wiki tooltips)

Hover Bazaar or Auction rows in the GUI to preview.

## API key

Create an Application key at [developer.hypixel.net](https://developer.hypixel.net/dashboard/) and set `HYPIXEL_API_KEY` in `.env`.

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
