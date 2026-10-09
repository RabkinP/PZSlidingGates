# Damage stages

Current gate geometry has four appearances: intact, Damage1 at <=75%,
Damage2 at <=50%, Damage3 at <=25% remaining native door health.
At zero health the existing whole-assembly destruction applies.

Damage is independent of construction quality. There are 36 new skinned GLBs:
widths 2/4 × qualities high/medium/low × forward/reverse × stages 1/2/3.
N/W use the same GLBs and retain their existing calibrated spriteModel anchors.

Damage bends wire infill outward and internal uprights. Mechanical parts,
outer frame, handles, rail and rack retain source geometry. Only short spans
on alternating wires break; crossing wires remain. Removed spans are under
0.065 model units (one cell is one unit); holes must never suggest a human passage.
The patches and deformation pattern are deterministic and grow across stages.
Closed-shell winding is corrected on damage meshes, including inherited inward
quality scrap straps; original quality meshes are preserved. Validate with
`verify_damage_normals.py`.

The authority polls loaded assemblies every 500ms using `getHealth/getMaxHealth`
on leaf/slave/block native doors. The worst observed stage is persisted as
registry `damage` and part `sgDamage`, so unloading an injured carrier or
recreating pocket blockers cannot restore the intact appearance. This is visual
damage tracking; it does not change native health or introduce repair gameplay.
`sgVisualDamage` keeps the active appearance during movement. Model changes
wait for the native track to end on both authority and client. Snapshots include
damage and use the existing instance/revision ordering. Legacy gates default
to intact and acquire their stage from surviving native door health.

Workflow:

1. `build_damage_variants.py` runs through the existing source Blender. It refuses
   existing damage scenes and saves a recoverable blend copy.
2. `verify_damage_variants.py` checks both clips, all frames and static intersections.
3. `export_damage_variants.py` exports only damage scenes to `exports/damage`.
4. `tools/register_damage_models.py` copies assets into the mod and derives all
   model/animation/spriteModel definitions from existing anchors and poses.
5. `preview_damage_variants.py` produces a comparison, not a gameplay rendering proof.

Do not run the general exporter on damage scenes. The quality exporter skips them.
Checks: `damage_checks.json` (7,848 frames without static intersections and
continuous roller capture), `damage_native_import.txt`,
`tests/test_gate_damage.py`, `tests/test_model_variants.py`,
`research/probe-gate-damage.py`. Actual game appearance and multiplayer packet
delivery still require a restarted PZ session with fresh test assemblies.

`check_damage_apertures.py` conservatively bounds empty-circle diameters in
the stage-3 XZ projection using nearest vertices plus a sampling margin.
The largest bound among all twelve severe variants is approximately 0.157
model units. This establishes small projected openings, not character physics.

Readability revision 2 uses broad buckling and sagging instead of small local
wire wrinkles. High-quality internal tubes now have intermediate rings so they
actually bend. Deformation fades out below z=0.40 and above z=1.55, preserving
clearance around the drive and guide bracket. `update_damage_variants.py` updates
only existing damage leaves and comparison meshes from pristine quality sources.
`preview_damage_native.py` provides approximate door-shader comparisons at native
1x and high-resolution 2x pixel coverage, ordered intact, 1, 2, 3 from left to right.
