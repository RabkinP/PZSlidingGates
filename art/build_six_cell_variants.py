"""Run in the live source Blender. Copy four-cell assemblies; build six-cell leaves.

Art only: no export, deployment, model-script or Lua changes. Existing workbenches
are fingerprinted and never modified. Set SIX_MATERIAL to chainlink or wood to
build one batch. Geometry helpers are loaded without running their old builders.
"""
import ast
import bpy
import bmesh
import hashlib
import json
import math
import os
from mathutils import Matrix, Vector

ART = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(ART, 'SG_ChainLink.blend')
assert os.path.normcase(bpy.data.filepath) == os.path.normcase(SOURCE)
MATERIAL = globals().get('SIX_MATERIAL', 'chainlink')
assert MATERIAL in ('chainlink', 'wood')


def definitions(filename, names, replacements=(), **values):
    """Import selected pure geometry helpers, excluding all builder side effects."""
    path = os.path.join(ART, filename)
    source = open(path, encoding='utf-8').read()
    for old, new in replacements:
        assert source.count(old) == 1, (filename, old)
        source = source.replace(old, new)
    tree = ast.parse(source, path)
    selected = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
    assert {n.name for n in selected} == set(names)
    namespace = dict(bpy=bpy, bmesh=bmesh, math=math, Vector=Vector, Matrix=Matrix)
    namespace.update(values)
    exec(compile(ast.Module(body=selected, type_ignores=[]), path, 'exec'), namespace)
    return namespace


def curves(action):
    for slot in action.slots:
        for layer in action.layers:
            for strip in layer.strips:
                bag = strip.channelbag(slot)
                if bag:
                    yield from bag.fcurves


def fingerprint(scene):
    digest = hashlib.sha256()
    def add(value):
        digest.update(repr(value).encode())
    add((scene.frame_start, scene.frame_end, scene.render.fps))
    for obj in sorted(scene.objects, key=lambda o: o.name):
        add((obj.name, tuple(obj.location), tuple(obj.rotation_euler), tuple(obj.scale)))
        if obj.type == 'MESH':
            add([tuple(v.co) for v in obj.data.vertices])
            add([(tuple(p.vertices), p.use_smooth) for p in obj.data.polygons])
            add([tuple(u.uv) for u in obj.data.uv_layers.active.data])
        if obj.animation_data:
            for track in obj.animation_data.nla_tracks:
                for strip in track.strips:
                    add((track.name, strip.frame_start, strip.frame_end))
                    for fc in curves(strip.action):
                        add((fc.data_path, fc.array_index,
                             [(tuple(k.co), tuple(k.handle_left), tuple(k.handle_right), k.interpolation)
                              for k in fc.keyframe_points]))
    return digest.hexdigest()


def source_name(material, quality, damage, reverse):
    if material == 'wood':
        name = 'SG_Wood_4_' + quality + ('_Reverse' if reverse else '')
    else:
        name = 'SG_ChainLink_4' + ('_Reverse' if reverse else '')
        name += '' if quality == 'high' else '_' + quality.title()
    return name + (f'_Damage{damage}' if damage else '') + '_Workbench'


def retime(rig, source_rig, label):
    rig.animation_data_clear()
    rig.animation_data_create()
    for oldtrack in source_rig.animation_data.nla_tracks:
        oldstrip = oldtrack.strips[0]
        action = oldstrip.action.copy()
        action.name = label + '_' + oldtrack.name
        for fc in curves(action):
            for key in fc.keyframe_points:
                for point in (key.co, key.handle_left, key.handle_right):
                    point.x = 1 + (point.x - 1) * 1.5
                    if fc.data_path.endswith('.location') and fc.array_index == 0:
                        point.y *= 1.5
            fc.update()
        track = rig.animation_data.nla_tracks.new()
        track.name = oldtrack.name
        strip = track.strips.new(oldtrack.name, 1, action)
        strip.action_slot = action.slots[0]
        strip.frame_start, strip.frame_end = 1, 217
        track.mute = True
    first = rig.animation_data.nla_tracks[0].strips[0]
    rig.animation_data.action = first.action
    rig.animation_data.action_slot = first.action_slot


def copy_assembly(source, name, mesh, reverse):
    scene = bpy.data.scenes.new(name)
    scene.world = source.world
    for key in source.keys():
        scene[key] = source[key]
    scene['sg_six_cell'] = True
    scene['sg_source_scene'] = source.name
    scene['SG_notes'] = '6-cell copy of 4-cell assembly; 6-unit stroke; 9s clips; art only.'
    scene.render.fps = 24
    scene.frame_start, scene.frame_end = 1, 217
    oldrig = next(o for o in source.objects if o.type == 'ARMATURE')
    oldleaf = next(o for o in source.objects if o.type == 'MESH' and o.parent == oldrig)
    clones = {}
    for obj in source.objects:
        if obj != oldrig and obj.type != 'MESH':
            continue
        clone = obj.copy()
        clone.name = name.removesuffix('_Workbench') + '_' + ('Rig' if obj == oldrig else 'Leaf' if obj == oldleaf else obj.name)
        if obj == oldrig:
            clone.data = obj.data.copy()
        elif obj == oldleaf:
            clone.data = mesh
        # Static meshes are reused exactly, with independent object transforms.
        scene.collection.objects.link(clone)
        clones[obj] = clone
        if obj != oldleaf and ('Post_Right' in obj.name or 'Drive' in obj.name):
            clone.location.x += -2 if reverse else 2
        if clone.get('export_static') is not None:
            clone['export_static'] = False
    rig, leaf = clones[oldrig], clones[oldleaf]
    rig['gate_width_cells'], rig['duration_seconds'] = 6, 9.0
    rig['gate_direction'] = 'reverse' if reverse else 'forward'
    leaf.parent = rig
    for modifier in leaf.modifiers:
        if modifier.type == 'ARMATURE':
            modifier.object = rig
    leaf.vertex_groups.clear()
    leaf.vertex_groups.new(name='DoorBone').add(list(range(len(mesh.vertices))), 1.0, 'REPLACE')
    leaf['handle_count'] = 2
    # Complete the 12-cell ground track using unchanged one-cell rail meshes.
    oldrail = next(o for o in source.objects if 'Rail_OneCell' in o.name)
    for x in range(8, 12):
        clone = oldrail.copy()
        clone.name = name.removesuffix('_Workbench') + f'_Rail_Preview_{x}'
        clone.location.x = -x if reverse else x
        if clone.get('export_static') is not None:
            clone['export_static'] = False
        scene.collection.objects.link(clone)
    retime(rig, oldrig, name.removesuffix('_Workbench'))
    bpy.context.window.scene = scene
    scene.frame_set(1)
    return scene, rig, leaf


