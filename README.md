# skyblock-agent

Portable Hypixel SkyBlock info collector and assistant.

## One-click start (Windows)

Double-click `start.bat` or run:

```powershell
.\start.ps1
```

This creates a venv on first run, opens the GUI in your browser, and starts the server. Later runs skip dependency installation unless `pyproject.toml` changed.

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

## Player inventories (Profile GUI)

Lookup responses include parsed inventory containers when the player has **Inventory API** enabled in-game:

| Container | API field |
|-----------|-----------|
| Inventory (36) | `inventory.inv_contents` |
| Armor & Equipment (8) | `inventory.inv_armor` + `inventory.equipment_contents` |
| Accessory Bag (paginated; API: `talisman_bag`) | `inventory.bag_contents.talisman_bag` |
| Ender Chest (54–405, paginated) | `inventory.ender_chest_contents` |
| Backpack (9–45 slots each, paginated) | `inventory.backpack_contents` (numeric keys only) |
| Wardrobe (4 armor slots per set, paginated) | `inventory.wardrobe_contents` + `inventory.wardrobe_equipped_slot`; optional `backpack_contents` keys `wd*` |

Hypixel often returns `wardrobe_equipped_slot` without `wardrobe_contents` even when Inventory API is enabled. In that case this app shows **currently equipped armor** from `inv_armor` only (saved sets are not available via API).

Backpack storage keys starting with `wd` are wardrobe sets and are shown under **Wardrobe**, not Backpack.

Profile lookup also returns **Collections** from `member.collection`, grouped using Hypixel's official [`/v2/resources/skyblock/collections`](https://api.hypixel.net/v2/resources/skyblock/collections) resource (same categories as in-game: Farming, Mining, Combat, Foraging, Fishing, Rift). The catalog is cached locally on first use under `data/processed/collections/`.

Data is **Base64 + GZip + NBT**; decoded with [`nbtlib`](https://github.com/vberlier/nbtlib) (installed automatically via `pip install -e .`).

If containers show “API disabled”, the player must enable inventory sharing in SkyBlock settings.

## Item icon sync (local cache)

After importing the item catalog, download 32×32 icons into `data/processed/items/icons/`:

```powershell
.\sync-icons.ps1
# or: sync-icons.bat
# or: skyblock-agent items icons import
```

| File | Location |
|------|----------|
| PNG icons | `data/processed/items/icons/{ITEM_ID}.png` |
| Icon manifest | `data/processed/items/icons/manifest.json` |
| Sync metadata | `data/processed/items/icons/meta.json` |

Icons are fetched from [Coflnet](https://sky.coflnet.com/) (SkyBlock item renders), with vanilla Minecraft textures as fallback via [PrismarineJS/minecraft-assets](https://github.com/PrismarineJS/minecraft-assets). The GUI serves them at `/api/items/{id}/icon`.

```bash
skyblock-agent items icons status
skyblock-agent items icons import --limit 100   # test run
skyblock-agent items icons import --force       # re-download all
```

Icons are **not** downloaded on GUI startup. Run `sync-icons` after `sync-items` when setting up or after major game updates.

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
- Item icons in Resources (after `sync-icons`) + wiki-style minetip on hover

## Item tooltips (local cache)

Full in-game-style tooltips are synced manually from three sources (merged by priority):

| Priority | Source | Saved to |
|----------|--------|----------|
| 1 | [NotEnoughUpdates-REPO](https://github.com/NotEnoughUpdates/NotEnoughUpdates-REPO) (`items/*.json` lore) | `data/raw/neu/items/` |
| 2 | [SkyBlock Wiki](https://hypixel-skyblock.fandom.com/wiki/Module:Inventory_slot/Tooltips) minetip module | `data/raw/wiki/inventory_slot_tooltips.lua` |
| 3 | Hypixel `v2/resources/skyblock/items` base stats | generated fallback |

```powershell
.\sync-tooltips.ps1
# or: sync-tooltips.bat
# or: skyblock-agent items tooltips import
skyblock-agent items tooltips status
skyblock-agent items tooltips import --sources neu,wiki
```

Output:

| File | Location |
|------|----------|
| Searchable tooltip cache | `data/processed/items/tooltips.json` |
| Import metadata | `data/processed/items/tooltips_meta.json` |

Re-run `sync-items.bat` first if you want Hypixel stat fallbacks to include the latest `stats` fields.

## Item tooltips (wiki-style rendering)

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
