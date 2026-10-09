"""Blender full-frame rigid travel/clearance checks; does not establish gameplay appearance."""
import bpy
import json
import os
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ART=r'E:\git\SlidingGates\art'
previous=bpy.context.window.scene
reports=json.load(open(os.path.join(ART,'damage_checks.json')))
for report in reports:
    scene=bpy.data.scenes[report['scene']];bpy.context.window.scene=scene
    rig=next(o for o in scene.objects if o.type=='ARMATURE' and o.get('gate_width_cells'))
    leaf=next(o for o in scene.objects if o.type=='MESH' and o.parent==rig)
    ad=rig.animation_data;action,slot=ad.action,ad.action_slot;mutes=[t.mute for t in ad.nla_tracks]
    frame=scene.frame_current
    def tree(obj,verts=None):
        return BVHTree.FromPolygons(verts or [obj.matrix_world@v.co for v in obj.data.vertices],
                                   [list(p.vertices) for p in obj.data.polygons])
    try:
        scene.frame_set(1);bpy.context.view_layer.update()
        fixed=[(o.name,[o.matrix_world@v.co for v in o.data.vertices],
                [list(p.vertices) for p in o.data.polygons])
               for o in scene.objects if o.type=='MESH' and o!=leaf]
        group=leaf.vertex_groups['DoorBone'].index
        assert all(any(g.group==group and abs(g.weight-1)<1e-6 for g in v.groups) for v in leaf.data.vertices)
        checked=0
        for track in ad.nla_tracks:
            for t in ad.nla_tracks:t.mute=True
            ad.action=track.strips[0].action;ad.action_slot=track.strips[0].action_slot
            scene.frame_set(1)
            base_loc=rig.pose.bones['DoorBone'].location.copy()
            e=leaf.evaluated_get(bpy.context.evaluated_depsgraph_get())
            base_vertices=[e.matrix_world@v.co for v in e.data.vertices]
            moving=tree(leaf,base_vertices)
            for f in range(1,scene.frame_end+1):
                scene.frame_set(f)
                loc=rig.pose.bones['DoorBone'].location
                assert abs(loc.y)<1e-6 and abs(loc.z)<1e-6
                shift=(-1 if report['reverse'] else 1)*loc.x
                width=report['width']
                assert -1e-5<=shift<=width+1e-5
                assert any(shift+.047<=x<=shift+width-.047 for x in (width-.12,width+.12))
                e=leaf.evaluated_get(bpy.context.evaluated_depsgraph_get())
                offset=rig.matrix_world.to_3x3()@(loc-base_loc)
                for index in (0,len(base_vertices)//2,len(base_vertices)-1):
                    assert ((e.matrix_world@e.data.vertices[index].co)-(base_vertices[index]+offset)).length<1e-5
                # Rigid leaf: translate the much smaller fixed meshes into its
                # reference pose rather than rebuilding its large BVH per frame.
                for name,vertices,polygons in fixed:
                    t=BVHTree.FromPolygons([v-offset for v in vertices],polygons)
                    assert not moving.overlap(t),(scene.name,track.name,f,name)
                checked+=1
        report.update(frames_checked=checked,surface_collisions=0,rail_capture=True)
        json.dump(reports,open(os.path.join(ART,'damage_checks.json'),'w'),indent=2)
        print('PASS',scene.name,checked,'frames')
    finally:
        ad.action=action
        if slot:ad.action_slot=slot
        for track,mute in zip(ad.nla_tracks,mutes):track.mute=mute
        scene.frame_set(frame)
bpy.context.window.scene=previous
json.dump(reports,open(os.path.join(ART,'damage_checks.json'),'w'),indent=2)
print('DAMAGE_FULL_FRAME_CHECKS',sum(r['frames_checked'] for r in reports))
