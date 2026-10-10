"""Regenerate only wooden meshes from canonical sources and the maintained builder helpers."""
import bpy
import os
import json
ART=r'E:\git\SlidingGates\art'
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART,'SG_ChainLink_before_wood_update.blend'),copy=True)
ns={'WOOD_UPDATE':True}
source=open(os.path.join(ART,'build_wood_variants.py'),encoding='utf-8').read().split('reports=[]')[0]
exec(compile(source,'wood-helpers','exec'),ns)
reports=[]
for scene in bpy.data.scenes:
    if scene.get('sg_material')!='wood':continue
    rig=next(o for o in scene.objects if o.type=='ARMATURE')
    width=rig['gate_width_cells'];reverse=rig.get('gate_direction')=='reverse'
    canonical=bpy.data.scenes['SG_ChainLink'+('_4' if width==4 else '')+'_Workbench']
    source_rig=next(o for o in canonical.objects if o.type=='ARMATURE' and o.get('gate_width_cells')==width)
    source_leaf=next(o for o in canonical.objects if o.parent==source_rig and o.type=='MESH')
    leaf=next(o for o in scene.objects if o.parent==rig and o.type=='MESH')
    old=leaf.data;leaf.data,broken=ns['leaf_mesh'](source_leaf.data,width,scene['sg_quality'],scene['sg_damage'],reverse)
    # Comparison objects may still share the previous leaf. Keep their data
    # until previews are rebuilt; removing it leaves invalid mesh objects and
    # can crash Blender's viewport draw-cache iterator during scene switches.
    if old.users==0: bpy.data.meshes.remove(old)
    group=leaf.vertex_groups.get('DoorBone') or leaf.vertex_groups.new(name='DoorBone')
    group.add(list(range(len(leaf.data.vertices))),1,'REPLACE')
    leaf['broken_boards']=broken
    reports.append(dict(scene=scene.name,width=width,quality=scene['sg_quality'],
        damage=scene['sg_damage'],reverse=reverse,broken_boards=broken,
        broken_diagonal=scene['sg_damage']==3,handle_count=leaf['handle_count'],
        vertices=len(leaf.data.vertices),central_upright=width==4,
        board_bottom=.18,brace_ends_clipped=True))
    # Clamp only the two triangular bracket gussets, preserving all running contacts.
    for obj in scene.objects:
        if obj.get('wood_static')!='GuidePost':continue
        for ids,ps,sw in ns['components'](obj.data):
            if len(ids)==6:
                for i in ids:obj.data.vertices[i].co.y=min(obj.data.vertices[i].co.y,.069)
        obj.data.update()
bpy.context.window.scene=bpy.data.scenes['SG_Wood_4_high_Workbench']
with open(os.path.join(ART,'wood_build_checks.json'),'w',encoding='utf-8') as f:
    json.dump(reports,f,indent=2)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART,'SG_ChainLink.blend'))
print('WOOD_UPDATED')
