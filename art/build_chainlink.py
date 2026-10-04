"""Run inside Blender through MCP. Prototype units: one cell = one Blender unit."""
import bpy, math, os, random
from mathutils import Vector, Quaternion

ROOT = r'E:\git\SlidingGates\art'
OUT = os.path.join(ROOT, 'exports')
os.makedirs(OUT, exist_ok=True)
scene = bpy.context.scene
WIDTH = int(globals().get('GATE_WIDTH', 2))
assert WIDTH >= 2
SAVE_PATH = globals().get('GATE_SAVE_PATH', os.path.join(ROOT, 'SG_ChainLink.blend'))
reference = bpy.data.collections.new('VanillaReference')
scene.collection.children.link(reference)
for obj in list(scene.objects):
    for col in list(obj.users_collection): col.objects.unlink(obj)
    reference.objects.link(obj)
reference.hide_viewport = True
reference.hide_render = True
col = bpy.data.collections.new('SlidingGates')
scene.collection.children.link(col)

# Shared opaque atlas: the mesh holes are geometry, so no alpha sorting is needed.
palette = [(0.28,0.33,0.30,1), (0.39,0.43,0.40,1), (0.20,0.23,0.21,1),
           (0.27,0.33,0.23,1), (0.24,0.22,0.18,1), (0.48,0.51,0.47,1),
           (0.09,0.11,0.10,1), (0.57,0.46,0.24,1)]
