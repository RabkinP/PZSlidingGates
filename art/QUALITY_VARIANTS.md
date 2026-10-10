# Gate assembly quality variants

Created 2026-10-10 in the existing `SG_ChainLink.blend` via Blender MCP.
The existing high-quality workbenches and leaf mesh/UV data remain unchanged.

Eight additional workbenches provide Low and Medium quality for both widths
(2 and 4) and both directions (forward and X-mirrored reverse). Scene names
insert `_Low` or `_Medium` immediately before `_Workbench`. Quality is separate
from the Open/Close animation state.

- Medium: mildly uneven wire infill, bowed internal upright(s), rough splice plates.
- Low: visibly distorted wire infill, more bent internal upright(s), mixed metal
  swatches, diagonal scrap straps and crude reinforcement plates.
- High: original geometry and materials.

The top/bottom rails, outer uprights, rack, wheels, handles, posts, drive and
ground track reuse the calibrated high-quality geometry. Added fittings face
outward. No negative object scales are used. All leaf vertices have DoorBone
weight 1. Width, motion, duration and permanent Y clearance remain unchanged.

`build_quality_variants.py` adds scenes without rebuilding originals and refuses
existing target scenes. It saves an ignored `SG_ChainLink_before_quality.blend`
backup first. `export_quality_variants.py` exports eight canonical N-facing GLBs
into `exports/quality`, with exact Open/Close clip names, one skinned mesh,
normals, UV and weights. Future W registrations can rotate these canonical
assets through spriteModels, as in the current mod. Use the existing external
opaque `SG_ChainLink_Atlas.png` and door shader when registering them.

`SG_Quality_Comparison` is an art-only comparison scene for the two-cell leaf,
with Low, Medium, High from left to right on the outward face. Generated with
`preview_quality_variants.py`; image: `SG_Quality_Comparison.png`. It uses studio
lighting, not the game renderer. Its labels/lights/camera are not export assets.

## Verification and remaining integration

`quality_checks.json`: 1,744 sampled animation frames across eight variants,
zero moving-leaf/static-part BVH surface intersections, continuous roller
capture, width bounds and unchanged source mesh/UV fingerprints. Static parts
are unchanged; the previous motor/post clearance evidence still applies.
BVH surface checks do not establish solid containment or final game appearance.

`quality_native_import.txt`: all eight GLBs successfully imported using the
installed game's Java/Jassimp native importer, fingerprint
`E1A69EB743EDE60B213A0FE7F8B83D4FCAB773036D256CC4543A336F3B058A33`.
The probe reports counts and first-vertex attributes; it is not full visual QA.

Gameplay integration is now registered by `tools/register_quality_models.py`:
welding 4–5 selects Low, 6–7 Medium, 8+ High. The minimum build skill is 4.
Six native entity recipes use the wooden-wall OnAddToMenu filter pattern and
translated quality suffixes in parentheses. High-quality entity IDs remain
unchanged. With Show All enabled, all tiers are listed; placement rejects a tier
that does not match the character's current welding level before materials are
consumed. Health follows vanilla: build-skill level × 300 per carrier (minimum level 4).

Assembly quality is saved in registry `quality`, part `sgQuality` and server
snapshots. Saved gates without quality retain High; the player's later skill
changes do not replace built gate models. Construction-only footprints 48..95
are unique per entity, while all old indices remain unchanged. Static ghosts
reuse the existing calibrated carriers. The local mod junction points at the
repository's `mod/SlidingGates` directory.

Verification: `tests/test_gate_quality.py`, `test_gate_preview.py`,
`test_gate_tiles.py`, `test_model_variants.py`, `test_localization.py` and the
existing direction/orientation/multiplayer/width regressions pass. The installed
game's actual parsers confirm all six recipe skill thresholds/callbacks
(`research/probe-gate-quality.py`, report `research/render-audit/gate-quality-native.txt`)
and all 96 preview carrier bindings (`research/probe-gate-tiles.py`).
The initial `gameplay_registered: false` in `quality_checks.json` describes the
earlier Blender-only art check, before this registration step.

The broader `test_gate_drive.py` currently fails at its unrelated client-menu
fixture: it lacks a mock for `TimedActions/ISInventoryTransferAction`, required
by the existing drive menu changes. No drive code was changed for gate quality.
Actual recipe presentation and appearance at gameplay zoom still require a
restart and fresh in-game build; headless parser/mock checks are not visual QA.
