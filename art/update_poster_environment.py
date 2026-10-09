"""Replace poster staging with the wooden-fence/asphalt gameplay reference."""
import bpy, math, random
from pathlib import Path
from mathutils import Vector

ROOT=Path(r'E:\git\SlidingGates\art')
scene=bpy.data.scenes['SG_Poster']
bpy.context.window.scene=scene
out=ROOT/'poster'
bpy.data.libraries.write(str(out/'SG_Poster_before_wood.blend'),{scene},path_remap='ABSOLUTE',fake_user=True)
cols={c.name.split(' / ')[-1]:c for c in scene.collection.children}
for name in ('Fence','Ground','Details'):
    for obj in list(cols[name].objects): bpy.data.objects.remove(obj,do_unlink=True)

def mat(name,color,rough=1,metal=0):
    m=bpy.data.materials.new('Poster / '+name);m.use_nodes=True
    b=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value=(*color,1)
    b.inputs['Roughness'].default_value=rough;b.inputs['Metallic'].default_value=metal
    return m

def procedural(m,scale,colors,strength=.2,stretch=None):
    ns,ls=m.node_tree.nodes,m.node_tree.links
    b=next(n for n in ns if n.type=='BSDF_PRINCIPLED')
    tex=ns.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=scale
    tex.inputs['Detail'].default_value=3
    if stretch:
        coord=ns.new('ShaderNodeTexCoord');v=ns.new('ShaderNodeVectorMath');v.operation='MULTIPLY'
        v.inputs[1].default_value=stretch
        ls.new(coord.outputs['Generated'],v.inputs[0]);ls.new(v.outputs['Vector'],tex.inputs['Vector'])
    ramp=ns.new('ShaderNodeValToRGB')
    for e,c in zip(ramp.color_ramp.elements,colors):e.color=(*c,1)
    ls.new(tex.outputs['Fac'],ramp.inputs['Fac']);ls.new(ramp.outputs['Color'],b.inputs['Base Color'])
    bump=ns.new('ShaderNodeBump');bump.inputs['Strength'].default_value=strength
    bump.inputs['Distance'].default_value=.018
    ls.new(tex.outputs['Fac'],bump.inputs['Height']);ls.new(bump.outputs['Normal'],b.inputs['Normal'])

asphalt=mat('weathered asphalt',(.17,.18,.18))
procedural(asphalt,36,[(.12,.13,.13),(.24,.25,.24)],.3)
patch=mat('old asphalt repairs',(.21,.22,.21))
procedural(patch,25,[(.18,.19,.18),(.28,.29,.27)],.22)
crack=mat('asphalt cracks',(.035,.037,.03))
curb=mat('concrete curb',(.43,.44,.40))
procedural(curb,6,[(.28,.29,.27),(.49,.50,.44)],.16)
grass=mat('dry lawn',(.16,.19,.055))
procedural(grass,18,[(.095,.12,.035),(.25,.28,.095)],.5)
leaf=mat('muted shrubs',(.21,.30,.11))
rock=mat('limestone',(.34,.36,.31))
orange=mat('faded traffic cone',(.65,.24,.055))
rubber=mat('cone base',(.085,.08,.065))
wood=[]
for i in range(7):
    m=mat('aged timber '+str(i),(.2,.1,.035))
    t=i*.009
    procedural(m,6,[(.09+t,.049+t*.6,.019+t*.3),(.30+t,.16+t*.6,.055+t*.3)],.33,(3,2,.055))
    wood.append(m)

def link(obj,col):
    for c in list(obj.users_collection):c.objects.unlink(obj)
    cols[col].objects.link(obj);return obj
