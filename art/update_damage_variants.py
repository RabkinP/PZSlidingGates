"""Rebuild only owned damage leaf meshes from pristine quality workbenches."""
import bpy
import bmesh
import math
import hashlib
import json
import os
from mathutils import Vector

ART=r'E:\git\SlidingGates\art'
assert bpy.data.filepath==os.path.join(ART,'SG_ChainLink.blend')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART,'SG_ChainLink_before_damage_readability.blend'),copy=True)
code=open(os.path.join(ART,'build_damage_variants.py'),encoding='utf-8').read()
exec(code[code.index('def fingerprint'):code.index('reports=[]')])
reports=[]
for scene in bpy.data.scenes:
    if not scene.get('sg_damage'):continue
    stage=int(scene['sg_damage']);source=bpy.data.scenes[scene.name.replace('_Damage'+str(stage),'')]
    original_rig=next(o for o in source.objects if o.type=='ARMATURE' and o.get('gate_width_cells'))
    original_leaf=next(o for o in source.objects if o.type=='MESH' and o.parent==original_rig)
    rig=next(o for o in scene.objects if o.type=='ARMATURE' and o.get('gate_width_cells'))
    leaf=next(o for o in scene.objects if o.type=='MESH' and o.parent==rig)
    width=int(rig['gate_width_cells']);reverse=rig.get('gate_direction')=='reverse'
    before=fingerprint(original_leaf.data);old=leaf.data
    leaf.data,report=damage_mesh(original_leaf.data,width,reverse,stage)
    # Keep the existing comparison objects attached to the revised mesh.
    for obj in bpy.data.objects:
        if obj.type=='MESH' and obj.data==old and obj.name.startswith('Compare_'):obj.data=leaf.data
    group=leaf.vertex_groups.get('DoorBone') or leaf.vertex_groups.new(name='DoorBone')
    group.add(list(range(len(leaf.data.vertices))),1,'REPLACE')
    for obj in bpy.data.objects:
        if obj.type=='MESH' and obj.data==leaf.data:
            g=obj.vertex_groups.get('DoorBone') or obj.vertex_groups.new(name='DoorBone')
            g.add(list(range(len(leaf.data.vertices))),1,'REPLACE')
    assert fingerprint(original_leaf.data)==before
    report.update(scene=scene.name,width=width,reverse=reverse,quality=scene['sg_quality'],stage=stage,
                  source_sha256=before,vertices=len(leaf.data.vertices),readability_revision=2)
    reports.append(report)
json.dump(reports,open(os.path.join(ART,'damage_checks.json'),'w'),indent=2)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART,'SG_ChainLink.blend'))
print('Updated 36 damage leaves; original quality geometry unchanged')
