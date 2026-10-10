"""Run in the existing Blender via MCP. Add wooden workbenches; preserve metal scenes.

Uses calibrated rigs and mechanisms, installed Doorknob FBX, native timber atlas.
Refuses overwriting existing workbenches. Wooden export has its own exporter.
"""
import bpy
import bmesh
import math
import json
import os
from mathutils import Vector, Matrix

ART = r'E:\git\SlidingGates\art'
assert bpy.data.filepath == os.path.join(ART, 'SG_ChainLink.blend')
if not globals().get('WOOD_UPDATE'):
    assert not any(s.get('sg_material') == 'wood' for s in bpy.data.scenes), 'Wood already exists: update explicitly'
assert bpy.data.scenes.get('SG_Wood_References'), 'Import the native DoorKnob FBX into its reference scene first'
KNOB = next(o.data for o in bpy.data.scenes['SG_Wood_References'].objects if o.type == 'MESH')
if not globals().get('WOOD_UPDATE'):
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART, 'SG_ChainLink_before_wood.blend'), copy=True)
img = bpy.data.images.load(os.path.join(ART,'SG_Wood_Atlas.png'), check_existing=True)
mat = bpy.data.materials.get('SG_Wood_Atlas') or bpy.data.materials.new('SG_Wood_Atlas'); mat.use_nodes = True
node = mat.node_tree.nodes.new('ShaderNodeTexImage'); node.image = img
bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
mat.node_tree.links.new(node.outputs['Color'], bsdf.inputs['Base Color'])
bsdf.inputs['Roughness'].default_value = .85


def components(mesh):
    adj = [set() for _ in mesh.vertices]
    for e in mesh.edges:
        a,b = e.vertices; adj[a].add(b); adj[b].add(a)
    seen = set()
    for v in mesh.vertices:
        if v.index in seen: continue
        ids=set(); todo=[v.index]
        while todo:
            i=todo.pop()
            if i in ids: continue
            ids.add(i); todo.extend(adj[i]-ids)
        seen.update(ids)
        ps=[p for p in mesh.polygons if p.vertices[0] in ids]
        uv=mesh.uv_layers.active.data[ps[0].loop_start].uv
        yield sorted(ids),ps,int(uv.x*4)+4*int(uv.y*2)


