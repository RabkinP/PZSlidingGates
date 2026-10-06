# SlidingGates project knowledge

## Work involving Project Zomboid models

For creation, modification, export, placement, animation, materials, normals, UV or visual diagnosis of PZ models, apply `$pz-models` before making changes. Read `skills/pz-models/SKILL.md` directly if it is not listed in the session's skill catalog. Follow its relevant references and verification guidance. This applies to model-related Lua/model-script integration too, but does not require loading the skill for unrelated gameplay changes.

The maintained engine evidence is `skills/pz-models/references/engine-render-audit.md`. Check the installed game fingerprint before trusting version-specific behavior. Use current installed classes and shaders; PZMining's old extracted classes are not automatically authoritative. Preserve new verified findings there with evidence and scope so future sessions can reuse them.

## Current gate invariants

- Source: `art/SG_ChainLink.blend`. Work through the existing Blender MCP instance when available. Inspect its active file/scene first.
- Width variants are generated from `art/build_chainlink.py`: default 2, parameter GATE_WIDTH for other integer widths. `art/build_width_variant.py` creates a separate scene in the same source blend and width-named GLBs. Currently 2 and 4 are registered in the mod. Future sizes need export, model registration and a Lua type entry, not a stretched model.
- The entire moving leaf fits local X 0..width: one cell equals one model unit in this asset. No 0.34-unit tail, overhead guide beam or moving upper carriage. Cell collision limits are a gameplay requirement, not an aesthetic allowance.
- Open/Close travel equals width along X at the same speed profile: duration = width × 1.5 seconds. At 24 fps, width 2 uses frames 1–73 (3 seconds), width 4 frames 1–145 (6 seconds). Permanent leaf Y offset is 0.10; there is no perpendicular animation. DoorBone weights are 1 for this rigid leaf. Increasing duration requires changing resting animationTime definitions too.
- The short post bracket has roller pairs at world X width−0.12 and width+0.12. At least one complete pair must engage the top rail throughout travel. The motor's offset gearbox/shaft passes beside the post; verify clearances after changes.
- The four-cell leaf has two handles on the same outward face, mounted directly to the outer vertical frame tubes at X 0.025 and width−0.025. No handle crossmembers remain. The two-cell leaf has its single handle on the catcher-end vertical tube at X 0.025. Do not add a handle on the inner face unless requested.
- Handles use a continuous rounded U-shaped sweep with two stand-offs and a narrow backplate (diameter 0.028, open hand gap 0.053). `art/update_handles.py` updates both existing leaves without rebuilding the other art and checks all animation frames. Evidence: `art/handle_checks.json`.
- Current rail Y is 0.10, roller centres Y 0.051/0.149 (0.002 side gap). Rack centre Y 0.045 and depth 0.010 clear the unchanged post. Pinion output ends at world Y 0.065, starts at 0.040, and radius 0.040 avoids tooth penetration. Handle fittings face outward so they pass the post. `art/update_clearance.py` is the guarded 0.18→0.10 migration and full-frame verifier; it refuses a second migration. Preserve `art/clearance_checks.json` as verification evidence.
- Keep the calibrated drive translation `(-0.5, 0, -0.6)` in the current model script unless current coordinate/runtime evidence requires recalibration. Do not reconstruct placement from obsolete README revisions or Blender screenshots alone.
- N-right is the integrated static assembly. Exported left/W leaves do not prove their static placement and collision assembly are supported; validate/mirror that integration separately when requested.
- Export only intended mesh/rig objects with exact Open/Close clip names. Use external opaque atlas and explicit door shader for the current static/animated assets. Preserve correct outward winding, smooth cylindrical sides and flat caps/housings.

Use `art/update_straight_slide.py` and `art/export_chainlink.py` after inspecting them; `build_chainlink.py` is a builder that can alter the active scene and should not be blindly rerun on a finished workbench. Relevant checks include two-cell bounds, both clips, continuous roller capture, motor/post intersections and native import. The PZ preview is approximate; only gameplay tests establish final appearance.

`art/README.md` records historical designs. Its tail, long-beam and earlier placement sections are superseded by the current invariants above. Update these rules when an authorized design change alters them.

## Construction preview resources

- Own construction carriers: `sg_gates_preview_01`; tiledef file number **6842**, tileset number **1**. Preserve identifiers and existing tile indices. Generator: `tools/build_gate_tiles.py`; mapping and limits: `art/tiles/README.md`.
- Pack and `.tiles` live in `mod/SlidingGates/42/media`; `spriteModels.txt` must live in `mod/SlidingGates/common/media` for the audited B42 `SpriteModelManager` loader.
- `ISBuildIsoEntity.cacheSprites` creates texture-only copies. Our hook must keep registered sprites to retain their `spriteModel`. Render all preview parts through native ghost calls; do not insert preview objects into world squares.
- Preview tiles have no physics/door/collision properties. Their entity registry is global: use unique sprites per entity footprint. Existing gameplay collision carriers are a separate concern; do not infer their properties from preview tiles.
- Verify binary resources with `tests/test_gate_tiles.py`, Lua preview behavior with `tests/test_gate_preview.py`, and actual installed parsers with `research/probe-gate-tiles.py`. Headless parsing does not establish final in-game appearance.
