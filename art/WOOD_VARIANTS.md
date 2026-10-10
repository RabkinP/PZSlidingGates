# Wooden sliding gates

Saved types `wood` and `wood4` use 2 and 4 cells, N/W forward/reverse placement,
the existing rigid DoorBone, and Open/Close clips of 3/6 seconds (24 fps).
No automatic upgrading: quality is persisted by the existing registry, part metadata
and multiplayer snapshot system. Carpentry minimum 4; low 4, medium 5–6, high 7+.

## Appearance and construction

The installed native wall references are in `research/wood-references/wall-quality.png`:
vanilla wall levels use carpentry 2–3, 4–5 and 6+, sprites 44/45, 40/41, 24/25.
Our chosen skill thresholds differ, but match that visual progression. The atlas uses
interior grain from native high wall 25 and the installed DoorKnob texture. References
and source crops are reproducible with `research/inspect-wood-references.py` and
`tools/build_wood_atlas.py`; provenance is in `wood_atlas_provenance.json`.

Frame, posts, crossbars, diagonal, guide and support brackets are timber. Fasteners,
rack, roller axes, motor enclosure and gearbox remain metal; drive mounting is timber.
Wheel and guide roller running surfaces remain rubber. Native DoorKnob FBX geometry
is turned upright and merged into the leaf, preserving its UV inside atlas tile 5.
Width 2 has one outward handle and width 4 has two. Low-quality plates tilt 9°/-7°;
the two wide-gate knobs also have different heights. Medium/high knobs are aligned.

Low quality has uneven, mismatched boards and small gaps; medium reduces gaps/tilt;
high uses closely fitted straight boards. All mechanical tracks remain straight.
Medium boards mix straight and leaning boards with varying 10–38 mm gaps;
their upper ends stay within their individual pitches to avoid board overlap.
All boards reach the bottom timber at Z .18. That timber retains its underside
at .095 but is 85 mm tall, keeping infill above the lower catcher slot at .17.
Four-cell leaves have a 90 mm central upright separating the two braced bays.
Each diagonal is clipped to the frame opening: its sawn horizontal/vertical ends
abut the bottom/top timber and the side uprights, including damaged brace halves.
Damage is independent of quality: stage 1 breaks four boards per two-cell bay,
stage 2 breaks eight, stage 3 also breaks each diagonal with a small surviving fibre.
Upper/lower board halves remain on their respective crossbars and lean outward near
the fracture. All breaks are small jagged openings; the outside frame is intact.
Thresholds remain <=75/50/25% native door health. Model swaps defer until motion ends.

Recipes require hammer and saw; width 2 consumes 12 planks, 24 nails, 8 screws,
1 Doorknob, 2 metal bars and 1 rubber hose. Width 4 consumes 20 planks, 40 nails,
8 screws, 2 Doorknobs, 3 bars and 2 hoses. The configured salvage budget matches
these resources; existing 70% dismantling rules apply, using vanilla Wood skill/tools.
Health follows vanilla: carpentry level × 300 per carrier. XP: Woodwork 40 (width 2), 50 (width 4).
Resource amounts and health are balancing choices, not engine requirements.

## Workflow and checks

Workbenches `SG_Wood_*` live in `SG_ChainLink.blend`; do not rebuild metal scenes.
The builder refuses existing wooden scenes and saves a recoverable source copy.
Import the installed `media/models_X/WorldItems/DoorKnob.fbx` into
`SG_Wood_References` before first build. `update_wood_variants.py` updates only wood.

1. `build_wood_variants.py` / `update_wood_variants.py` through existing Blender MCP.
2. `verify_wood_variants.py`: 48 scenes, both clips, all 10,464 frames; continuous
   guide capture and no moving/static surface intersections.
3. `export_wood_variants.py`: 48 single-mesh animated leaves and 8 static GLBs into
   `exports/wood`; exact clips, normals, UV and rigid skinning.
4. `tools/register_wood_models.py`: deploy 56 assets, 208 poses, 6 recipes and locales.
5. `tools/build_gate_tiles.py`: append wooden preview carriers 96..183.
6. `preview_wood_variants.py`: studio comparisons and build-menu icons, separate scenes.

`tests/test_gate_wood.py` covers skill boundaries, construction authority, health,
all orientations/qualities, drive, damage deferral, persistence/late MP, resources,
deployed GLB clips/weights/normals and frame evidence. All 17 repository checks pass.
Installed engine parsing: `research/probe-wood-native.py` and `probe-gate-tiles.py`.
Installed JNI import: `research/probe-wood-import.py`, 56 successful imports.
That importer probe reports counts and one vertex/normal/UV; it is not a whole-mesh
visual check. Engine fingerprint matches the maintained render audit.

The local mod junction points to this checkout, so deployed assets are available
after restarting PZ. Game appearance, vision/cutaways, fresh construction cursors,
movement in the world and real multiplayer packet delivery still need gameplay tests.
Studio comparisons do not establish final PZ appearance.
