# Chain-link gate prototype

## Width variants (current)

The same `SG_ChainLink.blend` now contains the original two-cell workbench
and `SG_ChainLink_4_Workbench`. The four-cell leaf opens to one side by four
units; the two-cell gate takes 3 seconds and the four-cell gate 6 seconds.
Duration is width × 1.5 seconds, preserving the same travel speed profile.
Tubes, height, wire
pitch, fittings, drive and post geometry keep their original dimensions.

`build_chainlink.py` is parameterized by integer `GATE_WIDTH` (default 2).
Run `build_width_variant.py` via Blender MCP with `GATE_WIDTH=4` (or another
integer >=2) in the source project to create a new, separate variant scene.
It refuses to overwrite an existing variant scene. `export_chainlink.py`
uses the active scene's gate rig and exports width-named leaves; width 2
keeps legacy filenames. The two-cell updater remains specifically for the
original workbench. Keep the saved closed pose and the Open/Close tracks.
New exports use zero-based timelines at 24 fps: 0–3 seconds / frames 1–73
for two cells, 0–6 seconds / frames 1–145 for four cells.
Native import results
for width 4 are in `research/render-audit/width-4-native-import.txt`.

For a future size, export that width, add it to `tools/gen_models.py` WIDTHS
(default 2,4), and register a corresponding type in SG_Gate.lua. The Lua
assembly uses its type width for opening doors, guide/drive placement,
rails and pocket blockers. It is not arbitrary runtime mesh scaling.
Example registration regeneration: `python tools/gen_models.py 0.12 2,3,4,5,6`;
only register sizes whose GLBs have actually been exported.

N-right debug menu offers both 2 and 4 cells. A four-cell opening needs an
additional four-cell parking zone on the sliding side (eight-cell total
travel envelope). Restart PZ after model changes and build a fresh assembly.
Four-cell Blender geometry/animation and native import are checked; actual
four-cell PZ appearance, chunk clipping and collision need gameplay testing.
Lua logic tests: `python tests/test_gate_widths.py` with the optional `lupa`
dependency. These mocks verify assembly/sync decisions, not PZ physics.

The earlier prototype sections below are historical and superseded where
they disagree with these width rules or root AGENTS.md.

Engine behaviour and export requirements are documented in
`../research/render-audit.md`, verified against the installed game JAR and
native Jassimp importer. Consult that audit before changing normals, UV,
scale, materials or preview lighting; older prototype notes below describe
the chronological design revisions.

Created in Blender 5.2.2 through Blender MCP. Source: `SG_ChainLink.blend`.

## Assets

- `exports/SG_ChainLink_{N,W}_{Left,Right}.glb`: skinned moving leaf, `DoorBone`, independent `Open` and `Close` clips.
- `exports/SG_GuidePost.glb`: roller guide post; `exports/SG_CatcherPost.glb`: receiving post with upper/lower U catches. The old SG_Post.glb is obsolete.
- `exports/SG_Rail.glb`: static one-cell rail segment; repeat along the four-cell travel envelope.
- `exports/SG_Drive.glb`: separate static motor/battery housing.
- `SG_ChainLink_Atlas.png`: shared opaque 128×128 atlas. Chain-link holes use geometry.

The leaf includes a 0.34-unit tail beyond the two-cell opening. Prototype coordinates use X along the opening, Y outward, Z up. One cell is provisionally one Blender unit. N is the canonical X-aligned asset; W rotates its root by +90 degrees. Left/Right mean negative/positive local travel, pending mapping to the game's camera and tile conventions.

## Animation

24 fps, frames 1–49, duration 2 seconds. Open slides 2 units along X; Close reverses the same path. The leaf geometry has a permanent Y offset of 0.18 units, with no perpendicular animation. Only the leaf moves. Height is provisionally 1.9 units; post height about 2.04.

The saved workbench shows the closed pose. Select `SG_Rig` and scrub frames 1–49 for Open. Both clips are stored in muted NLA tracks; Open is the active preview action. `export_chainlink.py` exports both tracks and restores the preview setup.

## Validation and remaining work

Checked closed and open poses visually through MCP. Parsed all seven GLBs to check object lists, absence of startup-scene objects, and exact `Open`/`Close` clip names with `DoorBone` in all four leaf files.

