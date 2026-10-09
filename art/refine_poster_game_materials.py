"""Apply rectified installed-game materials and detailed poster-only set dressing."""
import bpy, math, random
from pathlib import Path
from mathutils import Vector

ROOT=Path(r'E:\git\SlidingGates\art')
OUT=ROOT/'poster'
TEX=OUT/'game_textures/prepared'
scene=bpy.data.scenes['SG_Poster'];bpy.context.window.scene=scene
bpy.data.libraries.write(str(OUT/'SG_Poster_before_materials.blend'),{scene},path_remap='ABSOLUTE',fake_user=True)
cols={c.name.split(' / ')[-1]:c for c in scene.collection.children}

def shader(name):
    m=bpy.data.materials.new('Poster / '+name);m.use_nodes=True
    b=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    b.inputs['Roughness'].default_value=1
    b.inputs['Specular IOR Level'].default_value=.12
    return m,b

def image_material(name,path,axes=None,scale=None,alpha=False):
    m,b=shader(name);ns,ls=m.node_tree.nodes,m.node_tree.links
    image=bpy.data.images.load(str(path),check_existing=True);image.pack()
    t=ns.new('ShaderNodeTexImage');t.image=image;t.interpolation='Linear'
    if axes=='XZ':
        coord=ns.new('ShaderNodeTexCoord');sep=ns.new('ShaderNodeSeparateXYZ');comb=ns.new('ShaderNodeCombineXYZ')
        ls.new(coord.outputs['Generated'],sep.inputs[0])
        ls.new(sep.outputs['X'],comb.inputs['X']);ls.new(sep.outputs['Z'],comb.inputs['Y'])
        ls.new(comb.outputs['Vector'],t.inputs['Vector'])
    elif scale:
        geo=ns.new('ShaderNodeNewGeometry');mapping=ns.new('ShaderNodeVectorMath');mapping.operation='SCALE'
        mapping.inputs['Scale'].default_value=scale
        ls.new(geo.outputs['Position'],mapping.inputs[0]);ls.new(mapping.outputs['Vector'],t.inputs['Vector'])
    ls.new(t.outputs['Color'],b.inputs['Base Color'])
    bump=ns.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.008
    ls.new(t.outputs['Color'],bump.inputs['Height']);ls.new(bump.outputs['Normal'],b.inputs['Normal'])
    if alpha:ls.new(t.outputs['Alpha'],b.inputs['Alpha'])
    return m

wood=[image_material('native timber grain '+str(i),TEX/f'wood_board_{i}.png',axes='XZ') for i in range(7)]
asphalt=image_material('native asphalt',TEX/'asphalt.png',scale=.25)
# Low-frequency color variation only modulates grain slightly; no rectangular patches.
ns,ls=asphalt.node_tree.nodes,asphalt.node_tree.links
b=next(n for n in ns if n.type=='BSDF_PRINCIPLED');tex=next(n for n in ns if n.type=='TEX_IMAGE')
geo=next(n for n in ns if n.type=='NEW_GEOMETRY')
noise=ns.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=.7;noise.inputs['Detail'].default_value=2
ls.new(geo.outputs['Position'],noise.inputs['Vector'])
ramp=ns.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.68,.68,.67,1);ramp.color_ramp.elements[1].color=(1,1,1,1)
ls.new(noise.outputs['Fac'],ramp.inputs[0])
mix=ns.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1
ls.new(tex.outputs['Color'],mix.inputs[1]);ls.new(ramp.outputs[0],mix.inputs[2]);ls.new(mix.outputs[0],b.inputs['Base Color'])

random.seed(55)
boards=[]
for o in list(scene.objects):
    if any(k in o.name for k in ('entrance resurfacing','asphalt fracture','fracture branch')):
        bpy.data.objects.remove(o,do_unlink=True);continue
    if 'vertical timber board' in o.name:
        o.data.materials.clear();o.data.materials.append(random.choice(wood));boards.append(o)
        # Uneven weathered edges and board tips instead of identical moulded planks.
        for v in o.data.vertices:
            if v.co.z>0:v.co.z+=random.uniform(-.016,.016)
        o.rotation_euler.y+=random.uniform(-.006,.006)
    elif 'fence post' in o.name or 'horizontal backing rail' in o.name:
        o.data.materials.clear();o.data.materials.append(wood[2])
    elif 'asphalt yard' in o.name:
        o.data.materials.clear();o.data.materials.append(asphalt)
    elif 'grass corner' in o.name:
        o.data.materials.clear();o.data.materials.append(image_material('native dry grass',TEX/'grass.png',scale=1))

iron,b=shader('rusted nail heads');b.inputs['Base Color'].default_value=(.035,.026,.016,1)
rust,b=shader('dry split wood');b.inputs['Base Color'].default_value=(.045,.02,.009,1)
grime,b=shader('fence footing dirt');b.inputs['Base Color'].default_value=(.12,.10,.07,1)
def line(name,points,radius,m):
    c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.bevel_depth=radius;c.bevel_resolution=0
    p=c.splines.new('POLY');p.points.add(len(points)-1)
    for v,co in zip(p.points,points):v.co=(*co,1)
    o=bpy.data.objects.new('Poster / '+name,c);cols['Details'].objects.link(o);c.materials.append(m)
    return o

