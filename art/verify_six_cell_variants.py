"""Live Blender checks for six-cell art only. No exports or game-code changes.

Set SIX_VERIFY_SCENES to a list of names for bounded batches. Intersections use
the rigid leaf's BVH once and translate static surfaces into its coordinate frame
at every animation frame; this avoids rebuilding a large wire mesh every frame.
"""
import bpy
import json
import math
import os
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ART = os.path.dirname(os.path.abspath(__file__))
names = globals().get('SIX_VERIFY_SCENES')
scenes = [bpy.data.scenes[n] for n in names] if names else [s for s in bpy.data.scenes if s.get('sg_six_cell')]
assert scenes
reports = []


def bounds(points):
    return [(min(p[i] for p in points), max(p[i] for p in points)) for i in range(3)]


def shells(mesh):
    adjacency = [set() for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        adjacency[a].add(b)
        adjacency[b].add(a)
    seen, labels, centers = set(), {}, []
    for vertex in mesh.vertices:
        if vertex.index in seen:
            continue
        todo, ids = [vertex.index], set()
        while todo:
            i = todo.pop()
            if i in ids:
                continue
            ids.add(i)
            todo.extend(adjacency[i] - ids)
        seen.update(ids)
        center = sum((mesh.vertices[i].co for i in ids), Vector()) / len(ids)
        for i in ids:
            labels[i] = len(centers)
        centers.append(center)
    volumes = [0.] * len(centers)
    mesh.calc_loop_triangles()
    for tri in mesh.loop_triangles:
        label = labels[tri.vertices[0]]
        a, b, c = [mesh.vertices[i].co - centers[label] for i in tri.vertices]
        volumes[label] += a.dot(b.cross(c)) / 6
    assert all(v > 1e-12 for v in volumes), ('Non-outward/degenerate shells', min(volumes))
    return len(volumes)


for scene in scenes:
    bpy.context.window.scene = scene
    rig = next(o for o in scene.objects if o.type == 'ARMATURE')
    leaf = next(o for o in scene.objects if o.type == 'MESH' and o.parent == rig)
    reverse = rig.get('gate_direction') == 'reverse'
    sign = -1 if reverse else 1
    assert rig['gate_width_cells'] == 6 and rig['duration_seconds'] == 9
    assert (scene.frame_start, scene.frame_end, scene.render.fps) == (1, 217, 24)
    assert all(abs(v - 1) < 1e-7 for o in scene.objects for v in o.scale)
    assert leaf['handle_count'] == 2
    assert len(leaf.data.materials) == 1 and leaf.data.uv_layers.active
    assert all(math.isfinite(x) and 0 <= x <= 1 for uv in leaf.data.uv_layers.active.data for x in uv.uv)
    assert all(p.area > 1e-10 for p in leaf.data.polygons)
    assert all(len(v.groups) == 1 and abs(v.groups[0].weight - 1) < 1e-7 and
               leaf.vertex_groups[v.groups[0].group].name == 'DoorBone' for v in leaf.data.vertices)
    assert len([b for b in rig.data.bones if b.use_deform]) == 1
    assert {t.name for t in rig.animation_data.nla_tracks} == {'Open', 'Close'}
    shell_count = shells(leaf.data)
    canonical_x = [sign * v.co.x for v in leaf.data.vertices]
    assert min(canonical_x) >= -1e-6 and max(canonical_x) <= 6 + 1e-6
    ad = rig.animation_data
    old_action, old_slot = ad.action, ad.action_slot
    old_mutes = [t.mute for t in ad.nla_tracks]
    for track in ad.nla_tracks:
        track.mute = True
    scene.frame_set(1)
    bpy.context.view_layer.update()
    leaf_coords = [leaf.matrix_world @ v.co for v in leaf.data.vertices]
    leaf_faces = [tuple(p.vertices) for p in leaf.data.polygons]
    leaf_tree = BVHTree.FromPolygons(leaf_coords, leaf_faces)
    leaf_bounds = bounds(leaf_coords)
    fixed = []
    for obj in scene.objects:
        if obj.type == 'MESH' and obj != leaf:
            points = [obj.matrix_world @ v.co for v in obj.data.vertices]
            fixed.append((obj.name, points, [tuple(p.vertices) for p in obj.data.polygons], bounds(points)))
    guide = next(o for o in scene.objects if 'Post_Right' in o.name)
    drive = next(o for o in scene.objects if 'Drive' in o.name)
    def object_tree(obj):
        return BVHTree.FromPolygons([obj.matrix_world @ v.co for v in obj.data.vertices],
                                   [tuple(p.vertices) for p in obj.data.polygons])
    assert not object_tree(guide).overlap(object_tree(drive)), 'Motor/post collision'
    rails = [o for o in scene.objects if 'Rail_' in o.name]
    assert sorted(round(sign * o.location.x) for o in rails) == list(range(12))
    count, hits = 0, []
    try:
        for track in ad.nla_tracks:
            strip = track.strips[0]
            ad.action, ad.action_slot = strip.action, strip.action_slot
            assert abs(strip.frame_end - 217) < 1e-5
            positions = []
            for frame in range(1, 218):
                scene.frame_set(frame)
                location = rig.pose.bones['DoorBone'].location.copy()
                shift = sign * location.x
                assert abs(location.y) < 1e-6 and abs(location.z) < 1e-6
                assert -1e-5 <= shift <= 6 + 1e-5
                assert any(shift + .047 <= x <= shift + 6 - .047 for x in (5.88, 6.12)), 'Guide capture lost'
                positions.append(shift)
                # Confirm evaluated skinning is the same rigid translation used below.
                if frame in (1, 109, 217):
                    evaluated = leaf.evaluated_get(bpy.context.evaluated_depsgraph_get())
                    assert len(evaluated.data.vertices) == len(leaf_coords)
                    assert all((evaluated.matrix_world @ v.co - leaf_coords[i] - location).length < 2e-5
                               for i, v in enumerate(evaluated.data.vertices)), 'Non-rigid deformation'
                for name, points, faces, bbox in fixed:
                    if any(leaf_bounds[i][1] + location[i] < bbox[i][0] - 1e-7 or
                           bbox[i][1] < leaf_bounds[i][0] + location[i] - 1e-7 for i in range(3)):
                        continue
                    tree = BVHTree.FromPolygons([p - location for p in points], faces)
                    overlap = leaf_tree.overlap(tree)
                    if overlap and not any(h['part'] == name for h in hits):
                        hits.append(dict(part=name, clip=track.name, frame=frame, faces=overlap[:4]))
                count += 1
            expected = (0, 6) if track.name == 'Open' else (6, 0)
            assert abs(positions[0] - expected[0]) < 1e-5 and abs(positions[-1] - expected[1]) < 1e-5
            assert all((b - a) * (1 if track.name == 'Open' else -1) >= -1e-6
                       for a, b in zip(positions, positions[1:])), 'Non-monotonic travel'
    finally:
        ad.action = old_action
        if old_slot:
            ad.action_slot = old_slot
        for track, mute in zip(ad.nla_tracks, old_mutes):
            track.mute = mute
        scene.frame_set(1)
    reports.append(dict(scene=scene.name, frames=count, shells=shell_count, collisions=hits,
                        width=6, duration=9, rail_capture=True, rigid_weights=True,
                        outward_shells=True, uv_checked=True, clips=['Open', 'Close']))
    print('CHECKED', scene.name, count, 'frames', 'collisions', len(hits))
path = os.path.join(ART, 'six_motion_checks.json')
existing = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else []
by_name = {r['scene']: r for r in existing}
by_name.update({r['scene']: r for r in reports})
with open(path, 'w', encoding='utf-8') as handle:
    json.dump(list(by_name.values()), handle, indent=2)
failures = [r for r in reports if r['collisions']]
print('SIX_MOTION', sum(r['frames'] for r in reports), 'frames;', len(failures), 'failed scenes')
assert not failures, failures[:2]