These are prototype exports, not game-integrated assets. Validate scale/origin against PZ spriteModels, N/W handedness, animation interpolation in PZ, visibility outside the source cell, depth ordering, and texture loading before final art. Lower wheels rest on the straight rail; upper post-mounted rollers guide the leaf. A toothed rack on the leaf meets the drive pinion. This remains simplified game geometry; wheel/pinion rotation is not animated. The workbench shows the right-opening arrangement; mirror drive and rail placement for left-opening gates. No mod scripts or tile registrations have been changed.

`build_chainlink.py` builds the prototype in the active workbench scene and preserves its existing objects in a hidden reference collection. Run on a fresh workbench rather than repeatedly on the finished scene. `export_chainlink.py` runs inside the saved Blender file. Both are intended for Blender MCP execution.


Guide station: world X 2.14 and 2.20; top rail extends from X 0.04 to 2.30 at rest. Both stations remain within the top rail for the entire 2-unit stroke (verified at every frame of Open and Close). Left-opening exports mirror the asymmetric leaf geometry as well as reversing its travel. Place/mirror the guide and catcher posts appropriately for that arrangement.

## N-right prototype integration

The drive stays at Blender `(2.18, -0.22, 0)`. Its pinion spans Y
`0.105..0.145`, meeting the leaf rack centered at Y `0.125`.
Static exports reset object locations; assembly placement is reconstructed in
`SG_Proto.lua` and `SG_models.txt`. IMPORTANT (verified in game): the model is
rotated 180 degrees about the vertical axis in PZ and the spriteModel
`translate` is applied afterwards, in world axes. For a part at Blender
`(b, y_b)` on a carrier cell shifted `k` cells towards -x from the leaf cell:
`translate_x = -0.5 - b + k`, `translate_z = -0.5 + y_b`. Drive: `b=2.18`,
`y_b=-0.22`, `k=2` gives `(-0.68, 0, -0.72)`. Do not "fix" it back to
`(-0.32, 0, -0.28)`, which put the drive in the passage. See
`research/vanilla-gates.md`.
Restart the game after changing model scripts and spawn a fresh assembly for
visual verification. The Blender Studio viewport is a modelling preview;
final colour, shading and small-detail readability must be assessed in PZ.

Visual polish: cylindrical sides use smooth normals while caps, housings and
brackets remain flat. Wire radius is 0.0055 (previously 0.004), with six sides;
frame tubes have eight sides. Rack teeth use 52 larger teeth instead of 78.
The opaque atlas separates pale galvanized wire, painted frame, dark fittings
and olive drive housing, with restrained variation and wear. The updater
preserves the catcher geometry and rebuilds the atlas as well as meshes.
`preview_game_view.py` creates an approximate PZ orthographic camera and sets
the viewport to the same framing. It does not reproduce the game's lighting.
The previous art is preserved in `before_visual_polish/`.


## Two-cell leaf revision (2026-10-04)

Supersedes the tail/guide-station dimensions above. The complete moving leaf,
including rack and carriage, fits X 0..2 exactly. The carriage has four upper
rollers at X 1.82/1.94 straddling a fixed overhead guide rib spanning world
X 1.75..4.01 in the parking zone. Static guidance adds no moving door tail.
The drive moved to X 2.0, keeping Y -0.22; current game translation is
(-0.5,0,-0.6), retaining the calibrated perpendicular anchor.
The N-right debug assembly is supported. Left-opening leaves mirror the
carriage; their static beam/post arrangement also needs mirroring.
The preceding art is preserved in before_two_cell_leaf/.

## Short post-guide revision (2026-10-04)

Supersedes the overhead beam revision above. Removed the beam and leaf-mounted
carriage. A short post bracket carries two pairs of rollers at world X 1.88
and 2.12; at least one full pair engages the top rail at every animation frame.
The moving mesh still stays within X 0..2. The motor has a compact offset
gearbox passing beside the post, and a short output shaft beyond its front
face. Drive/post mesh intersection checks report zero surface intersections.
The rail is now 0.025 wide and 0.022 high, with a muted brown steel swatch.
Wire pitch is 0.13 and radius 0.005; galvanized wire and caps are less bright,
while dark fittings are lighter. A welded crossmember supports the handle.
Copies of the previous scene, scripts, texture and GLBs are in
before_post_roller_revision/. These are game-scale art adjustments, awaiting
in-game visual verification under the actual lighting and zoom.
