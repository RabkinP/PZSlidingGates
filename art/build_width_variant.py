"""Run through Blender MCP in the existing source file.

Set GATE_WIDTH (default 4). Keeps the two-cell scene; builds a separate scene
in the same .blend and exports width-specific leaves, reusing static assets.
"""
import bpy, os, math
from mathutils import Vector
from mathutils.bvhtree import BVHTree

root=r'E:\git\SlidingGates\art'
width=int(globals().get('GATE_WIDTH',4))
assert width>=2
name='SG_ChainLink_'+str(width)+'_Workbench'
assert bpy.data.filepath==os.path.join(root,'SG_ChainLink.blend'), 'Open the source project first'
assert name not in bpy.data.scenes, 'Variant already exists; edit it instead of rebuilding blindly'
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(root,'SG_ChainLink_before_width_'+str(width)+'.blend'),copy=True)
scene=bpy.data.scenes.new(name)
bpy.context.window.scene=scene
env={'GATE_WIDTH':width,'GATE_SAVE_PATH':os.path.join(root,'SG_ChainLink.blend')}
exec(compile(open(os.path.join(root,'build_chainlink.py'),encoding='utf-8').read(),'build_chainlink.py','exec'),env)
rig,gate=env['rig'],env['gate']
for obj in env['col'].objects:
    obj.name='SG_'+str(width)+'_'+obj.name.removeprefix('SG_')
env['col'].name='SlidingGates_'+str(width)
scene['SG_notes']=f'{width}-cell leaf and stroke; fixed clearance 0.18; duration {width*1.5:g} seconds; separate variant scene.'
xs=[v.co.x for v in gate.data.vertices]
assert min(xs)>=-1e-6 and max(xs)<=width+1e-6
for track in rig.animation_data.nla_tracks:
    rig.animation_data.action=track.strips[0].action
    for frame in range(scene.frame_start,scene.frame_end+1):
        scene.frame_set(frame)
        loc=rig.pose.bones['DoorBone'].location
        assert abs(loc.y)<1e-6 and abs(loc.z)<1e-6
        assert any(loc.x+0.047<=x<=loc.x+width-0.047 for x in (width-0.12,width+0.12))
    print(track.name,scene.frame_end-scene.frame_start+1,'frames validated; stroke',width)
def tree(obj):
    return BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],[list(p.vertices) for p in obj.data.polygons])
assert not tree(env['motor_obj']).overlap(tree(env['post_b']))
env.update(EXPORT_RIG=rig,EXPORT_LEAF=gate,EXPORT_SAVE_PATH=os.path.join(root,'SG_ChainLink.blend'))
exec(compile(open(os.path.join(root,'export_chainlink.py'),encoding='utf-8').read(),'export_chainlink.py','exec'),env)
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_location=Vector((width,0,1))
        area.spaces.active.region_3d.view_distance=width*2.5
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(root,'SG_ChainLink.blend'))
print('WIDTH_VARIANT',width,'bounds',min(xs),max(xs),'drive/post clear; scene',scene.name)