# Nails, occasional timber splits and a worn lower edge are visible in close renders.
for i,o in enumerate(boards):
    a=o.rotation_euler.z
    normal=Vector((math.sin(a),-math.cos(a),0))
    for z in (.43,1.66):
        pos=o.location+normal*.037;pos.z=z
        bpy.ops.mesh.primitive_uv_sphere_add(segments=8,ring_count=4,radius=.008,location=pos)
        nail=bpy.context.object;nail.name='Poster / nail'
        for c in list(nail.users_collection):c.objects.unlink(nail)
        cols['Details'].objects.link(nail);nail.data.materials.append(iron)
    if i%4==0:
        x,y=o.location.x,o.location.y
        p=Vector((x,y,0))+normal*.038
        line('wood split',[(p.x,p.y,.04),(p.x+.005,p.y,.19),(p.x-.003,p.y,.36)],.0025,rust)

def plane(name,loc,size,m):
    bpy.ops.mesh.primitive_plane_add(size=1,location=loc)
    o=bpy.context.object;o.name='Poster / '+name;o.scale=(size[0],size[1],1)
    for c in list(o.users_collection):c.objects.unlink(o)
    cols['Details'].objects.link(o);o.data.materials.append(m)
    return o

# Native chipped potholes, not raised black tubes.
for i,(x,y,size,index) in enumerate([(-.3,-2.7,1.6,16),(4.8,-3.2,1.3,20),(2.0,2.2,1.1,4),
        (-2.5,1.4,1.2,18),(6.7,1.4,1,7),(6.1,-.7,.8,12)]):
    m=image_material('native crack '+str(i),TEX/f'crack_{index}.png',alpha=True)
    o=plane('native asphalt damage',(x,y,.006),(size,size),m);o.rotation_euler.z=random.uniform(-.5,.5)

# Fine branching fissures as flat tapered polygons, with irregular edges.
dark,b=shader('fine asphalt fissures');b.inputs['Base Color'].default_value=(.04,.041,.04,1)
def fissure(start,direction,count,width,seed):
    rnd=random.Random(seed);p=Vector((*start,.006));pts=[p.copy()]
    heading=direction
    for i in range(count):
        heading+=rnd.uniform(-.45,.45)
        p+=Vector((math.cos(heading),math.sin(heading),0))*rnd.uniform(.07,.16);pts.append(p.copy())
    vs=[];fs=[]
    for i,p in enumerate(pts):
        d=pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)]
        n=Vector((-d.y,d.x,0)).normalized();w=width*rnd.uniform(.5,1.3)
        vs.extend([p+n*w,p-n*w])
        if i:fs.append((2*i-2,2*i-1,2*i+1,2*i))
    mesh=bpy.data.meshes.new('asphalt fissure');mesh.from_pydata(vs,[],fs);mesh.materials.append(dark)
    o=bpy.data.objects.new('Poster / fine branching fissure',mesh);cols['Details'].objects.link(o)
    return pts
for i,(start,angle,length) in enumerate([((-1.2,-3),.5,38),((4.5,-2.3),.8,26),((1.2,2.3),2.1,27)]):
    pts=fissure(start,angle,length,.012,41+i)
    for j in (8,17):fissure((pts[j].x,pts[j].y),angle+1.3,8,.006,97+i+j)

# Replace faceted shrub placeholders with the game's detailed ornamental sprites.
for o in list(scene.objects):
    if '/ shrub' in o.name:bpy.data.objects.remove(o,do_unlink=True)
for i,(x,y,width,index) in enumerate([(6.3,5.35,.85,4),(8.5,5.65,1.05,12),(9.1,4.2,.7,9)]):
    raw=OUT/'game_textures'/f'vegetation_ornamental_01_{index}.png'
    image=bpy.data.images.load(str(raw),check_existing=True)
    height=width*image.size[1]/image.size[0]
    m=image_material('native ornamental shrub '+str(i),raw,alpha=True)
    o=plane('native shrub',(x,y,height*.42+.10),(width,height),m)
    o.rotation_euler=scene.camera.rotation_euler.copy()

# Subtle details near the motor: cable conduit, fixings and a maintenance label.
line('drive conduit',[(4.06,-.31,.20),(4.15,-.32,.15),(4.17,.20,.06),(4.17,.32,.09)],.009,iron)
cam=scene.camera;cam.data.ortho_scale=10.2
cam.location=(11,-14,10.5);cam.rotation_euler=(Vector((2.5,.35,.6))-cam.location).to_track_quat('-Z','Y').to_euler()
for o in scene.objects:
    if 'native shrub' in o.name:o.rotation_euler=cam.rotation_euler.copy()
scene.cycles.samples=64
scene.render.resolution_x=2000;scene.render.resolution_y=1500
scene.render.filepath=str(OUT/'poster_draft.png')
scene['materials']='Installed PZ tiles: rectified wood, asphalt, grass, crack decals and shrub sprites.'
scene['details']='Irregular board tips, nail heads, wood splits, chipped asphalt and tapered fissures.'
bpy.data.libraries.write(str(OUT/'SG_Poster.blend'),{scene},path_remap='ABSOLUTE',fake_user=True)
print('REFINED_GAME_MATERIALS',len(scene.objects))
