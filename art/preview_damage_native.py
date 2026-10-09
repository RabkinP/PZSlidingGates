"""Native-density isometric comparison using the maintained approximate door shader.

Separate diagnostic meshes/materials; no game exports. Not a gameplay screenshot.
"""
import bpy
import math
import os
from mathutils import Vector

ART=r'E:\git\SlidingGates\art'
name='SG_Damage_Native_Comparison'
scene=bpy.data.scenes.get(name)
if scene:
    for obj in list(scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
    bpy.data.scenes.remove(scene)
scene=bpy.data.scenes.new(name)
scene.render.engine='BLENDER_EEVEE';scene.view_settings.view_transform='Raw'
scene.view_settings.exposure=0;scene.view_settings.gamma=1
world=bpy.data.worlds.new(name+'_World');world.use_nodes=True
next(n for n in world.node_tree.nodes if n.type=='BACKGROUND').inputs['Color'].default_value=(.025,.035,.035,1)
scene.world=world
mat=bpy.data.materials['SG_PZ_RenderPreview']
right=Vector((-1,1,0)).normalized()
for stage in (0,1,2,3):
    source=bpy.data.scenes['SG_ChainLink'+(f'_Damage{stage}' if stage else '')+'_Workbench']
    offset=right*(stage*3.5);clones={}
    rig=next(o for o in source.objects if o.type=='ARMATURE' and o.get('gate_width_cells'))
    for obj in source.objects:
        if obj!=rig and not (obj.type=='MESH' and obj.name.startswith('SG_')):continue
        if 'Rail_Preview' in obj.name:continue
        clone=obj.copy();clone.name=f'Diagnostic_Damage{stage}_'+obj.name
        if obj.type=='MESH':
            clone.data=obj.data.copy();clone.data.materials.clear();clone.data.materials.append(mat)
        scene.collection.objects.link(clone);clones[obj]=clone
    for obj,clone in clones.items():
        if obj.parent in clones:
            clone.parent=clones[obj.parent]
            for mod in clone.modifiers:
                if mod.type=='ARMATURE':mod.object=clone.parent
        else:clone.location+=offset
data=bpy.data.cameras.new(name+'_Camera');data.type='ORTHO'
camera=bpy.data.objects.new(name+'_Camera',data);scene.collection.objects.link(camera)
target=Vector((1,0,.98))+right*5.25
direction=Vector((math.cos(math.pi/6)/math.sqrt(2),math.cos(math.pi/6)/math.sqrt(2),.5))
camera.location=target+direction*10;camera.rotation_euler=direction.to_track_quat('Z','Y').to_euler()
data.ortho_scale=1280/(128/math.sqrt(2));scene.camera=camera
labelmat=bpy.data.materials.new(name+'_Labels');labelmat.use_nodes=True
nodes=labelmat.node_tree.nodes;nodes.clear()
emission=nodes.new('ShaderNodeEmission');emission.inputs['Color'].default_value=(.8,.85,.85,1)
output=nodes.new('ShaderNodeOutputMaterial');labelmat.node_tree.links.new(emission.outputs[0],output.inputs['Surface'])
for stage,label in enumerate(('INTACT','DAMAGE 1','DAMAGE 2','DAMAGE 3')):
    text=bpy.data.curves.new(name+'_Label'+str(stage),'FONT');text.body=label;text.align_x='CENTER';text.size=.14
    text.materials.append(labelmat)
    obj=bpy.data.objects.new(name+'_Label'+str(stage),text);scene.collection.objects.link(obj)
    obj.location=Vector((1,0,2.25))+right*(stage*3.5);obj.rotation_euler=camera.rotation_euler
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
scene.render.image_settings.color_mode='RGBA';scene.frame_set(1)
for scale in (1,2):
    scene.render.resolution_x=1280*scale;scene.render.resolution_y=280*scale
    scene.render.filepath=os.path.join(ART,f'SG_Damage_Native_{scale}x.png')
    bpy.ops.render.render(scene=scene.name,write_still=True)
scene['limitations']='Approximate door shader, uniform square light, no chunk filtering/cutaways or gameplay verification.'
bpy.context.window.scene=scene
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART,'SG_ChainLink.blend'))
print('Native 1x and high-resolution 2x isometric damage comparison; left to right stages 0/1/2/3')
