"""Approximate PZ orthographic framing; game lighting remains authoritative."""
import bpy
from mathutils import Vector

target=Vector((1.8,0,0.95))
direction=Vector((6,-6,4.9))
rotation=direction.to_track_quat('Z','Y')
camera=bpy.data.objects.get('SG_PreviewCamera')
if camera is None:
    data=bpy.data.cameras.new('SG_PreviewCamera')
    camera=bpy.data.objects.new('SG_PreviewCamera',data)
    bpy.data.collections['SlidingGates'].objects.link(camera)
camera.location=target+direction
camera.rotation_euler=rotation.to_euler()
camera.data.type='ORTHO'
camera.data.ortho_scale=5.0
bpy.context.scene.camera=camera
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        space=area.spaces.active
        space.region_3d.view_rotation=rotation
        space.region_3d.view_location=target
        space.region_3d.view_distance=5.0
        space.region_3d.view_perspective='ORTHO'
        space.shading.type='SOLID'
        space.shading.color_type='TEXTURE'
        space.overlay.show_overlays=False
bpy.ops.wm.save_as_mainfile(filepath=r'E:\git\SlidingGates\art\SG_ChainLink.blend')
