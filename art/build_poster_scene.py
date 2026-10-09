"""Run in the existing Blender MCP. Creates a separate, editable poster file.

Uses copies of the finished four-cell assembly; never rebuilds game geometry.
"""
import bpy, math, random
from mathutils import Vector
from pathlib import Path

ROOT = Path(r'E:\git\SlidingGates\art')
OUT = ROOT / 'poster'
OUT.mkdir(exist_ok=True)
assert 'SG_Poster' not in bpy.data.scenes, 'Poster already exists; edit it in place.'
source = bpy.data.scenes.get('SG_ChainLink_4_Workbench')
if source is None:
    with bpy.data.libraries.load(str(ROOT/'SG_ChainLink.blend'), link=False) as (src, dst):
        dst.scenes = ['SG_ChainLink_4_Workbench']
    source = dst.scenes[0]
scene = bpy.data.scenes.new('SG_Poster')
bpy.context.window.scene = scene
collections = {}
for name in ('Gate assembly', 'Fence', 'Ground', 'Details', 'Lighting'):
    col = bpy.data.collections.new('Poster / '+name)
    scene.collection.children.link(col)
    collections[name] = col

def material(name, color, roughness=.8, metallic=0):
    mat = bpy.data.materials.new('Poster / '+name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = metallic
    return mat

def weather(mat, scale, strength, colors):
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
    tex = nodes.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value = scale
    tex.inputs['Detail'].default_value = 3
    ramp = nodes.new('ShaderNodeValToRGB')
    for e, c in zip(ramp.color_ramp.elements, colors): e.color = (*c, 1)
    links.new(tex.outputs['Fac'], ramp.inputs['Fac'])
    links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    bump = nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = strength
    bump.inputs['Distance'].default_value = .025
    links.new(tex.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])

concrete = material('aged concrete', (.30,.32,.29))
weather(concrete, 7, .28, [(.20,.22,.20),(.43,.45,.39)])
soil = material('dry soil', (.17,.15,.105))
weather(soil, 14, .45, [(.10,.095,.065),(.24,.21,.14)])
steel = material('fence steel', (.30,.34,.31), .48, .68)
joint = material('expansion joints', (.065,.072,.06))
grass = material('olive dry grass', (.21,.25,.10))
edge = material('foundation edge', (.15,.18,.16))

def link(obj, category):
    for col in list(obj.users_collection): col.objects.unlink(obj)
    collections[category].objects.link(obj)
    return obj

