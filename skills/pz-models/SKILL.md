---
name: pz-models
description: Create, edit, export and diagnose Blender/GLB models for Project Zomboid, using verified engine import, shading, coordinate and pixel-density behavior. Apply to PZ model appearance, placement, normals, UV, animation and spriteModel integration.
---

# Project Zomboid models

Use installed-game evidence rather than Blender appearance to decide how an asset will render. The verified baseline covers the Build 42 IsoObject/spriteModel path with the door shader. Vehicles, characters, weapons and other shaders require inspection of their own path before transferring these conclusions.

## Start with existing evidence

Read [the engine audit](references/engine-render-audit.md) when changing import, materials, normals, UV, placement or preview lighting. It records the tested JAR hash, relevant classes, shader files, native-import results and limitations. For project paths, helper commands and asset ownership, read [the workspace workflow](references/workspace-workflow.md).

Compare the installed projectzomboid.jar SHA256 with the audit before relying on version-specific behavior. Reuse the evidence when it matches; when it differs, re-extract the relevant current classes and inspect the selected shaders. PZMining supplies research tools, but its previously extracted classes can be older than the installed game. Shader files and runtime settings can change independently of the JAR: inspect them when diagnosing visual differences.

## Model decisions

- The ordinary audited importer selects one mesh, not every GLB mesh/material. Prefer one joined mesh and an external albedo atlas per model; separate independently placed static parts. Export outward normals and deliberate smoothing: this import path does not generate missing normals.
- Model scripts select the external PNG and shader. Blender metallic, roughness, normal maps, AO nodes and studio lighting do not survive the audited door path. Use readable silhouette, deliberate albedo contrast and broad local wear/occlusion when useful.
- Account for native pixel coverage before adding detail. Thin wires can be below one pixel; increasing polygons or PNG resolution cannot fix geometric coverage. Evaluate normal and high-resolution chunk modes, then actual gameplay zoom.
- Preserve calibrated origin, axes, scale and model-script anchors. PZ applies handedness, winding and UV conversions; do not add manual flips from an isolated expression. Inspect the complete Blender → GLB → native importer → VBO → shader route.
- Keep a gameplay footprint distinct from render bounds and animation travel. Validate moving geometry and clearances throughout both clips, not only the closed pose. Project-specific cell dimensions belong in project rules.
- The audited door shader discards alpha below 0.01 and writes depth. Geometry holes are an established option; transparent alternatives need explicit in-game depth/sorting verification.

## Edit and verify

Inspect the active Blender file/scene through Blender MCP before editing. Open the requested source in the existing Blender instance, preserve unrelated scene work, and save a recoverable source revision before destructive rebuilds. Use project builders/exporters when they encode required invariants; inspect their current behavior first.

Check geometry bounds, normals/winding, relevant part intersections, UV, bone weights, exported object selection and exact clip names. Use the game's native importer for import/UV/normal regressions where warranted. A successful import or one sampled vertex is not a full mesh or visual validation.

Keep diagnostic rendering separate from export materials. For this shader, Non-Color texture sampling, Raw output, the audited ambient/Lambert formula and native image density are useful approximations. The existing Blender preview is not a pixel-identical PZ renderer: it omits chunk filtering/depth/cutaways, runtime cell light and final passes.

After relevant model-script/asset changes, restart PZ and spawn a fresh test assembly. Assess ordinary/far zoom, movement, lighting, walls and chunk boundaries. Report Blender checks, native import and actual in-game checks separately; do not claim the final appearance verified from a preview alone.

When discovering a new engine fact, update the audit with the game fingerprint, class/method or shader evidence, scope and verification method. Keep design recommendations and temporary diagnostics distinguishable from proven engine behavior.
