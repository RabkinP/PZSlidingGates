"""Export only wooden workbenches; never overwrite chain-link assets."""
import bpy
import os
import json
import struct

ART=r'E:\git\SlidingGates\art'
OUT=os.path.join(globals().get('EXPORT_ROOT',os.path.join(ART,'exports')),'wood');os.makedirs(OUT,exist_ok=True)
WIDTHS=globals().get('EXPORT_WIDTHS',(2,4))
previous=bpy.context.window.scene;count=0
for scene in bpy.data.scenes:
    if scene.get('sg_material')!='wood':continue
    rig=next(o for o in scene.objects if o.type=='ARMATURE')
    if rig['gate_width_cells'] not in WIDTHS:continue
    bpy.context.window.scene=scene
    rig=next(o for o in scene.objects if o.type=='ARMATURE');ad=rig.animation_data
    leaf=next(o for o in scene.objects if o.type=='MESH' and o.parent==rig)
    width=rig['gate_width_cells'];reverse=rig.get('gate_direction')=='reverse'
    model=('SG_Wood' if width==2 else f'SG_Wood_{width}')+('' if scene['sg_quality']=='high' else '_'+scene['sg_quality'].title())
    model+='_N_'+('Reverse' if reverse else 'Right')+(f"_Damage{scene['sg_damage']}" if scene['sg_damage'] else '')
    oldaction,oldslot=ad.action,ad.action_slot;mutes=[t.mute for t in ad.nla_tracks]
    def export(name,objects,animated):
        for o in scene.objects:o.select_set(False)
        for o in objects:o.select_set(True)
        bpy.context.view_layer.objects.active=objects[0]
        path=os.path.join(OUT,name+'.glb')
        bpy.ops.export_scene.gltf(filepath=path,use_selection=True,use_active_scene=True,
            export_animations=animated,export_animation_mode='NLA_TRACKS',export_anim_slide_to_zero=True)
        raw=open(path,'rb').read();doc=json.loads(raw[20:20+struct.unpack_from('<I',raw,12)[0]])
        assert len(doc['meshes'])==1 and len(doc['meshes'][0]['primitives'])==1
        assert [a['name'] for a in doc.get('animations',[])]==(['Open','Close'] if animated else [])
        attrs=doc['meshes'][0]['primitives'][0]['attributes']
        assert all(k in attrs for k in ('POSITION','NORMAL','TEXCOORD_0'))
        if animated:assert 'WEIGHTS_0' in attrs and 'JOINTS_0' in attrs
    try:
        ad.action=None
        for t in ad.nla_tracks:t.mute=False
        export(model,[rig,leaf],True);count+=1
        for obj in scene.objects:
            if not obj.get('export_static'):continue
            location=obj.location.copy();obj.location=(0,0,0)
            try:export('SG_Wood_'+obj['wood_static']+('_Reverse' if reverse else ''),[obj],False);count+=1
            finally:obj.location=location
    finally:
        ad.action=oldaction
        if oldslot:ad.action_slot=oldslot
        for t,m in zip(ad.nla_tracks,mutes):t.mute=m
        scene.frame_set(1)
bpy.context.window.scene=previous
print('WOOD_EXPORTED',count,'single-mesh GLBs')
