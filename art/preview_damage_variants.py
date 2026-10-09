"""Non-export comparison scene: Low, Medium, High viewed from outward face."""
import bpy
import math
import os
from mathutils import Vector, Quaternion

ART=r'E:\git\SlidingGates\art'
assert 'SG_Damage_Comparison' not in bpy.data.scenes
scene=bpy.data.scenes.new('SG_Damage_Comparison')
bpy.context.window.scene=scene
for label,offset,source_name in [('INTACT',8.1,'SG_ChainLink_Workbench'),
                                 ('DAMAGE 1',5.4,'SG_ChainLink_Damage1_Workbench'),
                                 ('DAMAGE 2',2.7,'SG_ChainLink_Damage2_Workbench'),
                                 ('DAMAGE 3',0,'SG_ChainLink_Damage3_Workbench')]:
    source=bpy.data.scenes[source_name]
    clones={}
    for obj in source.objects:
        if not obj.name.startswith('SG_') or obj.type not in ('MESH','ARMATURE'):continue
        # Only one ground rail: extra pocket lengths obscure the comparison.
        if 'Rail_Preview' in obj.name:continue
        clone=obj.copy();clone.name='Compare_'+label+'_'+obj.name
        scene.collection.objects.link(clone);clones[obj]=clone
    for obj,clone in clones.items():
        if obj.parent in clones:
            clone.parent=clones[obj.parent]
            for mod in clone.modifiers:
                if mod.type=='ARMATURE':mod.object=clone.parent
        else:clone.location.x+=offset
    text=bpy.data.curves.new('Label_'+label,'FONT');text.body=label;text.align_x='CENTER';text.size=.19
    obj=bpy.data.objects.new('Label_'+label,text);scene.collection.objects.link(obj)
    obj.location=(offset+1,.25,2.30);obj.rotation_euler=(math.pi/2,0,math.pi)
    mat=bpy.data.materials.get('SG_Quality_Label')
    if mat is None:
        mat=bpy.data.materials.new('SG_Quality_Label');mat.use_nodes=True
        bsdf=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        bsdf.inputs['Base Color'].default_value=(.85,.9,.88,1)
        bsdf.inputs['Emission Color'].default_value=(.85,.9,.88,1)
        bsdf.inputs['Emission Strength'].default_value=.5
    text.materials.append(mat)
world=bpy.data.worlds.new('SG_Damage_Comparison_World');world.use_nodes=True
next(n for n in world.node_tree.nodes if n.type=='BACKGROUND').inputs['Color'].default_value=(.10,.12,.13,1)
scene.world=world
for name,pos,power,size in [('Key',(4,5,7),1800,8),('Fill',(1,-3,4),900,6)]:
    data=bpy.data.lights.new('Quality_'+name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    obj=bpy.data.objects.new('Quality_'+name,data);scene.collection.objects.link(obj);obj.location=pos
    obj.rotation_euler=(Vector((3.7,0,1))-obj.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('SG_Damage_Camera');data.type='ORTHO';data.ortho_scale=10.9
camera=bpy.data.objects.new('SG_Damage_Camera',data);scene.collection.objects.link(camera)
target=Vector((5.05,0,1.13));camera.location=target+Vector((0,12,2.5))
camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();scene.camera=camera
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=2000;scene.render.resolution_y=600
scene.render.resolution_percentage=100;scene.frame_set(1)
scene.render.filepath=os.path.join(ART,'SG_Damage_Comparison.png')
scene.render.image_settings.file_format='PNG'
scene['SG_notes']='Art comparison only; outward-facing view. Not a game rendering verification.'
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART,'SG_ChainLink.blend'))
bpy.ops.render.render(write_still=True)
