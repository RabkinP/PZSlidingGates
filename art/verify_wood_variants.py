"""Live Blender verification of every frame/clip against static assembly surfaces."""
import bpy
import json
import os
from mathutils.bvhtree import BVHTree

ART=r'E:\git\SlidingGates\art'
reports=[];failures=[]
for scene in bpy.data.scenes:
    if scene.get('sg_material')!='wood':continue
    bpy.context.window.scene=scene
    rig=next(o for o in scene.objects if o.type=='ARMATURE')
    leaf=next(o for o in scene.objects if o.type=='MESH' and o.parent==rig)
    width=rig['gate_width_cells'];reverse=rig.get('gate_direction')=='reverse'
    def tree(obj,coords=None):
        return BVHTree.FromPolygons(coords if coords is not None else [obj.matrix_world@v.co for v in obj.data.vertices],
                                   [tuple(p.vertices) for p in obj.data.polygons])
    bpy.context.view_layer.update()
    fixed=[(o.name,tree(o)) for o in scene.objects if o.type=='MESH' and o!=leaf]
    ad=rig.animation_data;oldaction,oldslot=ad.action,ad.action_slot
    mutes=[t.mute for t in ad.nla_tracks];count=0;hits=[]
    for t in ad.nla_tracks:t.mute=True
    for track in ad.nla_tracks:
        ad.action=track.strips[0].action;ad.action_slot=track.strips[0].action_slot
        for frame in range(1,scene.frame_end+1):
            scene.frame_set(frame);loc=rig.pose.bones['DoorBone'].location
            assert abs(loc.y)<1e-6 and abs(loc.z)<1e-6
            shift=loc.x*(-1 if reverse else 1)
            assert -1e-5<=shift<=width+1e-5
            assert any(shift+.047<=x<=shift+width-.047 for x in (width-.12,width+.12))
            e=leaf.evaluated_get(bpy.context.evaluated_depsgraph_get())
            moving=tree(leaf,[e.matrix_world@v.co for v in e.data.vertices])
            for name,t in fixed:
                overlap=moving.overlap(t)
                if overlap and not any(h['part']==name for h in hits):
                    hits.append(dict(part=name,clip=track.name,frame=frame,faces=overlap[:6]))
            count+=1
    ad.action=oldaction
    if oldslot:ad.action_slot=oldslot
    for t,mute in zip(ad.nla_tracks,mutes):t.mute=mute
    scene.frame_set(1)
    report=dict(scene=scene.name,frames=count,collisions=hits,rail_capture=True,rigid_weights=True)
    reports.append(report)
    if hits:failures.append(report)
with open(os.path.join(ART,'wood_motion_checks.json'),'w',encoding='utf-8') as f:json.dump(reports,f,indent=2)
print('WOOD_MOTION',sum(r['frames'] for r in reports),'frames;',len(failures),'failed scenes')
print(json.dumps(failures[:3]))
assert not failures,'See wood_motion_checks.json: intersections require fixing'
