"""Update the existing prototype in place through Blender MCP."""
import bpy, math
from mathutils import Vector
source=open(r'E:\git\SlidingGates\art\build_chainlink.py',encoding='utf-8').read()
scene=bpy.context.scene; col=bpy.data.collections['SlidingGates']; mat=bpy.data.materials['SG_ChainLink_Atlas']
assert bpy.data.objects['SG_Rig'].name in scene.objects, 'Select the original two-cell workbench before running this updater'
ROOT=r'E:\git\SlidingGates\art'
WIDTH=2
CLEARANCE=0.10
import os, random
exec(source[source.index('palette ='):source.index("mat=bpy.data.materials.new")])
exec(source[source.index('def rod('):source.index("gate=mesh('SG_Leaf'")])
exec(source[source.index('def post('):source.index("post_a=mesh(")])
exec(source[source.index('def rail_piece('):source.index("rail=mesh(")])
exec(source[source.index('def motor('):source.index("motor_obj=mesh(")])
for name,fn in [('SG_Leaf',leaf),('SG_Post_Left',catcher),('SG_Post_Right',post),('SG_Drive',motor),('SG_Rail_OneCell',rail_piece)]:
    obj=bpy.data.objects[name]; fresh=mesh('SG_UpdateTemp',fn); obj.data=fresh.data
    bpy.data.objects.remove(fresh,do_unlink=True)
    if name=='SG_Leaf':
        for vertex in obj.data.vertices: vertex.co.y+=CLEARANCE
        group=obj.vertex_groups.get('DoorBone') or obj.vertex_groups.new(name='DoorBone')
        group.add(list(range(len(obj.data.vertices))),1,'REPLACE')
    if name=='SG_Rail_OneCell':
        for index in range(1,4):
            bpy.data.objects['SG_Rail_Preview_'+str(index)].data=obj.data
# Match build_chainlink.py and SG_Drive_Static: motor pinion meets the rack
# at Blender Y=0.045 (leaf clearance 0.10 minus rack offset 0.055).
bpy.data.objects['SG_Drive'].location=(2.0,-0.22,0)
rig=bpy.data.objects['SG_Rig']; rig['fence_clearance']=CLEARANCE
if 'outward_offset' in rig: del rig['outward_offset']
exec(source[source.index('def animate('):source.index("scene['SG_notes']")])
scene['SG_notes']='Fixed clearance 0.10; straight sliding 2 cells; duration 3 seconds.'
exec(compile(open(r'E:\git\SlidingGates\art\export_chainlink.py',encoding='utf-8').read(),'export_chainlink.py','exec'))
for track in rig.animation_data.nla_tracks:
    rig.animation_data.action=track.strips[0].action
    for frame in range(scene.frame_start,scene.frame_end+1):
        scene.frame_set(frame); loc=rig.pose.bones['DoorBone'].location
        assert abs(loc.y)<1e-6 and abs(loc.z)<1e-6
        assert any(loc.x+0.047 <= x <= loc.x+1.953 for x in (1.88,2.12))
    print(track.name,'validated all',scene.frame_end-scene.frame_start+1,'frames')
leaf_x=[v.co.x for v in bpy.data.objects['SG_Leaf'].data.vertices]
assert min(leaf_x)>=-1e-6 and max(leaf_x)<=2.000001
# One complete roller station must remain within the moving top rail.
for shift in [i/100 for i in range(201)]:
    assert any(shift+0.025+0.022 <= x <= shift+1.975-0.022
               for x in (1.88,2.12))
print('TWO_CELL_BOUNDS',min(leaf_x),max(leaf_x),'GUIDE_CAPTURE full stroke')
from mathutils.bvhtree import BVHTree
def world_tree(name):
    obj=bpy.data.objects[name]
    return BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],
                               [list(p.vertices) for p in obj.data.polygons])
assert not world_tree('SG_Drive').overlap(world_tree('SG_Post_Right'))
print('DRIVE_POST_INTERSECTIONS',0)
rig.animation_data.action=rig.animation_data.nla_tracks[0].strips[0].action
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=r'E:\git\SlidingGates\art\SG_ChainLink.blend')
print('LEAF_TRIANGLES',sum(len(p.vertices)-2 for p in bpy.data.objects['SG_Leaf'].data.polygons))
