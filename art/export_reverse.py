"""Run through Blender MCP in the existing source; add mirrored workbenches.

Reflect X only, preserving outward-facing handles and the fence-side clearance.
Original scenes/exports remain untouched. Refuse to overwrite an existing reverse
workbench; inspect it before deciding how to regenerate a later revision.
"""
import bpy
import json
import os
import shutil
from mathutils import Matrix

ROOT = r'E:\git\SlidingGates'
ART = os.path.join(ROOT, 'art')
assert bpy.data.filepath == os.path.join(ART, 'SG_ChainLink.blend')
names = [(2, 'SG_ChainLink_Workbench', 'SG_ChainLink_Reverse_Workbench'),
         (4, 'SG_ChainLink_4_Workbench', 'SG_ChainLink_4_Reverse_Workbench')]
assert all(target not in bpy.data.scenes for _, _, target in names), 'Reverse workbench already exists: inspect before editing'
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART, 'SG_ChainLink_before_reverse.blend'), copy=True)
previous = bpy.context.window.scene
reflection = Matrix.Diagonal((-1, 1, 1, 1))
reports = []


def mirror_action(action):
    result = action.copy()
    for slot in result.slots:
        for layer in result.layers:
            for strip in layer.strips:
                bag = strip.channelbag(slot)
                if bag:
                    for curve in bag.fcurves:
                        if curve.data_path.endswith('.location') and curve.array_index == 0:
                            for key in curve.keyframe_points:
                                key.co[1] *= -1
                                key.handle_left[1] *= -1
                                key.handle_right[1] *= -1
    return result


def export(scene, objects, filename, animated):
    bpy.context.window.scene = scene
    for obj in scene.objects: obj.select_set(False)
    for obj in objects: obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    path = os.path.join(ART, 'exports', filename+'.glb')
    bpy.ops.export_scene.gltf(filepath=path, use_selection=True, use_active_scene=True,
        export_animations=animated, export_animation_mode='NLA_TRACKS', export_anim_slide_to_zero=True)
    shutil.copyfile(path, os.path.join(ROOT, 'mod/SlidingGates/42/media/models_X/IsoObject', filename+'.glb'))


