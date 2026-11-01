---
name: asset-sources
description: Use before downloading or generating any third-party or paid asset for GRAFT (textures, HDRIs, sounds, models, animations, Meshy, ElevenLabs) — approved sources, license rules, and the CREDITS.md entry every file needs.
---

# Asset sources and licenses

## Free sources (no approval needed)

| Source | What | License | Host (must be in the network allowlist) |
|---|---|---|---|
| Poly Haven | Textures, HDRIs, models | CC0 | api.polyhaven.com, dl.polyhaven.org |
| ambientCG | PBR textures | CC0 | ambientcg.com |
| OpenGameArt | Sounds, misc | Varies — CC0 preferred; check each file | opengameart.org |
| Quaternius Universal Animation Library | Animations | CC0 | — |
| MPFB / MakeHuman | Rigged humans | Check the asset pack's license | extensions.blender.org, static.makehumancommunity.org |

Prefer CC0. Avoid licenses that need attribution in-game unless the owner agrees; never use NC (non-commercial) or ND licenses.

## Paid sources — ask the owner first

- **Meshy** (text/image to 3D, `api.meshy.ai`) and **ElevenLabs** (sound generation, `api.elevenlabs.io`) cost money. Before any call, tell the owner what you want to make and roughly how many calls. Their MCP servers are only added to `.mcp.json` after the API keys are set.

## Every third-party file

1. Put the original in `raw_assets/` (sources) or the processed result in `assets/`.
2. Add a row to `CREDITS.md`: what, path, source URL, author, license.
3. If the license file ships with the asset, keep it next to the asset.

## If a host is blocked

The session's network allowlist is set by the owner (CLAUDE.md §10.1). If a download is blocked, say which host, and either ask the owner to add it or do the download in a GitHub Actions workflow and commit the result.
