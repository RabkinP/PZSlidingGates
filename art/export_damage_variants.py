"""Run via Blender MCP. Export damaged leaves to art/exports/damage only.

W orientation will reuse these assets through spriteModel rotation, like the
current registered gates. Gameplay registration is intentionally a separate step.
"""
import bpy
import os
import json
import struct

ART=r'E:\git\SlidingGates\art'
OUT=os.path.join(globals().get('EXPORT_ROOT',os.path.join(ART,'exports')),'damage')
WIDTHS=globals().get('EXPORT_WIDTHS',(2,4))
os.makedirs(OUT,exist_ok=True)
previous=bpy.context.window.scene
for scene in bpy.data.scenes:
    if scene.get('sg_material') == 'wood' or not scene.get('sg_damage'):continue
    rig=next(o for o in scene.objects if o.type=='ARMATURE')
    if rig['gate_width_cells'] not in WIDTHS:continue
    bpy.context.window.scene=scene
    rig=next(o for o in scene.objects if o.type=='ARMATURE' and o.get('gate_width_cells'))
    leaf=next(o for o in scene.objects if o.type=='MESH' and o.parent==rig)
    ad=rig.animation_data
    action,slot=ad.action,ad.action_slot
    mutes=[t.mute for t in ad.nla_tracks]
    frame=scene.frame_current
    prefix='SG_ChainLink' if rig['gate_width_cells']==2 else f"SG_ChainLink_{rig['gate_width_cells']}"
    filename=prefix+('' if scene['sg_quality']=='high' else '_'+scene['sg_quality'].title())+'_N_'+('Reverse' if rig.get('gate_direction')=='reverse' else 'Right')+'_Damage'+str(scene['sg_damage'])+'.glb'
    path=os.path.join(OUT,filename)
    try:
        ad.action=None
        for track in ad.nla_tracks:track.mute=False
        for obj in scene.objects:obj.select_set(False)
        rig.select_set(True);leaf.select_set(True)
        bpy.context.view_layer.objects.active=rig
        bpy.ops.export_scene.gltf(filepath=path,use_selection=True,use_active_scene=True,
            export_animations=True,export_animation_mode='NLA_TRACKS',export_anim_slide_to_zero=True)
        raw=open(path,'rb').read();doc=json.loads(raw[20:20+struct.unpack_from('<I',raw,12)[0]])
        assert [a['name'] for a in doc['animations']]==['Open','Close']
        assert len(doc['meshes'])==1 and len(doc['skins'])==1
        assert len(doc['meshes'][0]['primitives'])==1
        assert 'DoorBone' in [n.get('name') for n in doc['nodes']]
        attrs=doc['meshes'][0]['primitives'][0]['attributes']
        assert all(k in attrs for k in ('POSITION','NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0'))
        print('DAMAGE_EXPORT',filename,'Open/Close, single skinned mesh, normals/UV/weights')
    finally:
        ad.action=action
        if slot:ad.action_slot=slot
        for track,mute in zip(ad.nla_tracks,mutes):track.mute=mute
        scene.frame_set(frame)
bpy.context.window.scene=previous
