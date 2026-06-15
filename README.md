# skyblock-agent

Portable Hypixel SkyBlock info collector and assistant.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e .

copy .env.example .env
# Edit .env and set HYPIXEL_API_KEY (use /api new in-game)

skyblock-agent profile <username>
skyblock-agent profile <username> --profile Apple
skyblock-agent profile <username> --json
```

## API key

Run `/api new` on Hypixel and put the key in `.env` as `HYPIXEL_API_KEY`.

## License

[LGPL-3.0-or-later](LICENSE) — aligned with SkyBlock community projects such as [Skyblocker](https://github.com/SkyblockerMod/Skyblocker) and [NotEnoughUpdates](https://github.com/NotEnoughUpdates/NotEnoughUpdates).