img = bpy.data.images.get('SG_ChainLink_Atlas') or bpy.data.images.new('SG_ChainLink_Atlas', width=128, height=128, alpha=True)
random.seed(42)
pixels=[]
for y in range(128):
    for x in range(128):
        sw=(y//64)*4+x//32; c=palette[sw]
        # Quiet broad variation survives downsampling; narrow scratches stay subtle.
        lx=(x%32)/31; ly=(y%64)/63
        shade=0.94+0.06*math.sin(lx*math.pi)+0.025*math.sin(ly*math.pi*3)
        wear=0.045 if sw in (0,1,3,5) and (x+3*y)%47==0 else 0
        noise=random.uniform(-0.008,0.008)
        pixels.extend([max(0,min(1,v*shade+noise+wear)) for v in c[:3]]+[1])
img.pixels.foreach_set(pixels)
img.filepath_raw=os.path.join(ROOT,'SG_ChainLink_Atlas.png')
img.file_format=next(i.identifier for i in img.bl_rna.properties['file_format'].enum_items if i.identifier=='PNG')
img.save()
mat=bpy.data.materials.new('SG_ChainLink_Atlas'); mat.use_nodes=True
bsdf=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
tex=mat.node_tree.nodes.new('ShaderNodeTexImage'); tex.image=img
mat.node_tree.links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
bsdf.inputs['Roughness'].default_value=0.82

def rod(a,b,r,verts,faces,swatches,swatch=0,sides=8):
    a,b=Vector(a),Vector(b); d=(b-a).normalized()
    u=d.cross(Vector((0,0,1)))
    if u.length<0.01: u=d.cross(Vector((0,1,0)))
    u.normalize(); v=d.cross(u); start=len(verts)
    for p in (a,b):
        for i in range(sides):
            verts.append(tuple(p+r*(u*math.cos(i*2*math.pi/sides)+v*math.sin(i*2*math.pi/sides))))
    for i in range(sides):
        smooth_faces.add(len(faces))
        j=(i+1)%sides; faces.append((start+i,start+j,start+sides+j,start+sides+i)); swatches.append(swatch)
    faces.extend([tuple(start+i for i in range(sides-1,-1,-1)),tuple(start+sides+i for i in range(sides))]); swatches.extend([swatch,swatch])

def box(center,size,verts,faces,swatches,swatch):
    start=len(verts)
    for x,y,z in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]:
        verts.append(tuple(center[i]+q*size[i]/2 for i,q in enumerate((x,y,z))))
    for f in [(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]:
        # PZ preserves supplied normals: these corners require reversed winding
        # for outward-facing normals on every box face.
        face=tuple(start+i for i in reversed(f))
        a,b,c=(Vector(verts[index]) for index in face[:3])
        centre=sum((Vector(verts[index]) for index in face),Vector())/4
        assert (b-a).cross(c-a).dot(centre-Vector(center))>0
        faces.append(face); swatches.append(swatch)

def mesh(name,build):
    global smooth_faces
    smooth_faces=set()
    vs,fs,ss=[],[],[]; build(vs,fs,ss)
    data=bpy.data.meshes.new(name); data.from_pydata(vs,[],fs); data.update()
    obj=bpy.data.objects.new(name,data); col.objects.link(obj); data.materials.append(mat)
    uv=data.uv_layers.new(name='AtlasUV')
    for poly,sw in zip(data.polygons,ss):
        poly.use_smooth=poly.index in smooth_faces
        cx=(sw%4+0.5)/4; cy=(sw//4+0.5)/2
        for j,li in enumerate(poly.loop_indices):
            uv.data[li].uv=(cx+(-0.07 if j%2==0 else 0.07),cy+(-0.15 if j<2 else 0.15))
    return obj

def leaf(v,f,s):
    # Width changes lengths/counts, never tube thickness, height or wire pitch.
    for a,b in [((0.025,0,0.12),(WIDTH-0.025,0,0.12)),((0.025,0,1.88),(WIDTH-0.025,0,1.88))] + [((x,0,0.12),(x,0,1.88)) for x in [0.025,*range(1,WIDTH),WIDTH-0.025]]:
        rod(a,b,0.025,v,f,s)
    # Two diagonal families clipped to the inside of the tubular frame.
    xmin,xmax,zmin,zmax=0.05,WIDTH-0.05,0.145,1.855
    for slope in (1,-1):
        for k in range(-math.ceil(WIDTH/0.13)-2,math.ceil((WIDTH+1.9)/0.13)+2):
            c=k*0.13; pts=[]
            for x in (xmin,xmax):
                z=slope*x+c
                if zmin<=z<=zmax: pts.append((x,0.006*slope,z))
            for z in (zmin,zmax):
                x=(z-c)/slope
                if xmin<=x<=xmax: pts.append((x,0.006*slope,z))
            if len(pts)==2: rod(pts[0],pts[1],0.005,v,f,s,1,6)
    box((WIDTH/2,-0.055,0.28),(WIDTH,0.055,0.04),v,f,s,2)
    for i in range(math.floor((WIDTH-0.05)/0.045)+1):
        box((0.025+i*0.045,-0.055,0.245),(0.0225,0.055,0.03),v,f,s,5)
    # Mount the handle on a short crossmember, rather than on loose wire.
    box((WIDTH-0.51,0,0.95),(0.97,0.045,0.045),v,f,s,0)
    box((WIDTH-0.2,-0.055,0.95),(0.07,0.07,0.13),v,f,s,2)
    rod((WIDTH-0.21,-0.10,0.88),(WIDTH-0.21,-0.10,1.02),0.012,v,f,s,5)
    for x in (0.22,WIDTH-0.22):
        rod((x,-0.025,0.0975),(x,0.025,0.0975),0.055,v,f,s,6,10)

gate=mesh('SG_Leaf',leaf)
for vertex in gate.data.vertices: vertex.co.y += 0.18
def post(v,f,s):
    # Square steel post provides a flat face for the bolted guide bracket.
    box((0,0,1.01),(0.076,0.076,2.02),v,f,s,0)
    box((0,0,0.025),(0.13,0.13,0.05),v,f,s,2)
    box((0,0,2.02),(0.09,0.09,0.035),v,f,s,5)
    # Vertical mounting plate touches the front face; the shelf starts outside it.
    box((0,0.044,1.89),(0.15,0.012,0.24),v,f,s,2)
    # Two roller stations straddle the post along the direction of travel.
    # World X 1.88 and 2.12: at least one grips the top rail at any pose.
    box((-0.04,0.155,1.975),(0.42,0.25,0.025),v,f,s,0)
    for x in (-0.16,0.08):
        for y in (0.131,0.229):
            rod((x,y,1.82),(x,y,1.9625),0.006,v,f,s,5)
            rod((x,y,1.83),(x,y,1.93),0.022,v,f,s,6,10)
            rod((x,y,1.9875),(x,y,1.9995),0.010,v,f,s,5,6)
    # Two triangular gussets brace the shelf from below.
    for x in (-0.075,0.075):
        start=len(v)
        for dx in (-0.006,0.006):
            for y,z in [(0.05,1.9625),(0.05,1.83),(0.15,1.9625)]:
                v.append((x+dx,y,z))
        for face in [(0,2,1),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)]:
            f.append(tuple(start+i for i in face)); s.append(0)
    for x in (-0.047,0.047):
        for z in (1.80,1.995):
            rod((x,0.050,z),(x,0.055,z),0.014,v,f,s,5,10)
            rod((x,0.055,z),(x,0.064,z),0.010,v,f,s,2,6)
def catcher(v,f,s):
    box((0,0,1.01),(0.076,0.076,2.02),v,f,s,0)
    box((0,0,0.025),(0.13,0.13,0.05),v,f,s,2)
    box((0,0,2.02),(0.09,0.09,0.035),v,f,s,5)
    for z in (0.12,1.88):
        # Bolted arm carries an open-ended U receiver, facing the approaching leaf.
        box((0,0.044,z),(0.07,0.012,0.14),v,f,s,2)
        box((0,0.111,z),(0.045,0.122,0.045),v,f,s,0)
        box((0.02,0.18,z),(0.016,0.10,0.10),v,f,s,2)
        for y in (0.134,0.226): box((0.067,y,z),(0.11,0.012,0.10),v,f,s,0)
        if z<1: box((0.067,0.18,0.09),(0.11,0.08,0.012),v,f,s,0)
        for dz in (-0.048,0.048): rod((0,0.050,z+dz),(0,0.062,z+dz),0.009,v,f,s,5,6)
post_a=mesh('SG_Post_Left',catcher); post_a.location.x=-0.04
post_b=mesh('SG_Post_Right',post); post_b.location.x=WIDTH+0.04
def rail_piece(v,f,s):
    box((0.5,0.18,0.0315),(1,0.025,0.022),v,f,s,4)
rail=mesh('SG_Rail_OneCell',rail_piece)
for i in range(1,2*WIDTH):
    o=bpy.data.objects.new('SG_Rail_Preview_'+str(i),rail.data); col.objects.link(o); o.location.x=i
def motor(v,f,s):
    box((0,0,0.055),(0.42,0.29,0.11),v,f,s,2)
    box((0,0,0.27),(0.32,0.28,0.36),v,f,s,3)
    box((0,0,0.465),(0.35,0.31,0.03),v,f,s,3)
    for z in (0.2,0.23,0.26,0.29): box((0,-0.145,z),(0.14,0.012,0.009),v,f,s,6)
    box((0,-0.15,0.36),(0.085,0.012,0.04),v,f,s,7)
    # Compact offset gearbox routes around the post at world X=2.04.
    # The connecting neck is at X=1.94; the output shaft starts past Y=0.038.
    box((-0.06,0.245,0.19),(0.09,0.23,0.07),v,f,s,2)
    box((-0.03,0.31,0.19),(0.10,0.06,0.07),v,f,s,2)
    rod((0,0.325,0.19),(0,0.365,0.19),0.016,v,f,s,5,8)
    rod((0,0.325,0.19),(0,0.365,0.19),0.055,v,f,s,2,12)
motor_obj=mesh('SG_Drive',motor); motor_obj.location=(WIDTH,-0.22,0)

arm=bpy.data.armatures.new('SG_Rig'); rig=bpy.data.objects.new('SG_Rig',arm); col.objects.link(rig)
bpy.context.view_layer.objects.active=rig; rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); bone=arm.edit_bones.new('DoorBone'); bone.head=(0,0,0); bone.tail=(0,1,0); bpy.ops.object.mode_set(mode='OBJECT')
group=gate.vertex_groups.new(name='DoorBone'); group.add(list(range(len(gate.data.vertices))),1,'REPLACE')
mod=gate.modifiers.new('DoorBone','ARMATURE'); mod.object=rig; gate.parent=rig
scene.render.fps=24; scene.frame_start=1; scene.frame_end=49
rig['cell_width']=1.0; rig['gate_width_cells']=WIDTH; rig['fence_clearance']=0.18; rig['duration_seconds']=2.0
def animate(direction):
    rig.animation_data_clear(); rig.animation_data_create()
    for label,keys in [('Open',[(1,(0,0,0)),(49,(direction*WIDTH,0,0))]),('Close',[(1,(direction*WIDTH,0,0)),(49,(0,0,0))])]:
        action=bpy.data.actions.new('SG_'+label); rig.animation_data.action=action
        for frame,loc in keys:
            rig.pose.bones['DoorBone'].location=loc
            rig.pose.bones['DoorBone'].keyframe_insert(data_path='location',frame=frame,group='DoorBone')
        track=rig.animation_data.nla_tracks.new(); track.name=label
        strip=track.strips.new(label,1,action); track.mute=True
    rig.animation_data.action=rig.animation_data.nla_tracks[0].strips[0].action
    scene.frame_set(1)
animate(1)
scene['SG_notes']=f'1 cell = 1 unit; height 1.9; fixed fence clearance 0.18; straight slide {WIDTH} cells in 2 seconds. Validate PZ scale/origin and clipping.'

# A clean orthographic modelling view; original startup scene remains untouched.
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_rotation=Quaternion((0.82,0.42,0.18,0.35)).normalized()
        area.spaces.active.region_3d.view_distance=6.5
        area.spaces.active.region_3d.view_location=Vector((1.8,0,0.9))
        area.spaces.active.shading.color_type='TEXTURE'
bpy.ops.wm.save_as_mainfile(filepath=SAVE_PATH)
print('CREATED',len(col.objects),'objects; leaf triangles',sum(len(p.vertices)-2 for p in gate.data.polygons))
