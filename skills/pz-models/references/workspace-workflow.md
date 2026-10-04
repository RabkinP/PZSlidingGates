# Local tools and source assets

The skill is maintained in `E:\git\SlidingGates\skills\pz-models`. The following paths are this workstation's configuration, not universal PZ conventions. In another checkout, resolve equivalent project paths first.

| Resource | Path / purpose |
| --- | --- |
| Installed game | `E:\SteamLibrary\steamapps\common\ProjectZomboid` |
| Research toolkit | `E:\git\PZMining`; CFR at `tools\cfr.jar` |
| Source Blender file | `E:\git\SlidingGates\art\SG_ChainLink.blend` |
| Build / update | `art\build_chainlink.py`, `art\update_straight_slide.py`; run inside Blender via MCP after inspecting source |
| Export | `art\export_chainlink.py`; four leaf variants and four static parts |
| Diagnostic render | `art\render_pz_preview.py`; separate preview scene, 1x/2x images |
| Model definitions | `mod\SlidingGates\42\media\scripts\SG_models.txt` |
| Runtime integration | Find current SG_Gate/SG_Proto Lua files under `mod`; inspect current code rather than infer from historical art notes |
| Native import probe | `research\probe-assimp.py`; inspect invocation below |

Run from the repository root in PowerShell:

```powershell
Get-FileHash 'E:\SteamLibrary\steamapps\common\ProjectZomboid\projectzomboid.jar' -Algorithm SHA256
Get-Content research\extract-render-code.ps1
Get-Content research\probe-assimp.py
```

For a changed engine or newly required class, extract current installed classes using:

```powershell
& .\research\extract-render-code.ps1 -GameRoot 'E:\SteamLibrary\steamapps\common\ProjectZomboid' -MiningRoot 'E:\git\PZMining'
```

This writes `research/render-audit/classes`, `source`, and `manifest.txt`. Generated decompiled code is ignored by Git. Extend the class list only for the relevant rendering path. It does not modify PZMining or the game.

The native probe script generates minimal JVM classes without requiring a JDK; it does not itself import a supplied asset. Generate the classes and then run the game's Java/JNI importer:

```powershell
python .\research\probe-assimp.py
& 'E:\SteamLibrary\steamapps\common\ProjectZomboid\jre64\bin\java.exe' --enable-native-access=ALL-UNNAMED '-Djava.library.path=E:\SteamLibrary\steamapps\common\ProjectZomboid' -cp 'research\render-audit\probe;E:\SteamLibrary\steamapps\common\ProjectZomboid\projectzomboid.jar' PZImportProbe 'E:\git\SlidingGates\art\exports\SG_Drive.glb'
```

Inspect the generator's current native library path before using it on another workstation. It imports with the engine's audited flags and reports the first mesh/vertex, so it is diagnostic rather than exhaustive. The preserved eight-asset results are `research/render-audit/native-import-probes.txt`.

The reusable engine audit lives in this skill's `references/engine-render-audit.md`. `research/render-audit.md` routes to it. `art/README.md` contains chronological revisions; the current project invariants in root `AGENTS.md` take precedence over superseded dimensions there.

The local game-mod junction `C:\Users\pavel\Zomboid\mods\SlidingGates` has pointed to `mod/SlidingGates`; verify its target before relying on deployment. Export into `art/exports` and update the corresponding mod assets, without copying reference/diagnostic scene objects. Inspect existing export/install steps rather than assume exporting alone updates the mod.
