# skyblock_agent

Hypixel SkyBlock 信息收集与助手（可迁移）。

## 快速开始

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .

copy .env.example .env
# 编辑 .env，填入 HYPIXEL_API_KEY（游戏内 /api new）

skyblock-agent profile <玩家名>
skyblock-agent profile <玩家名> --profile Apple
```

## API Key

在 Hypixel 服务器执行 `/api new` 获取 Key，写入 `.env` 的 `HYPIXEL_API_KEY`。

## License

[LGPL-3.0-or-later](LICENSE) — 与 [Skyblocker](https://github.com/SkyblockerMod/Skyblocker)、[NotEnoughUpdates](https://github.com/NotEnoughUpdates/NotEnoughUpdates) 等 SkyBlock 社区项目一致。

