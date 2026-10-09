"""Run in the live source Blender via MCP. Adds workbenches, never rebuilds originals.

Quality is an independent art variant, not an animation state. No game registration
or skill thresholds are changed here. Static mechanical parts and export anchors
are reused; the original high-quality leaf is kept intact.
"""
import bpy
import math
import json
import os
import hashlib
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ART = r'E:\git\SlidingGates\art'
assert bpy.data.filepath == os.path.join(ART, 'SG_ChainLink.blend')
SOURCES = [(2, False, 'SG_ChainLink_Workbench'),
           (4, False, 'SG_ChainLink_4_Workbench'),
           (2, True, 'SG_ChainLink_Reverse_Workbench'),
           (4, True, 'SG_ChainLink_4_Reverse_Workbench')]
assert all(name.replace('_Workbench', '_' + quality + '_Workbench') not in bpy.data.scenes
           for _, _, name in SOURCES for quality in ('Low', 'Medium')), 'Variants already exist: edit them instead'
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART, 'SG_ChainLink_before_quality.blend'), copy=True)


def fingerprint(mesh):
    return hashlib.sha256(repr(([(tuple(v.co)) for v in mesh.vertices],
                               [tuple(p.vertices) for p in mesh.polygons],
                               [tuple(u.uv) for u in mesh.uv_layers.active.data])).encode()).hexdigest()