def box(name, loc, size, mat, category='Ground', bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = link(bpy.context.object, category); obj.name = 'Poster / '+name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new('soft edge', 'BEVEL'); mod.width=bevel; mod.segments=2
    return obj

def line(name, points, radius, mat, category='Fence'):
    curve = bpy.data.curves.new('Poster / '+name, 'CURVE'); curve.dimensions='3D'
    curve.resolution_u=1; curve.bevel_depth=radius; curve.bevel_resolution=2
    spline=curve.splines.new('POLY'); spline.points.add(len(points)-1)
    for p, co in zip(spline.points, points): p.co=(*co,1)
    obj=bpy.data.objects.new('Poster / '+name, curve)
    collections[category].objects.link(obj); curve.materials.append(mat)
    return obj

# Independent object, mesh and material data; leaf fixed at a 40% open pose.
poster_mats = {}
for original in source.objects:
    if original.type != 'MESH': continue
    obj = original.copy(); obj.data = original.data.copy()
    obj.animation_data_clear(); obj.parent=None
    # An appended scene's matrix_world may be stale before depsgraph evaluation.
    # The source assembly has identity rig/root transforms; preserve local basis.
    obj.matrix_world=original.matrix_basis.copy()
    for mod in list(obj.modifiers):
        if mod.type == 'ARMATURE': obj.modifiers.remove(mod)
    if '_Leaf' in original.name: obj.location.x += 1.6
    obj.name='Poster / '+original.name.replace('.001','')
    obj.hide_render=False; obj.hide_viewport=False
    collections['Gate assembly'].objects.link(obj)
    for i, mat in enumerate(obj.data.materials):
        if mat.name not in poster_mats:
            copy=mat.copy(); copy.name='Poster / gate atlas'
            bsdf=next(n for n in copy.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
            bsdf.inputs['Roughness'].default_value=.57
            bsdf.inputs['Metallic'].default_value=.30
            poster_mats[mat.name]=copy
        obj.data.materials[i]=poster_mats[mat.name]

box('diorama base', (2.6,0,-.22), (12,7,.38), edge, bevel=.12)
box('left verge', (-2.45,0,-.025), (1.8,6.8,.09), soil, bevel=.03)
box('right verge', (7.65,0,-.025), (1.8,6.8,.09), soil, bevel=.03)
box('concrete apron', (2.6,0,-.045), (8.3,6.8,.1), concrete, bevel=.025)
for x in (-1.5,1.25,4,6.75):
    box('concrete joint', (x,0,.007), (.018,6.7,.007), joint)
for y in (-1.85,1.85):
    box('concrete joint', (2.6,y,.007), (8.2,.018,.007), joint)

# Fence stays in the fence plane, behind the moving leaf's 0.10 clearance.
for side, start, end in [('left',-3.15,-.08),('right',4.08,8.35)]:
    height=1.65
    for x in (start, (start+end)/2, end):
        line(side+' post',[(x,0,.02),(x,0,height+.07)],.032,steel)
    for z in (.18,height): line(side+' rail',[(start,0,z),(end,0,z)],.019,steel)
    # Clipped diagonal strands form a true open diamond mesh.
    for sign in (-1,1):
        intercept=start-height
        while intercept <= end+height:
            points=[]
            for z in (.20,height-.02):
                x=intercept+sign*z
                if start<=x<=end: points.append((x,0,z))
            for x in (start,end):
                z=(x-intercept)/sign
                if .20<z<height-.02: points.append((x,0,z))
            if len(points)>=2: line(side+' wire',points[:2],.006,steel)
            intercept+=.20

random.seed(42)
for i in range(95):
    x=random.choice((-2.5,7.7))+random.uniform(-.75,.75)
    y=random.uniform(-3.1,3.1)
    for j in range(3):
        h=random.uniform(.06,.19)
        line('grass',[(x,y,.025),(x+random.uniform(-.06,.06),y+random.uniform(-.06,.06),h)],.005,grass,'Details')
for points in ([(-.8,-2.6,.014),(-.5,-2.45,.014),(-.32,-2.15,.014),(.1,-1.96,.014)],
               [(5.7,2.9,.014),(5.4,2.7,.014),(5.45,2.45,.014),(5.1,2.1,.014)]):
    line('concrete crack',points,.004,joint,'Details')

def aim(obj, point): obj.rotation_euler=(Vector(point)-obj.location).to_track_quat('-Z','Y').to_euler()
camdata=bpy.data.cameras.new('Poster camera')
cam=bpy.data.objects.new('Poster camera',camdata); collections['Lighting'].objects.link(cam)
cam.location=(10,-13,8.5); aim(cam,(2.6,0,.5))
camdata.type='ORTHO'; camdata.ortho_scale=12.7; camdata.lens=50
scene.camera=cam
world=bpy.data.worlds.new('Poster / dusk'); world.use_nodes=True
bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND')
bg.inputs['Color'].default_value=(.14,.19,.18,1); bg.inputs['Strength'].default_value=.45
scene.world=world
def light(name, typ, pos, energy, color, size=None):
    data=bpy.data.lights.new(name,typ); data.energy=energy; data.color=color
    if size is not None: data.size=size
    obj=bpy.data.objects.new(name,data); collections['Lighting'].objects.link(obj)
    obj.location=pos; aim(obj,(3,0,.6)); return obj
sun=light('Poster / warm evening sun','SUN',(-6,-4,7),2.5,(1,.76,.48))
sun.data.angle=math.radians(9)
light('Poster / cool soft fill','AREA',(3,-6,7),700,(.64,.78,1),7)
light('Poster / rim','AREA',(7,3,5),550,(1,.85,.61),5)
try: scene.render.engine='CYCLES'
except TypeError: pass
if scene.render.engine=='CYCLES':
    scene.cycles.samples=48; scene.cycles.use_denoising=True
scene.render.resolution_x=1600; scene.render.resolution_y=1200
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.filepath=str(OUT/'poster_draft.png')
scene.view_settings.view_transform='AgX'
scene['purpose']='Workshop poster staging scene. Independent copies; no gameplay exports.'
scene['leaf_open_fraction']=.4
scene['source']=str(ROOT/'SG_ChainLink.blend')
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_perspective='CAMERA'
        area.spaces.active.overlay.show_overlays=False
# Store only poster dependencies, preserving the user's other open scenes.
bpy.data.libraries.write(str(OUT/'SG_Poster.blend'),{scene}, path_remap='ABSOLUTE', fake_user=True)
print('POSTER_SAVED',str(OUT/'SG_Poster.blend'),len(scene.objects),'objects')
