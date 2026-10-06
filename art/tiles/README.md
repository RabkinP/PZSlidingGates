# Construction carriers

`python tools/build_gate_tiles.py` rebuilds the source PNG, binary pack/tile definitions,
manifest and model bindings. The PNG is intentionally transparent: gate geometry is
rendered from GLB via spriteModel, not baked into a gate sprite sheet.

Deployed files:

- `mod/SlidingGates/42/media/texturepacks/SG_GatesPreview.pack` (PZPK v1).
- `mod/SlidingGates/42/media/SG_GatesPreview.tiles` (tdef v1).
- `mod/SlidingGates/common/media/spriteModels.txt` (required common location in this B42 loader).
- `mod/SlidingGates/42/mod.info`: pack registration and tiledef file number **6842**.

These are construction-only sprites. Existing gameplay door/vehicle collision carriers
and saved gates are not migrated by this change. Do not add door/collision/PhysicsShape
properties to preview sprites or reuse these entity sprites for other buildable entities:
SpriteConfig's entity-to-sprite registry is global.

The namespace is `sg_gates_preview_01`, tileset number **1**, eight columns.
Keep file number, tileset number and existing indices stable:

| Index | Purpose |
| --- | --- |
| 0, 1 | Two-cell opening row; index 1 carries the entire closed leaf |
| 2, 3, 4, 5 | Four-cell opening row; index 5 carries the entire closed leaf |
| 6, 7 | Reserved |
| 8 | Catcher post |
| 9 | Guide post |
| 10 | One-cell rail, repeated along opening and pocket |
| 11 | Drive (reserved for future drive construction preview; bare gate has no drive) |
| 12..15 | Reserved |

Blank indices use the existing tiny hidden rail model. Atlas entries have explicit
untrimmed 128×256 bounds, even though every pixel is transparent. Do not run an atlas
optimizer that drops empty entries.

The entity cursor normally constructs texture-only sprite copies. Our `cacheSprites`
hook uses registered sprites so it retains their model binding. The base entity renderer
draws the leaf; the render hook draws posts and rails through `RenderGhostTileColor`.
It creates no temporary world objects. The floor grid remains the standard entity grid.
Valid models use vanilla white tint, invalid models red; the floor grid supplies its
own highlight colors. The current native model ghost path ignores alpha=0.6 and uses
alpha=1, so it is not a translucent model preview.

Tests: `tests/test_gate_tiles.py`, `tests/test_gate_preview.py` (lupa),
`research/probe-gate-tiles.py` (installed-game parsers). Native probe report:
`research/render-audit/gate-tiles-native.txt`. Restart PZ after changing packs or tile
definitions; test fresh construction cursors for both widths, valid/invalid placement,
moving/cancelling the cursor and completing a build. No visual gameplay test was
performed by the headless checks.