def components(mesh):
    adj = [set() for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        adj[a].add(b); adj[b].add(a)
    seen = set()
    for vertex in mesh.vertices:
        if vertex.index in seen: continue
        todo, ids = [vertex.index], set()
        while todo:
            i = todo.pop()
            if i in ids: continue
            ids.add(i); todo.extend(adj[i] - ids)
        seen.update(ids)
        yield sorted(ids)


def quality_mesh(source, width, quality, reverse):
    # Work in the canonical positive-X leaf, then reflect vertices and winding.
    sign = -1 if reverse else 1
    low = quality == 'Low'
    vs, fs, uvs, smooth = [], [], [], []
    def face(ids, sw, smoothing=False, exact_uv=None):
        fs.append(tuple(reversed(ids)) if reverse else tuple(ids))
        cx, cy = (sw % 4 + .5) / 4, (sw // 4 + .5) / 2
        uv = exact_uv or [(cx + (-.07 if j % 2 == 0 else .07), cy + (-.15 if j < 2 else .15)) for j in range(len(ids))]
        uvs.append(list(reversed(uv)) if reverse else uv); smooth.append(smoothing)
    def coord(i):
        p = source.vertices[i].co.copy(); p.x *= sign
        return p
    def sweep(points, radius, sw, sides=8):
        start = len(vs)
        for k, p in enumerate(points):
            tangent = (points[min(k+1, len(points)-1)] - points[max(0, k-1)]).normalized()
            u = tangent.cross(Vector((0, 1, 0))).normalized(); v = tangent.cross(u)
            for j in range(sides):
                vs.append(p + radius*(u*math.cos(j*2*math.pi/sides) + v*math.sin(j*2*math.pi/sides)))
        for k in range(len(points)-1):
            for j in range(sides):
                base = start+k*sides; nxt = (j+1) % sides
                face((base+j, base+nxt, base+sides+nxt, base+sides+j), sw, True)
        face(tuple(start+j for j in range(sides-1,-1,-1)), sw)
        base = start+(len(points)-1)*sides
        face(tuple(base+j for j in range(sides)), sw)
    def plate(a, b, thickness, depth, sw):
        # Flat scrap strap with outward winding and deliberate flat shading.
        a, b = Vector(a), Vector(b); d = (b-a).normalized()
        u = Vector((-d.z, 0, d.x))*thickness/2; v = Vector((0, depth/2, 0))
        start = len(vs)
        for p in (a,b): vs.extend((p-u-v, p+u-v, p+u+v, p-u+v))
        face((start+3,start+2,start+1,start),sw)
        face((start+4,start+5,start+6,start+7),sw)
        for j in range(4):
            n=(j+1)%4;face((start+j,start+n,start+4+n,start+4+j),sw)
    preserved = 0
    for ci, ids in enumerate(components(source)):
        member = set(ids)
        polygons = [p for p in source.polygons if p.vertices[0] in member]
        first_uv = source.uv_layers.active.data[polygons[0].loop_indices[0]].uv
        sw = int(first_uv.x*4)+4*int(first_uv.y*2)
        pts = [coord(i) for i in ids]
        xmin, xmax = min(p.x for p in pts), max(p.x for p in pts)
        interior = sw == 0 and xmax-xmin < .051 and xmin > .2 and xmax < width-.2
        if sw == 1:
            # Subdivide the original wire rings, preserving both end rings exactly.
            assert len(ids) == 12, ('Unexpected wire topology', len(ids))
            start = len(vs); steps = 8
            for k in range(steps+1):
                t = k/steps
                for j in range(6):
                    p = pts[j].lerp(pts[j+6], t)
                    boundary = min(1, max(0, (p.z-.36)/.24), max(0,(1.76-p.z)/.2),
                                   max(0,(p.x-.12)/.18),max(0,(width-.12-p.x)/.18))
                    envelope = math.sin(math.pi*t)*boundary
                    p.x += (.075 if low else .025)*envelope*math.sin(p.z*8.1+p.x*3.2)
                    p.z += (.047 if low else .016)*envelope*math.sin(p.x*6.7-p.z*2.1)
                    vs.append(p)
            for k in range(steps):
                for j in range(6):
                    n=(j+1)%6; base=start+k*6
                    face((base+j,base+n,base+6+n,base+6+j), 1 if not low or ci%5 else 4, True)
            face(tuple(start+j for j in range(5,-1,-1)),1)
            face(tuple(start+steps*6+j for j in range(6)),1)
        elif interior:
            x=(xmin+xmax)/2
            points=[]
            for k in range(9):
                t=k/8; z=.12+1.76*t
                dx=(.105 if low else .038)*math.sin(math.pi*t)*math.sin(4*t+x)
                points.append(Vector((x+dx,.10,z)))
            sweep(points,.025,4 if low and round(x)%2 else 0)
            # Rough welded splice sleeve around the bent internal tube.
            t=.43; z=.12+1.76*t
            xsplice=x+(.105 if low else .038)*math.sin(math.pi*t)*math.sin(4*t+x)
            plate((xsplice-.07,.139,z-.055),(xsplice+.07,.139,z+.065),.105 if low else .055,.009,2)
        else:
            start=len(vs); remap={old:start+j for j,old in enumerate(ids)};vs.extend(pts)
            for p in polygons:
                order=list(p.vertices)
                exact=[tuple(source.uv_layers.active.data[li].uv) for li in p.loop_indices]
                # Unmirror source face order before the common reflection below.
                if reverse: order.reverse();exact.reverse()
                face([remap[i] for i in order], sw, p.use_smooth, exact)
            preserved += len(ids)
    # Salvaged diagonal reinforcement welded to the frame, on its outward face.
    if low:
        for cell in range(width):
            left=.025 if cell==0 else cell
            right=width-.025 if cell==width-1 else cell+1
            plate((left,.150,.52+.06*(cell%2)),(right,.150,1.40-.09*(cell%2)),.045,.012,4 if cell%2==0 else 2)
            # Small rough gussets at brace/frame contacts.
            for x,z in ((left+.035,.58+.06*(cell%2)),(right-.035,1.34-.09*(cell%2))):
                plate((x,.151,z-.085),(x+.025,.151,z+.085),.070,.015,2)
    mesh=bpy.data.meshes.new(source.name+'_'+quality)
    mesh.from_pydata([(sign*p.x,p.y,p.z) for p in vs], [], fs);mesh.update()
    for mat in source.materials:mesh.materials.append(mat)
    uv=mesh.uv_layers.new(name='AtlasUV')
    for p, coords, shading in zip(mesh.polygons,uvs,smooth):
        p.use_smooth=shading
        for li,co in zip(p.loop_indices,coords):uv.data[li].uv=co
    assert all(p.area>1e-10 for p in mesh.polygons)
    xs=[sign*v.co.x for v in mesh.vertices]
    assert min(xs)>=-1e-6 and max(xs)<=width+1e-6
    return mesh,preserved


reports=[]
original_hashes={}
for width,reverse,source_name in SOURCES:
    source=bpy.data.scenes[source_name]
    original_rig=next(o for o in source.objects if o.type=='ARMATURE' and o.get('gate_width_cells')==width)
    original_leaf=next(o for o in source.objects if o.type=='MESH' and o.parent==original_rig)
    original_hashes[source_name]=fingerprint(original_leaf.data)
    for quality in ('Medium','Low'):
        scene=bpy.data.scenes.new(source_name.replace('_Workbench','_'+quality+'_Workbench'))
        scene.render.fps=source.render.fps
        scene.frame_start,scene.frame_end=source.frame_start,source.frame_end
        scene.world=source.world
        clones={}
        for obj in source.objects:
            if obj!=original_rig and not (obj.type=='MESH' and obj.name.startswith('SG_')):continue
            clone=obj.copy();clone.name=obj.name+'_'+quality
            if obj==original_rig:clone.data=obj.data.copy()
            if obj==original_leaf:clone.data,preserved=quality_mesh(obj.data,width,quality,reverse)
            scene.collection.objects.link(clone);clones[obj]=clone
        rig,leaf=clones[original_rig],clones[original_leaf]
        leaf.parent=rig
        for mod in leaf.modifiers:
            if mod.type=='ARMATURE':mod.object=rig
        group=leaf.vertex_groups.get('DoorBone') or leaf.vertex_groups.new(name='DoorBone')
        group.add(list(range(len(leaf.data.vertices))),1,'REPLACE')
        leaf['sg_quality']=quality.lower();scene['sg_quality']=quality.lower()
        scene['SG_notes']='Quality art variant; unchanged mechanical paths; deployment managed by tools/register_quality_models.py.'
        bpy.context.window.scene=scene
        fixed=[o for o in scene.objects if o.type=='MESH' and o!=leaf]
        def tree(obj,verts=None):
            return BVHTree.FromPolygons(verts if verts is not None else [obj.matrix_world@v.co for v in obj.data.vertices], [list(p.vertices) for p in obj.data.polygons])
        bpy.context.view_layer.update();trees=[(o.name,tree(o)) for o in fixed]
        checked=0
        for track in rig.animation_data.nla_tracks:
            for t in rig.animation_data.nla_tracks:t.mute=True
            rig.animation_data.action=track.strips[0].action
            rig.animation_data.action_slot=track.strips[0].action_slot
            for frame in range(1,scene.frame_end+1):
                scene.frame_set(frame)
                loc=rig.pose.bones['DoorBone'].location
                assert abs(loc.y)<1e-6 and abs(loc.z)<1e-6
                shift=(-1 if reverse else 1)*loc.x
                assert -1e-5<=shift<=width+1e-5
                assert any(shift+.047<=x<=shift+width-.047 for x in (width-.12,width+.12))
                deps=bpy.context.evaluated_depsgraph_get();e=leaf.evaluated_get(deps)
                moving=tree(leaf,[e.matrix_world@v.co for v in e.data.vertices])
                for name,fixed_tree in trees:assert not moving.overlap(fixed_tree),(scene.name,track.name,frame,name)
                checked+=1
        rig.animation_data.action=rig.animation_data.nla_tracks[0].strips[0].action
        rig.animation_data.action_slot=rig.animation_data.nla_tracks[0].strips[0].action_slot
        scene.frame_set(1)
        report=dict(scene=scene.name,width=width,quality=quality.lower(),reverse=reverse,
                    frames_checked=checked,surface_collisions=0,mechanical_vertices_preserved=preserved,
                    vertices=len(leaf.data.vertices),source_leaf_sha256=original_hashes[source_name],
                    full_weight_DoorBone=True,rail_capture=True,gameplay_registered=False)
        reports.append(report);print(json.dumps(report))

for _,_,name in SOURCES:
    s=bpy.data.scenes[name];r=next(o for o in s.objects if o.type=='ARMATURE' and 'gate_width_cells' in o)
    g=next(o for o in s.objects if o.type=='MESH' and o.parent==r)
    assert fingerprint(g.data)==original_hashes[name],('Source changed',name)
with open(os.path.join(ART,'quality_checks.json'),'w',encoding='utf-8') as file:json.dump(reports,file,indent=2)
bpy.context.window.scene=bpy.data.scenes['SG_ChainLink_Low_Workbench']
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART,'SG_ChainLink.blend'))
print('QUALITY_VARIANTS_SAVED',len(reports))
