# Workshop poster scene

The user-approved final poster is `poster_final.png` (1254 × 1254), supplied
2026-10-09. Its exact copy is `mod/SlidingGates/42/poster.png`, registered in
`mod.info`. Earlier generated covers and Blender drafts are retained as history.

`SG_Poster.blend` is a standalone editable staging scene, separate from game art.
`poster_draft.png` is a 2000 × 1500 Cycles draft, without typography.

The four-cell chain-link assembly is copied from `../SG_ChainLink.blend`,
with its leaf fixed at 40% open (1.6 units). Posts, drive and all eight rail
segments keep their source placement. The original game mesh and animation
data are not edited. A tall wooden privacy fence, weathered asphalt entrance,
cracks, a planted corner and two traffic cones surround the assembly, based on
the user's gameplay screenshot. Camera and evening lights are editable.

Collections separate gate, fence, ground, details and lighting. The atlas is
packed for portability. Poster materials and Cycles lighting are artistic;
this image is not a simulation of the game's renderer.

The reproducible builder is `../build_poster_scene.py`. Run through the existing
Blender MCP in a session without an `SG_Poster` scene; it appends the four-cell
source scene if necessary and writes only poster dependencies to the new file.
Then run `../update_poster_environment.py` to apply the wooden-fence reference.
That script retains a recoverable `SG_Poster_before_wood.blend` revision.
For the current material/detail pass, run `tools/extract_poster_tiles.py` and
`tools/prepare_poster_game_materials.py` from the repository, then execute
`../refine_poster_game_materials.py` through Blender MCP. This retains
`SG_Poster_before_materials.blend` and uses installed-game timber grain,
asphalt, grass, damage decals and ornamental shrub sprites. Extraction source
and affine transforms are recorded in `game_textures/manifest.json` and
`game_textures/prepared/provenance.json`. Native textures remain local poster
resources; none are added to the gameplay mod. Fine branching fissures, nail
heads, occasional timber splits and uneven board tips add geometric detail.
Render with F12. Composition and title treatment can be refined before publishing.
