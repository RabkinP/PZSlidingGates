# Six-cell source models

Created in the existing `SG_ChainLink.blend` through live Blender MCP. This is an
art-only stage: 48 GLBs exported to `art/exports/six`, without deployment or Lua,
recipe, spriteModel or preview tile changes. The installed game JAR matches the engine audit:
`E1A69EB743EDE60B213A0FE7F8B83D4FCAB773036D256CC4543A336F3B058A33`.

## Source and geometry

48 new workbenches: 2 materials × 3 qualities × 4 damage states × 2 travel directions.
Chain-link names replace `SG_ChainLink_4` with `SG_ChainLink_6`; wooden names replace
`SG_Wood_4` with `SG_Wood_6`. Each scene has `sg_six_cell=true` and a
`sg_source_scene` pointing to its four-cell source.

The saved active scene `SG_Six_Cell_Comparison` shows the intact high-quality
assemblies together: chain-link above, wood below. Its display copies share mesh
data but have no animation; use the production workbenches to inspect the clips.

`build_six_cell_variants.py` copies four-cell assemblies, their rigs and their
Open/Close action curves. Static mesh data is reused unchanged; the guide post and
motor move two units toward the new far end. Ground-track copies cover X 0..11,
reflected for reverse assemblies. Original workbenches are fingerprinted before
and after both build batches. Backup: ignored `SG_ChainLink_before_six.blend`.

Leaves are regenerated with the established geometry helpers, loaded via AST
without executing the old builders. Width changes lengths/counts, preserving
height, tube/wire/board thickness, wire pitch, atlas UVs and mechanical clearance.
Two width-specific helper conditions are extended only in this builder's private
namespace: two metal handles for width >=4, and wooden intermediate uprights every
two cells. No original two/four-cell builder is rerun or rewritten.

- Leaf bounds: canonical X 0..6; permanent Y offset .10.
- Wood: three braced two-cell bays, 90 mm uprights at X 2 and 4; clipped diagonal
  ends; lower board ends at Z .18, bottom timber Z .095..180.
- Two outward handles/knobs, on the two outer vertical frame members.
- Quality and damage retain the existing visual rules. Damage does not remove the
  outside frame, tracks or mechanical contacts. Wood Damage3 breaks all three
  diagonals; metal tears retain crossing infill and removed spans below .065.
- Reverse geometry is reflected in mesh coordinates, with corrected winding and
  UV loop order; object scales stay positive. Outward face remains unchanged.
- Both clips retain the four-cell curve shape, retimed by 1.5 in time and travel:
  6-unit stroke, 9-second clips, frames 1..217 at 24 fps. Rigid DoorBone weights 1.

## Verification

`verify_six_cell_variants.py` checks all 48 scenes, both clips, all **20,832 frames**:
continuous roller capture, zero moving/static surface intersections, no motor/post
surface intersections, correct endpoints and monotonic travel. It also checks
evaluated rigid skinning, weights, UV range, positive scale, positive signed volume
of every connected shell, face area, mesh bounds and complete ground tracks.
Results: `six_motion_checks.json`; build/source fingerprints:
`six_chainlink_build_checks.json`, `six_wood_build_checks.json`.

`tests/test_six_cell_exports.py` verifies the exact 48-file variant set, SHA256,
single meshes/primitives/skins, unit normals, UV range, rigid weights, DoorBone,
canonical bounds, exact Open/Close names, 9-second intervals and 6-unit strokes.
Results: `six_glb_checks.json` and `six_export_manifest.json`.

`research/probe-six-import.py` successfully imports all 48 files using the installed
PZ JNI/Assimp importer. Results: `six_native_import.txt`. This checks native import
and first-vertex diagnostics; final gameplay appearance remains untested.

## Export and later integration

Run `export_six_cell_variants.py` in the live source Blender. It exports the two
intact high-quality chain-link leaves directly, then calls the existing specialized
wood/quality/damage exporters with `EXPORT_WIDTHS=(6,)` and a separate `EXPORT_ROOT`.
Names use `_6`, never the old width-4 fallback. The specialized exporters default
to widths 2/4, preserving their original behavior. All 119 older GLBs were checked
by SHA256 before/after export and remained unchanged.

Output layout mirrors the old exporters: `exports/six/*.glb` (2 high chain-link),
`exports/six/quality` (4), `exports/six/damage` (18), `exports/six/wood` (24).
Static posts, drive and one-cell rails reuse existing material-specific 2/4 assets;
W orientation reuses the N assets by spriteModel rotation at integration time.
The old wooden updater also assumes 2/4; do not run it on six-cell scenes until its
scene lookup is generalized. The guarded six-cell builder refuses existing targets.

## Integration

`tools/register_six_models.py` deploys the 48 GLBs and writes `SG_models_six.txt`
(48 models, 48 animation meshes, 192 carrier poses) and `entity_sliding_gates_six.txt`
(six recipes) by cloning the registered four-cell blocks, so all anchors stay
calibrated: names `_4`→`_6`, resting open pose 6→9 seconds. Lua types `chainlink6`/
`wood6` use 9-second clips. Preview footprints 184..327 come from
`tools/build_gate_tiles.py`; `research/probe-gate-tiles.py` parses all 328 with the
installed game. Native import of all GLBs: `six_native_import.txt`. Recipe icons
reuse the four-cell icons. No in-game visual test has been performed yet.

Six-cell recipe balance, all three quality tiers: 60 XP for both materials;
8 screws for wood and 4 screws/nuts-bolts for chain-link, matching widths 2/4;
2 rubber hoses (or the existing chain-link alternatives) for both materials.
Wood's shared material/salvage budget matches its recipe. Chain-link retains the
existing metal-only salvage budget, with 4 screws like the smaller widths.
