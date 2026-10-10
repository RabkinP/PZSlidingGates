"""Blender art comparisons and build-menu icons; not a PZ rendering proof."""
import bpy
import math
import os
from mathutils import Vector

ART=r'E:\git\SlidingGates\art'
def setup(name,width,height):
    old=bpy.data.scenes.get(name)
    if old:bpy.data.scenes.remove(old)
    s=bpy.data.scenes.new(name);bpy.context.window.scene=s
    s.render.engine='BLENDER_EEVEE';s.render.resolution_x=width;s.render.resolution_y=height;s.render.resolution_percentage=100
    s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA'
    s.render.film_transparent=True
    s.world=bpy.data.worlds.new(name+'_World');s.world.use_nodes=True
    bg=next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(.3,.3,.3,1);bg.inputs['Strength'].default_value=.65
    for location,power,size in [((2,5,6),900,7),((6,-4,5),600,5)]:
        data=bpy.data.lights.new(name+'_Light','AREA');data.energy=power;data.shape='DISK';data.size=size
        obj=bpy.data.objects.new(name+'_Light',data);s.collection.objects.link(obj);obj.location=location
        obj.rotation_euler=(Vector((2,0,1))-obj.location).to_track_quat('-Z','Y').to_euler()
    camera=bpy.data.objects.new(name+'_Camera',bpy.data.cameras.new(name+'_Camera'));s.collection.objects.link(camera);s.camera=camera;camera.data.type='ORTHO'
    return s,camera
def assembly(target,source,dx):
    for obj in source.objects:
        if obj.type!='MESH':continue
        clone=obj.copy();clone.data=obj.data;clone.parent=None;clone.modifiers.clear();clone.location=obj.location.copy()+Vector((dx,0,0))
        target.collection.objects.link(clone)
def render(s,camera,center,scale,path,angle=True,back=False):
    camera.location=Vector(center)+Vector((1.5 if angle else 0,-12 if back else 12,4 if angle else 1.8))
    camera.rotation_euler=(Vector(center)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
    s.render.filepath=path;bpy.ops.render.render(write_still=True)
for name,variants in [('Quality',[('low',0),('medium',0),('high',0)]),('Damage',[('high',i) for i in range(4)])]:
    s,camera=setup('SG_Wood_'+name+'_Comparison',len(variants)*420,450)
    for i,(q,d) in enumerate(variants):
        source=bpy.data.scenes[f'SG_Wood_2_{q}'+(f'_Damage{d}' if d else '')+'_Workbench']
        # Camera is on the outward face; +X appears left in this view.
        assembly(s,source,(len(variants)-1-i)*2.7)
    render(s,camera,((len(variants)-1)*1.35+1,0,1),len(variants)*2.8,os.path.join(ART,f'wood_{name.lower()}_comparison.png'),False)
s,camera=setup('SG_Wood_Damage_Back_Comparison',1680,450)
for damage in range(4):
    source=bpy.data.scenes['SG_Wood_2_high'+(f'_Damage{damage}' if damage else '')+'_Workbench']
    assembly(s,source,damage*2.7)
render(s,camera,(5.05,0,1),11.2,os.path.join(ART,'wood_damage_back_comparison.png'),False,True)
for width in (2,4):
    s,camera=setup(f'SG_Wood_Icon{width}',256,256)
    assembly(s,bpy.data.scenes[f'SG_Wood_{width}_high_Workbench'],0)
    render(s,camera,(width/2,0,1),width+1.1,
        os.path.join(ART,'..','mod','SlidingGates','42','media','textures',f'SG_BuildWood{width}.png'))
s,camera=setup('SG_Wood_4_Frame_Comparison',1400,700)
assembly(s,bpy.data.scenes['SG_Wood_4_medium_Workbench'],0)
render(s,camera,(2,0,1),5.1,os.path.join(ART,'wood_4_frame_back.png'),False,True)
bpy.context.window.scene=bpy.data.scenes['SG_Wood_4_high_Workbench']
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART,'SG_ChainLink.blend'))
print('WOOD_PREVIEWS_SAVED')