sources = [bpy.data.scenes[source_name(MATERIAL, q, d, r)]
           for r in (False, True) for q in ('high', 'medium', 'low') for d in range(4)]
targets = [s.name.replace('_4', '_6', 1) for s in sources]
assert not any(name in bpy.data.scenes for name in targets), 'Six-cell batch exists; inspect instead of rebuilding.'
originals = {s.name: fingerprint(s) for s in bpy.data.scenes if s.name.endswith('_Workbench')}
backup = os.path.join(ART, 'SG_ChainLink_before_six.blend')
if not os.path.exists(backup):
    bpy.ops.wm.save_as_mainfile(filepath=backup, copy=True)

canonical = bpy.data.scenes['SG_ChainLink_4_Workbench']
oldrig = next(o for o in canonical.objects if o.type == 'ARMATURE')
oldleaf = next(o for o in canonical.objects if o.type == 'MESH' and o.parent == oldrig)
net = definitions('build_chainlink.py', ('rod', 'box', 'mesh', 'handle', 'leaf'),
                  [('if WIDTH==4:', 'if WIDTH>=4:')],
                  WIDTH=6, CLEARANCE=.10, mat=oldleaf.data.materials[0], smooth_faces=set())
temporary = bpy.data.collections.new('SG_Six_Geometry_Temporary')
net['col'] = temporary
base_object = net['mesh']('SG_ChainLink_6_Base', net['leaf'])
base = base_object.data
for vertex in base.vertices:
    vertex.co.y += .10
base.update()

if MATERIAL == 'chainlink':
    quality_helpers = definitions('build_quality_variants.py', ('components', 'quality_mesh'))
    damage_helpers = definitions('build_damage_variants.py', ('components', 'orient_shells', 'damage_mesh'))
else:
    wood = definitions('build_wood_variants.py', ('components', 'Mesh', 'leaf_mesh'),
        [('if width==4: m.box((2,.10,1.0),(.090,.050,1.71),2)',
          'for x in range(2,width,2): m.box((x,.10,1.0),(.090,.050,1.71),2)')],
        mat=bpy.data.materials['SG_Wood_Atlas'],
        KNOB=next(o.data for o in bpy.data.scenes['SG_Wood_References'].objects if o.type == 'MESH'))

reports = []
for quality in ('high', 'medium', 'low'):
    if MATERIAL == 'chainlink':
        intact = base.copy() if quality == 'high' else quality_helpers['quality_mesh'](base, 6, quality.title(), False)[0]
    for damage in range(4):
        if MATERIAL == 'chainlink':
            mesh, details = (intact.copy(), {}) if not damage else damage_helpers['damage_mesh'](intact, 6, False, damage)
            # Correct closed-shell winding without changing smooth flags or UVs.
            damage_helpers['orient_shells'](mesh)
        else:
            mesh, broken = wood['leaf_mesh'](base, 6, quality, damage, False)
            details = dict(broken_boards=broken, broken_diagonal=damage == 3)
        for reverse in (False, True):
            data = mesh.copy()
            if reverse:
                data.transform(Matrix.Diagonal((-1, 1, 1, 1)))
                data.flip_normals()
                data.update()
            source = bpy.data.scenes[source_name(MATERIAL, quality, damage, reverse)]
            name = source.name.replace('_4', '_6', 1)
            scene, rig, leaf = copy_assembly(source, name, data, reverse)
            scene['sg_material'], scene['sg_quality'], scene['sg_damage'] = MATERIAL, quality, damage
            for key, value in details.items():
                leaf[key] = value
            data.name = name.removesuffix('_Workbench') + '_Mesh'
            reports.append(dict(scene=name, source=source.name, vertices=len(data.vertices),
                                polygons=len(data.polygons), quality=quality, damage=damage,
                                reverse=reverse, **details))
        bpy.data.meshes.remove(mesh)
    if MATERIAL == 'chainlink':
        bpy.data.meshes.remove(intact)
bpy.data.objects.remove(base_object, do_unlink=True)
bpy.data.meshes.remove(base)
bpy.data.collections.remove(temporary)
assert all(fingerprint(bpy.data.scenes[name]) == value for name, value in originals.items()), 'Original scene changed'
with open(os.path.join(ART, f'six_{MATERIAL}_build_checks.json'), 'w', encoding='utf-8') as handle:
    json.dump(dict(originals_unchanged=True, originals=originals, scenes=reports), handle, indent=2)
bpy.context.window.scene = bpy.data.scenes['SG_Wood_6_high_Workbench' if MATERIAL == 'wood' else 'SG_ChainLink_6_Workbench']
bpy.ops.wm.save_as_mainfile(filepath=SOURCE)
print('SIX_BUILT', MATERIAL, len(reports), 'scenes; originals unchanged')
