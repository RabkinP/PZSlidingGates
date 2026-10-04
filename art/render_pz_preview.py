"""Shader/projection diagnostic derived from PZ 42 installed code.

Uses PZ's ambient + one Lambert fill light, opaque albedo, 30 degree camera,
and native model pixel density. This is not the game's FBO/depth/postprocessing.
The main workbench and export materials remain unchanged.
"""
import bpy, math, os, ast, re
from mathutils import Vector

root=r'E:\git\SlidingGates\art'
workbench=bpy.context.scene
preview=bpy.data.scenes.get('SG_PZ_RenderPreview') or bpy.data.scenes.new('SG_PZ_RenderPreview')
collection=bpy.data.collections['SlidingGates']
if collection.name not in preview.collection.children:
    preview.collection.children.link(collection)
try:
    preview.render.engine='BLENDER_EEVEE'
except TypeError as error:
    raise RuntimeError('EEVEE preview unavailable') from error

def set_enum(owner,prop,identifier):
    valid=[item.identifier for item in owner.bl_rna.properties[prop].enum_items]
    if valid==['NONE']:
        # Some Blender colour-management enums are dynamic and RNA omits them.
        try:
            setattr(owner,prop,'__list_valid_values__')
        except TypeError as error:
            match=re.search(r'not found in (\(.+\))',str(error))
            if match: valid=list(ast.literal_eval(match.group(1)))
    assert identifier in valid,(prop,valid)
    setattr(owner,prop,identifier)

material=bpy.data.materials.get('SG_PZ_RenderPreview') or bpy.data.materials.new('SG_PZ_RenderPreview')
material.use_nodes=True
nodes=material.node_tree.nodes
nodes.clear()
links=material.node_tree.links
texture=nodes.new('ShaderNodeTexImage')
image=bpy.data.images.get('SG_PZ_PreviewAlbedo')
if image is None:
    image=bpy.data.images.load(os.path.join(root,'SG_ChainLink_Atlas.png'),check_existing=False)
    image.name='SG_PZ_PreviewAlbedo'
else:
    image.filepath=os.path.join(root,'SG_ChainLink_Atlas.png')
    image.reload()
image.colorspace_settings.name='Non-Color'
texture.image=image
geometry=nodes.new('ShaderNodeNewGeometry')
dot=nodes.new('ShaderNodeVectorMath')
set_enum(dot,'operation','DOT_PRODUCT')
links.new(geometry.outputs['Normal'],dot.inputs[0])
# MAKE_LEFT_HANDED maps Blender normals (x,y,z) into PZ (x,z,y).
# Shader.setLight receives (0,-2,5) and swaps Y/Z: PZ direction (0,5,-2).
dot.inputs[1].default_value=Vector((0,-2,5)).normalized()
positive=nodes.new('ShaderNodeMath'); set_enum(positive,'operation','MAXIMUM')
links.new(dot.outputs['Value'],positive.inputs[0]); positive.inputs[1].default_value=0
strength=nodes.new('ShaderNodeMath'); set_enum(strength,'operation','MULTIPLY')
links.new(positive.outputs[0],strength.inputs[0])
strength.inputs[1].default_value=0.375*(1-math.sqrt(29)/5000)
ambient=nodes.new('ShaderNodeMath'); set_enum(ambient,'operation','ADD')
links.new(strength.outputs[0],ambient.inputs[0]); ambient.inputs[1].default_value=1
lit=nodes.new('ShaderNodeMath'); set_enum(lit,'operation','MULTIPLY')
links.new(ambient.outputs[0],lit.inputs[0]); lit.inputs[1].default_value=0.70
clamp=nodes.new('ShaderNodeMath'); set_enum(clamp,'operation','MINIMUM')
links.new(lit.outputs[0],clamp.inputs[0]); clamp.inputs[1].default_value=1
colour=nodes.new('ShaderNodeVectorMath'); set_enum(colour,'operation','SCALE')
links.new(texture.outputs['Color'],colour.inputs[0]); links.new(clamp.outputs[0],colour.inputs['Scale'])
emission=nodes.new('ShaderNodeEmission')
links.new(colour.outputs['Vector'],emission.inputs['Color'])
output=nodes.new('ShaderNodeOutputMaterial')
links.new(emission.outputs[0],output.inputs['Surface'])
preview.view_layers[0].material_override=material
set_enum(preview.view_settings,'view_transform','Raw')
preview.view_settings.exposure=0
preview.view_settings.gamma=1
preview['ambient_assumption']=0.70
preview['limitations']='Uniform square light; no PZ chunk filtering/depth/cutaways. EEVEE rasterization differs.'

camera=bpy.data.objects.get('SG_PZ_DiagnosticCamera')
if camera is None:
    data=bpy.data.cameras.new('SG_PZ_DiagnosticCamera')
    camera=bpy.data.objects.new('SG_PZ_DiagnosticCamera',data)
    preview.collection.objects.link(camera)
target=Vector((1.8,0,0.95))
direction=Vector((math.cos(math.pi/6)/math.sqrt(2),-math.cos(math.pi/6)/math.sqrt(2),0.5))
camera.location=target+direction*10
camera.rotation_euler=direction.to_track_quat('Z','Y').to_euler()
set_enum(camera.data,'type','ORTHO')
# Core.scale * 1.5 * undoCoreScale(2/3) * 1920 = 128/sqrt(2).
camera.data.ortho_scale=480/(128/math.sqrt(2))
preview.camera=camera
preview.render.resolution_percentage=100
preview.render.image_settings.color_mode='RGBA'
set_enum(preview.render.image_settings,'file_format','PNG')
preview.render.film_transparent=True
for scale in (1,2):
    preview.render.resolution_x=480*scale
    preview.render.resolution_y=320*scale
    preview.render.filepath=os.path.join(root,'SG_PZ_Preview_'+str(scale)+'x.png')
    bpy.ops.render.render(scene=preview.name,write_still=True)
bpy.context.window.scene=workbench
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(root,'SG_ChainLink.blend'))
print('PZ diagnostic previews: native 480x320 and high-resolution 960x640')
