"""Run via live Blender MCP: 48 six-cell GLBs; no deploy or game-code changes.

Use the established specialized exporters with an explicit width filter and a
separate output root, preserving every existing two/four-cell export.
"""
import bpy
import hashlib
import json
import os
from pathlib import Path

ART = Path(__file__).resolve().parent
OUT = ART / 'exports' / 'six'
assert Path(bpy.data.filepath).resolve() == ART / 'SG_ChainLink.blend'
scenes = [s for s in bpy.data.scenes if s.get('sg_six_cell')]
assert len(scenes) == 48
assert all(next(o for o in s.objects if o.type == 'ARMATURE')['gate_width_cells'] == 6 for s in scenes)
OUT.mkdir(parents=True, exist_ok=True)
old_exports = {p: hashlib.sha256(p.read_bytes()).hexdigest()
               for p in (ART / 'exports').rglob('*.glb') if OUT not in p.parents}
previous = bpy.context.window.scene
try:
    # Intact high-quality chain-link is the only batch not owned by a specialized exporter.
    for reverse in (False, True):
        scene = bpy.data.scenes['SG_ChainLink_6' + ('_Reverse' if reverse else '') + '_Workbench']
        bpy.context.window.scene = scene
        rig = next(o for o in scene.objects if o.type == 'ARMATURE')
        leaf = next(o for o in scene.objects if o.type == 'MESH' and o.parent == rig)
        ad = rig.animation_data
        action, slot, frame = ad.action, ad.action_slot, scene.frame_current
        mutes = [t.mute for t in ad.nla_tracks]
        selected, active = [o for o in scene.objects if o.select_get()], bpy.context.view_layer.objects.active
        try:
            ad.action = None
            for track in ad.nla_tracks:
                track.mute = False
            for obj in scene.objects:
                obj.select_set(False)
            rig.select_set(True)
            leaf.select_set(True)
            bpy.context.view_layer.objects.active = rig
            name = 'SG_ChainLink_6_N_' + ('Reverse' if reverse else 'Right')
            bpy.ops.export_scene.gltf(filepath=str(OUT / (name + '.glb')), use_selection=True,
                use_active_scene=True, export_animations=True, export_animation_mode='NLA_TRACKS',
                export_anim_slide_to_zero=True)
        finally:
            ad.action = action
            if slot:
                ad.action_slot = slot
            for track, mute in zip(ad.nla_tracks, mutes):
                track.mute = mute
            scene.frame_set(frame)
            for obj in scene.objects:
                obj.select_set(obj in selected)
            bpy.context.view_layer.objects.active = active
    for script in ('export_quality_variants.py', 'export_damage_variants.py', 'export_wood_variants.py'):
        path = ART / script
        exec(compile(path.read_text(encoding='utf-8'), str(path), 'exec'),
             {'__file__': str(path), 'EXPORT_ROOT': str(OUT), 'EXPORT_WIDTHS': (6,)})
finally:
    bpy.context.window.scene = previous
paths = sorted(OUT.rglob('*.glb'))
assert len(paths) == 48
assert all('_6_' in p.name for p in paths)
assert all(hashlib.sha256(p.read_bytes()).hexdigest() == digest for p, digest in old_exports.items())
manifest = [dict(path=p.relative_to(ART).as_posix(), bytes=p.stat().st_size,
                 sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths]
(ART / 'six_export_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print('SIX_EXPORTED', len(paths), 'GLBs;', len(old_exports), 'older exports unchanged;', OUT)
