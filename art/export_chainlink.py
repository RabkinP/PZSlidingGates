"""Run in SG_ChainLink.blend via Blender MCP after build_chainlink.py."""
import bpy, os, math, json, struct
OUT=r'E:\git\SlidingGates\art\exports'
rig=globals().get('EXPORT_RIG') or next(o for o in bpy.context.scene.objects if o.type=='ARMATURE' and 'gate_width_cells' in o)
gate=globals().get('EXPORT_LEAF') or next(o for o in bpy.context.scene.objects if o.type=='MESH' and o.parent==rig)
WIDTH=int(rig.get('gate_width_cells',2))
PREFIX='SG_ChainLink' if WIDTH==2 else 'SG_ChainLink_'+str(WIDTH)
SAVE_PATH=globals().get('EXPORT_SAVE_PATH',r'E:\git\SlidingGates\art\SG_ChainLink.blend')
scene=bpy.context.scene
def export_selected(name,objects,animated):
    for obj in bpy.context.view_layer.objects: obj.select_set(False)
    for obj in objects: obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT,name+'.glb'),use_selection=True,
        use_active_scene=True,export_animations=animated,export_animation_mode='NLA_TRACKS',
        export_anim_slide_to_zero=True)
def flip():
    for track in rig.animation_data.nla_tracks:
        action=track.strips[0].action
        for slot in action.slots:
            for layer in action.layers:
                for strip in layer.strips:
                    bag=strip.channelbag(slot)
                    if bag:
                        for fc in bag.fcurves:
                            if fc.data_path.endswith('.location') and fc.array_index==0:
                                for key in fc.keyframe_points:
                                    key.co[1]*=-1; key.handle_left[1]*=-1; key.handle_right[1]*=-1
def mirror_leaf():
    # Mirroring the asymmetric tail is necessary as well as reversing travel.
    for vertex in gate.data.vertices: vertex.co.x=WIDTH-vertex.co.x
    for polygon in gate.data.polygons: polygon.flip()
    gate.data.update()
rig.animation_data.action=None
for track in rig.animation_data.nla_tracks: track.mute=False
rig.rotation_euler.z=0
export_selected(PREFIX+'_N_Right',[rig,gate],True)
flip(); mirror_leaf(); export_selected(PREFIX+'_N_Left',[rig,gate],True)
rig.rotation_euler.z=math.pi/2
export_selected(PREFIX+'_W_Left',[rig,gate],True)
flip(); mirror_leaf(); export_selected(PREFIX+'_W_Right',[rig,gate],True)
rig.rotation_euler.z=0
for objname,filename in ([] if WIDTH!=2 else [('SG_Post_Left','SG_CatcherPost'),('SG_Post_Right','SG_GuidePost'),('SG_Rail_OneCell','SG_Rail'),('SG_Drive','SG_Drive')]):
    obj=bpy.data.objects[objname]; location=obj.location.copy(); obj.location=(0,0,0)
    export_selected(filename,[obj],False); obj.location=location
for track in rig.animation_data.nla_tracks: track.mute=True
rig.animation_data.action=rig.animation_data.nla_tracks[0].strips[0].action
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=SAVE_PATH)
for filename in sorted(os.listdir(OUT)):
    if filename.endswith('.glb'):
        raw=open(os.path.join(OUT,filename),'rb').read()
        doc=json.loads(raw[20:20+struct.unpack_from('<I',raw,12)[0]])
        names=[n.get('name') for n in doc['nodes']]
        assert 'Cube' not in names
        clips=[a['name'] for a in doc.get('animations',[])]
        if 'ChainLink' in filename: assert clips==['Open','Close'] and 'DoorBone' in names
        print(filename, names, clips)