class Mesh:
    def __init__(self): self.v=[]; self.f=[]; self.uv=[]; self.smooth=[]
    def face(self, ids, sw, smooth=False, uv=None):
        self.f.append(tuple(ids)); self.smooth.append(smooth)
        if uv is None:
            uv=[(.04,.04),(.96,.04),(.96,.96),(.04,.96)]
            if len(ids)!=4:
                uv=[(.5+.44*math.cos(i*math.tau/len(ids)),.5+.44*math.sin(i*math.tau/len(ids))) for i in range(len(ids))]
        self.uv.append([((sw%4+u)/4,(sw//4+v)/2) for u,v in uv])
    def prism(self, outline, y0, y1, sw):
        # CCW polygon in XZ. Front +Y and back -Y are deliberately opposed.
        n=len(outline); start=len(self.v)
        self.v.extend((x,y,z) for y in (y0,y1) for x,z in outline)
        xmin=min(x for x,z in outline); xmax=max(x for x,z in outline)
        zmin=min(z for x,z in outline); zmax=max(z for x,z in outline)
        uv=[(.04+.92*(x-xmin)/max(.001,xmax-xmin),.04+.92*(z-zmin)/max(.001,zmax-zmin)) for x,z in outline]
        self.face([start+i for i in range(n)],sw,uv=uv)
        self.face([start+n+i for i in reversed(range(n))],sw,uv=list(reversed(uv)))
        for i in range(n):
            j=(i+1)%n; self.face((start+i,start+n+i,start+n+j,start+j),sw)
    def box(self, center, size, sw):
        x,y,z=center; w,d,h=size
        self.prism([(x-w/2,z-h/2),(x+w/2,z-h/2),(x+w/2,z+h/2),(x-w/2,z+h/2)],y-d/2,y+d/2,sw)
    def beam(self,a,b,w,d,sw,bounds=None):
        a,b=Vector(a),Vector(b); delta=(b-a).normalized(); u=Vector((-delta.z,0,delta.x))*w/2
        pts=[(p.x,p.z) for p in (a-u,b-u,b+u,a+u)]
        if bounds:
            # Saw the ends against the frame opening, including both corner faces.
            for axis,edge,sign in ((0,bounds[0],1),(0,bounds[1],-1),(1,bounds[2],1),(1,bounds[3],-1)):
                clipped=[]
                for p,q in zip(pts,pts[1:]+pts[:1]):
                    inside=(p[axis]-edge)*sign>=-1e-10
                    other=(q[axis]-edge)*sign>=-1e-10
                    if inside: clipped.append(p)
                    if inside!=other:
                        t=(edge-p[axis])/(q[axis]-p[axis])
                        clipped.append(tuple(p[k]+t*(q[k]-p[k]) for k in range(2)))
                pts=clipped
        self.prism(pts,a.y-d/2,a.y+d/2,sw)
    def copy(self,mesh,ids,ps,sw,transform=None,native_uv=False):
        start=len(self.v); remap={i:start+j for j,i in enumerate(ids)}
        self.v.extend(tuple(transform(mesh.vertices[i].co) if transform else mesh.vertices[i].co) for i in ids)
        for p in ps:
            uv=None
            if native_uv: uv=[tuple(mesh.uv_layers.active.data[i].uv) for i in p.loop_indices]
            self.face([remap[i] for i in p.vertices],sw,p.use_smooth,uv)
    def finish(self,name,reverse=False):
        data=bpy.data.meshes.new(name)
        data.from_pydata([(-x,y,z) if reverse else (x,y,z) for x,y,z in self.v],[],
                         [tuple(reversed(f)) if reverse else f for f in self.f]); data.update()
        data.materials.append(mat); layer=data.uv_layers.new(name='AtlasUV')
        for p,uv,smooth in zip(data.polygons,self.uv,self.smooth):
            p.use_smooth=smooth
            for li,co in zip(p.loop_indices,list(reversed(uv)) if reverse else uv): layer.data[li].uv=co
        # Includes the installed FBX and inherited mechanical components.
        bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
        data.update(); assert all(p.area>1e-10 for p in data.polygons)
        return data


def leaf_mesh(source,width,quality,damage,reverse):
    m=Mesh()
    # Racks and rubber wheels preserve the calibrated contacts exactly.
    for ids,ps,sw in components(source):
        if sw!=0 and max(source.vertices[i].co.z for i in ids)<.31:
            m.copy(source,ids,ps,6 if sw==6 else 4)
    # Square timber top/bottom guides and outside frame stay inside X 0..width.
    # Deeper bottom timber closes the infill to the frame while keeping the
    # boards above the catcher's calibrated lower slot (Z <= .17).
    m.box((width/2,.10,.1375),(width,.050,.085),2)
    m.box((width/2,.10,1.88),(width,.050,.050),2)
    for x in (.045,width-.045): m.box((x,.10,1.0),(.090,.050,1.71),2)
    if width==4: m.box((2,.10,1.0),(.090,.050,1.71),2)
    # Crossbars are behind the boards; front/outward is +Y.
    for z in (.43,1.73): m.box((width/2,.095,z),(width-.10,.038,.11),2)
    count=width*7; span=width-.18; pitch=span/count
    broken=[]
    for i in range(count):
        # The same deterministic break set grows between damage stages.
        fractured=damage>0 and (i%7 in ((2,5) if damage==1 else (1,2,4,5)))
        if fractured: broken.append(i)
        x=.09+(i+.5)*pitch
        gap={'low':.034,'medium':.013,'high':.004}[quality]
        if quality=='medium': gap=.010+.028*(.5+.5*math.sin(i*2.17))
        w=pitch-gap
        tilt=(.027*math.sin(i*2.3) if quality=='low' else .019*math.sin(i*1.9) if quality=='medium' and i%3!=0 else 0)
        if quality=='medium': tilt=max(-gap/2+.002,min(gap/2-.002,tilt))
        bottom=.18
        top=1.795+(.014*math.sin(i*2.7) if quality=='low' else .010)
        sw=(i*3+1)%4 if quality=='low' else i%2 if quality=='medium' else 0
        left,right=x-w/2,x+w/2
        def outline(z0,z1,jagged_bottom=False,jagged_top=False):
            pts=[(left,z0),(right,z0),(right+tilt,z1),(left+tilt,z1)]
            if jagged_top:
                pts=[(left,z0),(right,z0),(right+tilt,z1-.015),
                     (x+w*.24+tilt,z1+.035),(x+tilt,z1-.026),(left+tilt,z1+.013)]
            if jagged_bottom:
                pts=[(left,z0+.02),(x-w*.24,z0-.018),(x,z0+.04),(right,z0),
                     (right+tilt,z1),(left+tilt,z1)]
            return pts
        if fractured:
            split=.99+.075*math.sin(i*2.1)
            # The anchored ends stay on both crossbars; broken ends lean outward.
            for upper,pts in ((False,outline(bottom,split-.012,jagged_top=True)),
                              (True,outline(split+.022,top,jagged_bottom=True))):
                start=len(m.v);m.prism(pts,.120,.150,sw)
                for j in range(start,len(m.v)):
                    px,py,pz=m.v[j]
                    envelope=max(0,1-abs(pz-split)/.68)
                    m.v[j]=(px,py+(.065 if damage==1 else .11)*envelope,pz)
        else: m.prism(outline(bottom,top),.120,.150,sw)
        # Two visible fastening points on both supporting crossbars.
        for z in (.43,1.73): m.box((x,.153,z),(.013,.006,.013),7)
    # One diagonal per two-cell bay, inside the calibrated Y clearance.
    for bay in range(width//2):
        left=.09 if bay==0 else bay*2+.045
        right=width-.09 if bay==width//2-1 else (bay+1)*2-.045
        bounds=(left,right,.18,1.855)
        corner_a=Vector((left,.085,.18));corner_b=Vector((right,.085,1.855))
        extension=(corner_b-corner_a).normalized()*.12
        a=corner_a-extension;b=corner_b+extension
        if damage==3:
            middle=a.lerp(b,.52)
            m.beam(a,middle-Vector((.025,0,.04)),.095,.025,2,bounds)
            m.beam(middle+Vector((.025,0,.04)),b,.095,.025,2,bounds)
            # Small surviving timber splinter links the fractured brace.
            m.beam(middle-Vector((.04,0,.025)),middle+Vector((.04,0,.025)),.012,.015,1)
        else: m.beam(a,b,.095,.025,2,bounds)
    handle_count=1 if width==2 else 2
    for k in range(handle_count):
        x=.085 if k==0 else width-.085
        z=.98 + ((-.055 if k else .045) if quality=='low' else 0)
        angle=math.radians(9 if k==0 else -7) if quality=='low' else 0
        def transform(p):
            # Native plate long axis X becomes vertical, local Z becomes outward Y.
            dx,dz=p.y*.020,p.x*.020
            return Vector((x+math.cos(angle)*dx+math.sin(angle)*dz,.155+p.z*.020,
                           z-math.sin(angle)*dx+math.cos(angle)*dz))
        m.copy(KNOB,list(range(len(KNOB.vertices))),list(KNOB.polygons),5,transform,True)
    data=m.finish('SG_Wood_Leaf',reverse)
    xs=[v.co.x*(-1 if reverse else 1) for v in data.vertices]
    assert min(xs)>-1e-6 and max(xs)<width+1e-6
    return data,broken


def static_mesh(source,name,reverse):
    m=Mesh()
    for ids,ps,sw in components(source):
        # Replace structural steel with timber, preserve rubber and small fasteners.
        fastener=sw==5 and len(ids) in (12,16,20)
        new=6 if sw==6 else 7 if fastener else 2
        if 'Drive' in name:
            # Wooden mounting plinth; motor enclosure/gearbox remain metal.
            new=2 if min(source.vertices[i].co.z for i in ids)<.001 else (6 if sw==6 else 4)
        # Timber bracket gussets end behind the top guide's running surface.
        transform=(lambda p: Vector((p.x,min(p.y,.069),p.z))) if len(ids)==6 else None
        m.copy(source,ids,ps,new,transform)
    return m.finish(name,reverse)


reports=[]
for width in (2,4):
    canonical=bpy.data.scenes['SG_ChainLink'+('_4' if width==4 else '')+'_Workbench']
    source_rig=next(o for o in canonical.objects if o.type=='ARMATURE' and o.get('gate_width_cells')==width)
    source_leaf=next(o for o in canonical.objects if o.type=='MESH' and o.parent==source_rig)
    for reverse in (False,True):
        source=bpy.data.scenes['SG_ChainLink'+('_4' if width==4 else '')+('_Reverse' if reverse else '')+'_Workbench']
        old_rig=next(o for o in source.objects if o.type=='ARMATURE' and o.get('gate_width_cells')==width)
        for quality in ('high','medium','low'):
            for damage in range(4):
                label=f'SG_Wood_{width}_{quality}'+('_Reverse' if reverse else '')+(f'_Damage{damage}' if damage else '')
                scene=bpy.data.scenes.new(label+'_Workbench')
                scene['sg_material']='wood';scene['sg_quality']=quality;scene['sg_damage']=damage
                scene.render.fps=24;scene.frame_start=1;scene.frame_end=width*36+1
                scene.world=canonical.world
                rig=old_rig.copy();rig.data=old_rig.data.copy();rig.name=label+'_Rig';scene.collection.objects.link(rig)
                mesh,broken=leaf_mesh(source_leaf.data,width,quality,damage,reverse)
                leaf=bpy.data.objects.new(label+'_Leaf',mesh);scene.collection.objects.link(leaf)
                leaf.parent=rig;mod=leaf.modifiers.new('Rigid leaf','ARMATURE');mod.object=rig
                leaf.vertex_groups.new(name='DoorBone').add(list(range(len(mesh.vertices))),1,'REPLACE')
                leaf['handle_count']=1 if width==2 else 2;leaf['broken_boards']=broken;leaf['broken_diagonal']=damage==3
                leaf['sg_material']='wood'
                for obj in source.objects:
                    if obj.type!='MESH' or obj.parent==old_rig or not obj.name.startswith('SG_'):continue
                    clone=obj.copy();clone.name=label+'_'+obj.name
                    # Input is already mirrored: unmirror, regenerate normals, then mirror once.
                    data=obj.data.copy()
                    if reverse:
                        data.transform(Matrix.Diagonal((-1,1,1,1)));data.flip_normals()
                    clone.data=static_mesh(data,obj.name,reverse);bpy.data.meshes.remove(data)
                    scene.collection.objects.link(clone)
                    clone['wood_static']=('CatcherPost' if 'Post_Left' in obj.name else 'GuidePost' if 'Post_Right' in obj.name else 'Drive' if 'Drive' in obj.name else 'Rail')
                    clone['export_static']=width==2 and quality=='high' and damage==0 and ('Preview' not in obj.name)
                bpy.context.window.scene=scene
                ad=rig.animation_data
                for t in ad.nla_tracks:t.mute=True
                ad.action=ad.nla_tracks[0].strips[0].action;ad.action_slot=ad.nla_tracks[0].strips[0].action_slot
                scene.frame_set(1)
                reports.append(dict(scene=scene.name,width=width,quality=quality,damage=damage,reverse=reverse,
                    broken_boards=broken,broken_diagonal=damage==3,handle_count=leaf['handle_count'],vertices=len(mesh.vertices)))
with open(os.path.join(ART,'wood_build_checks.json'),'w',encoding='utf-8') as f:json.dump(reports,f,indent=2)
bpy.context.window.scene=bpy.data.scenes['SG_Wood_4_high_Workbench']
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART,'SG_ChainLink.blend'))
print('WOOD_BUILT',len(reports),'workbenches, originals preserved')