def box(name,loc,size,m,col='Ground',bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    o=link(bpy.context.object,col);o.name='Poster / '+name;o.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(m)
    if bevel:
        b=o.modifiers.new('worn edges','BEVEL');b.width=bevel;b.segments=1
    return o
def line(name,points,radius,m,col='Details'):
    c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.bevel_depth=radius;c.bevel_resolution=1
    p=c.splines.new('POLY');p.points.add(len(points)-1)
    for v,co in zip(p.points,points):v.co=(*co,1)
    o=bpy.data.objects.new('Poster / '+name,c);cols[col].objects.link(o);c.materials.append(m)
    return o

random.seed(81)
box('asphalt yard',(3,1,-.07),(32,28,.12),asphalt)
box('entrance resurfacing',(1.9,-2.2,-.004),(4.5,4.4,.011),patch)
# Fence sits just behind the moving leaf, on its outside face in this camera.
fence_y=.32
def fence(start,end):
    a,b=Vector(start),Vector(end);length=(b-a).length;direction=(b-a).normalized()
    count=round(length/.13)
    for i in range(count):
        pos=a+direction*((i+.5)*length/count)
        h=2.08+random.uniform(-.025,.025)
        o=box('vertical timber board',(pos.x,pos.y,h/2),(.125,.065,h),random.choice(wood),'Fence',.004)
        o.rotation_euler.z=math.atan2(direction.y,direction.x)
    for i in range(math.ceil(length/1.9)+1):
        pos=a+(b-a)*i/math.ceil(length/1.9)
        box('fence post',(pos.x,pos.y+.03,1.08),(.14,.14,2.16),wood[2],'Fence',.01)
    mid=(a+b)/2
    for z in (.42,1.65):
        o=box('horizontal backing rail',(mid.x,mid.y+.065,z),(length,.075,.085),wood[0],'Fence')
        o.rotation_euler.z=math.atan2(direction.y,direction.x)
fence((-4,fence_y),(0,fence_y))
fence((4,fence_y),(10,fence_y))
fence((-4,fence_y),(-4,6.5))
fence((-4,6.5),(10,6.5))

# Small planted corner as in the reference, with a concrete retaining edge.
box('grass corner',(7.8,4.7,.02),(4.4,3.2,.11),grass)
for loc,size in [((5.55,4.7,.04),(.09,3.3,.16)),((7.8,3.05,.04),(4.5,.09,.16))]:
    box('lawn curb',loc,size,curb,bevel=.015)
for x,y,r in [(6.2,5.3,.5),(8.5,5.7,.6),(9.1,4.0,.38)]:
    for j in range(7):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=r*.65,
            location=(x+random.uniform(-.35,.35),y+random.uniform(-.3,.3),.25+random.uniform(.05,.5)))
        o=link(bpy.context.object,'Details');o.name='Poster / shrub';o.data.materials.append(leaf)
for i in range(5):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=random.uniform(.1,.21),
        location=(random.uniform(6,8),random.uniform(3.5,4.2),.14))
    o=link(bpy.context.object,'Details');o.name='Poster / stone';o.scale.z=.6;o.data.materials.append(rock)
for i in range(110):
    x=random.uniform(5.7,9.8);y=random.uniform(3.2,6.1)
    for j in range(2):line('grass blade',[(x,y,.08),(x+random.uniform(-.06,.06),y,.08+random.uniform(.04,.15))],.004,grass)

for seed,start,steps,step in [(6,(-1,-4),15,.45),(12,(4.8,-3.5),10,.38),(18,(1,3),10,.3)]:
    rnd=random.Random(seed);x,y=start;pts=[]
    for i in range(steps):
        pts.append((x,y,.003));x+=step;y+=rnd.uniform(-.25,.3)
    line('asphalt fracture',pts,.013,crack)
    for i in (3,7):
        p=pts[i];line('fracture branch',[p,(p[0]+.15,p[1]+.35,.003),(p[0]+.5,p[1]+.47,.003)],.008,crack)
for x,y in [(5.9,-2.5),(7.1,-2.5)]:
    box('cone foot',(x,y,.02),(.32,.32,.04),rubber,'Details',.025)
    bpy.ops.mesh.primitive_cone_add(vertices=12,radius1=.13,radius2=.025,depth=.42,location=(x,y,.25))
    o=link(bpy.context.object,'Details');o.name='Poster / traffic cone';o.data.materials.append(orange)

cam=scene.camera;cam.location=(11,-14,12)
cam.rotation_euler=(Vector((2.2,.4,.65))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.ortho_scale=11.4
sun=bpy.data.objects['Poster / warm evening sun'];sun.data.energy=2.0;sun.data.color=(1,.86,.67)
scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.render.filepath=str(out/'poster_draft.png')
scene['environment']='Wooden privacy fence and weathered asphalt yard, based on gameplay screenshot.'
for image in bpy.data.images:
    if image.source=='FILE' and image.has_data and not image.packed_file:image.pack()
bpy.data.libraries.write(str(out/'SG_Poster.blend'),{scene},path_remap='ABSOLUTE',fake_user=True)
print('WOODEN_FENCE_SCENE_SAVED',len(scene.objects))