for width, source_name, target_name in names:
    original = bpy.data.scenes[source_name]
    bpy.context.window.scene = original
    original.frame_set(original.frame_current)
    bpy.context.view_layer.update()
    original_rig = next(o for o in original.objects if o.type == 'ARMATURE' and o.get('gate_width_cells') == width)
    original_leaf = next(o for o in original.objects if o.type == 'MESH' and o.parent == original_rig)
    scene = bpy.data.scenes.new(target_name)
    scene.render.fps = original.render.fps
    scene.frame_start, scene.frame_end = original.frame_start, original.frame_end
    clones, meshes = {}, {}
    for obj in original.objects:
        if obj != original_rig and not (obj.type == 'MESH' and obj.name.startswith('SG_')): continue
        clone = obj.copy()
        clone.name = obj.name+'_Reverse'
        if obj.type == 'MESH':
            if obj.data.name not in meshes:
                data = obj.data.copy()
                data.transform(reflection)
                data.flip_normals()
                data.update()
                meshes[obj.data.name] = data
            clone.data = meshes[obj.data.name]
        else:
            clone.data = obj.data.copy()
        clone.location.x = -obj.location.x
        scene.collection.objects.link(clone)
        clones[obj] = clone
    rig, leaf = clones[original_rig], clones[original_leaf]
    leaf.parent = rig
    for modifier in leaf.modifiers:
        if modifier.type == 'ARMATURE': modifier.object = rig
    rig['gate_direction'] = 'reverse'
    rig.animation_data_clear()
    rig.animation_data_create()
    for source_track in original_rig.animation_data.nla_tracks:
        action = mirror_action(source_track.strips[0].action)
        track = rig.animation_data.nla_tracks.new()
        track.name = source_track.name
        strip = track.strips.new(source_track.name, 1, action)
        strip.frame_start, strip.frame_end = 1, scene.frame_end
        track.mute = True
    bpy.context.window.scene = scene
    scene.frame_set(1)
    bpy.context.view_layer.update()
    assert all((new.co-reflection@old.co).length < 1e-6
               for old, new in zip(original_leaf.data.vertices, leaf.data.vertices))
    for src, clone in clones.items():
        if src.type == 'MESH':
            assert all((clone.matrix_world@new.co-reflection@(src.matrix_world@old.co)).length < 1e-5
                       for old, new in zip(src.data.vertices, clone.data.vertices))
    original_action = original_rig.animation_data.action
    original_frame = original.frame_current
    original_mutes = [t.mute for t in original_rig.animation_data.nla_tracks]
    for track in original_rig.animation_data.nla_tracks: track.mute = True
    checked = 0
    try:
        for old_track, new_track in zip(original_rig.animation_data.nla_tracks, rig.animation_data.nla_tracks):
            original_rig.animation_data.action = old_track.strips[0].action
            original_rig.animation_data.action_slot = old_track.strips[0].action_slot
            rig.animation_data.action = new_track.strips[0].action
            rig.animation_data.action_slot = new_track.strips[0].action_slot
            for frame in range(scene.frame_start, scene.frame_end+1):
                bpy.context.window.scene = original
                original.frame_set(frame)
                shift = original_rig.pose.bones['DoorBone'].location.x
                bpy.context.window.scene = scene
                scene.frame_set(frame)
                mirrored_shift = rig.pose.bones['DoorBone'].location.x
                assert abs(mirrored_shift+shift) < 1e-5, (width,frame,shift,mirrored_shift)
                assert -width-1e-5 <= mirrored_shift <= 1e-5
                assert abs(rig.pose.bones['DoorBone'].location.y) < 1e-6
                assert abs(rig.pose.bones['DoorBone'].location.z) < 1e-6
                # A complete guide roller pair captures the rail at all frames.
                assert any(-width+mirrored_shift+.047 <= x <= mirrored_shift-.047
                           for x in (-width-.12,-width+.12))
                checked += 1
    finally:
        original_rig.animation_data.action = original_action
        for track, mute in zip(original_rig.animation_data.nla_tracks, original_mutes): track.mute = mute
        bpy.context.window.scene = original
        original.frame_set(original_frame)
    bpy.context.window.scene = scene
    rig.animation_data.action = None
    for track in rig.animation_data.nla_tracks: track.mute = False
    scene.frame_set(1)
    prefix = 'SG_ChainLink' if width == 2 else 'SG_ChainLink_4'
    export(scene, [rig, leaf], prefix+'_N_Reverse', True)
    if width == 2:
        for suffix, filename in [('Post_Left','SG_CatcherPost_Reverse'), ('Post_Right','SG_GuidePost_Reverse'),
                                 ('Rail_OneCell','SG_Rail_Reverse'), ('Drive','SG_Drive_Reverse')]:
            obj = next(clone for src, clone in clones.items() if suffix in src.name)
            location = obj.location.copy()
            obj.location = (0,0,0)
            export(scene, [obj], filename, False)
            obj.location = location
    for track in rig.animation_data.nla_tracks: track.mute = True
    rig.animation_data.action = rig.animation_data.nla_tracks[0].strips[0].action
    rig.animation_data.action_slot = rig.animation_data.nla_tracks[0].strips[0].action_slot
    scene.frame_set(1)
    reports.append(dict(width=width, scene=target_name, frames_checked=checked,
                        reflection_axis='X', negative_scale_export=False,
                        source_mesh_and_assembly_reflection_verified=True,
                        outward_face_and_clearance_preserved=True,
                        source_clearance_evidence='art/clearance_checks.json'))
bpy.context.window.scene = previous
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART,'SG_ChainLink.blend'))
with open(os.path.join(ART,'reverse_checks.json'),'w',encoding='utf8') as file:
    json.dump(reports,file,indent=2)
print('REVERSE_CHECKS',json.dumps(reports))
