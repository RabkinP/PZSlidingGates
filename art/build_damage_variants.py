"""Run in source Blender via MCP; add three damage stages per existing leaf.

Never rebuild originals. Break only short wire spans; retain crossing wires.
All offsets face away from the post. Mechanical components remain byte-identical.
"""
import bpy
import bmesh
import math
import json
import os
import hashlib
from mathutils import Vector

ART = r'E:\git\SlidingGates\art'
assert bpy.data.filepath == os.path.join(ART, 'SG_ChainLink.blend')
sources = [s for s in bpy.data.scenes if s.name.endswith('_Workbench') and
           any(o.type == 'ARMATURE' and o.get('gate_width_cells') for o in s.objects)
           and not s.get('sg_damage')]
assert len(sources) == 12
assert not any(s.get('sg_damage') for s in bpy.data.scenes), 'Damage workbenches already exist'
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART, 'SG_ChainLink_before_damage.blend'), copy=True)
previous = bpy.context.window.scene


def fingerprint(mesh):
    return hashlib.sha256(repr(([tuple(v.co) for v in mesh.vertices],
                               [tuple(p.vertices) for p in mesh.polygons])).encode()).hexdigest()


def components(mesh):
    adj = [set() for _ in mesh.vertices]
    for e in mesh.edges:
        a, b = e.vertices; adj[a].add(b); adj[b].add(a)
    seen = set()
    for v in mesh.vertices:
        if v.index in seen: continue
        todo, ids = [v.index], set()
        while todo:
            i = todo.pop()
            if i in ids: continue
            ids.add(i); todo.extend(adj[i] - ids)
        seen.update(ids)
        yield sorted(ids)


def orient_shells(mesh):
    bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    labels={};centers=[]
    for ids in components(mesh):
        ci=len(centers);centers.append(sum((mesh.vertices[i].co for i in ids),Vector())/len(ids))
        for i in ids:labels[i]=ci
    volumes=[0.0]*len(centers);mesh.calc_loop_triangles()
    for t in mesh.loop_triangles:
        ci=labels[t.vertices[0]];c=centers[ci]
        a,b,d=[mesh.vertices[i].co-c for i in t.vertices]
        volumes[ci]+=a.dot(b.cross(d))/6
    negative={i for i,v in enumerate(volumes) if v<0}
    if negative:
        bm=bmesh.new();bm.from_mesh(mesh);bm.verts.index_update()
        bmesh.ops.reverse_faces(bm,faces=[f for f in bm.faces if labels[f.verts[0].index] in negative])
        bm.to_mesh(mesh);bm.free()


def damage_mesh(source, width, reverse, stage):
    sign = -1 if reverse else 1
    vs, faces, uvs, smooth = [], [], [], []
    polygons = {}
    for p in source.polygons: polygons.setdefault(p.vertices[0], []).append(p)
    patches = [(width*.28, .78), (width*.67, 1.25), (width*.49, 1.57)]
    broken = 0; preserved = 0; max_gap = 0
    def face(ids, uv, shading):
        faces.append(tuple(ids)); uvs.append(uv); smooth.append(shading)
    def wireface(ids, uv, shading):
        face(tuple(reversed(ids)) if reverse else ids, uv, shading)
    for ci, ids in enumerate(components(source)):
        ps = [p for i in ids for p in polygons.get(i, [])]
        pts = [source.vertices[i].co.copy() for i in ids]
        x = [sign*p.x for p in pts]
        uv0 = source.uv_layers.active.data[ps[0].loop_indices[0]].uv
        sw = int(uv0.x*4)+4*int(uv0.y*2)
        wire = len(ids) in (12, 54) and sw in (1, 4) and max(p.z for p in pts)-min(p.z for p in pts) > .05
        if wire:
            # Existing meshes have contiguous six-vertex cylinder rings.
            nr = len(pts)//6
            centers = [sum(pts[k*6:(k+1)*6], Vector())/6 for k in range(nr)]
            length = sum((b-a).length for a,b in zip(centers, centers[1:]))
            steps = max(32, math.ceil(length/.045))
            rings = []; influence = []
            for k in range(steps+1):
                t=k/steps; f=t*(nr-1); n=min(int(f),nr-2); u=f-n
                center=centers[n].lerp(centers[n+1],u)
                px=sign*center.x
                local=max(math.exp(-((px-cx)**2+(center.z-cz)**2)/.20) for cx,cz in patches)
                # Broad folded panels, anchored to the perimeter. The same field
                # moves crossing wires together instead of opening a passage.
                envelope=min(1,max(0,(px-.08)/.25),max(0,(width-.08-px)/.25),
                             max(0,(center.z-.40)/.24),max(0,(1.55-center.z)/.30))
                dx=(.10,.20,.30)[stage-1]*local*envelope*math.sin(center.z*7+px*2)
                dz=-(.06,.13,.22)[stage-1]*local*envelope*(.5+.5*math.sin(px*5+center.z*3))
                dy=(.12,.26,.43)[stage-1]*local*envelope
                ring=[]
                for j in range(6):
                    p=pts[n*6+j].lerp(pts[(n+1)*6+j],u)
                    p.x+=sign*dx; p.z+=dz; p.y+=dy
                    ring.append(len(vs));vs.append(p)
                rings.append(ring);influence.append(local)
            # At most one short gap on alternating wires: crossing infill remains.
            candidates=[k for k in range(2,steps-2) if (vs[rings[k+1][0]]-vs[rings[k][0]]).length<.065]
            cut = max(candidates,key=lambda k:influence[k]) if candidates else 2
            tear = bool(candidates) and stage>=2 and ci%2==0 and influence[cut]>(.80 if stage==2 else .55)
            for k in range(steps):
                if tear and k==cut:
                    broken+=1;max_gap=max(max_gap,(vs[rings[k+1][0]]-vs[rings[k][0]]).length)
                    continue
                for j in range(6):
                    a,b=rings[k],rings[k+1];n=(j+1)%6
                    wireface((a[j],a[n],b[n],b[j]),[(uv0.x,uv0.y)]*4,True)
            wireface(tuple(reversed(rings[0])),[(uv0.x,uv0.y)]*6,False)
            wireface(tuple(rings[-1]),[(uv0.x,uv0.y)]*6,False)
            if tear:
                wireface(tuple(rings[cut]),[(uv0.x,uv0.y)]*6,False)
                wireface(tuple(reversed(rings[cut+1])),[(uv0.x,uv0.y)]*6,False)
        else:
            start=len(vs);remap={old:start+j for j,old in enumerate(ids)}
            internal=(sw in (0,4) and len(ids) in (16,72) and max(x)-min(x)<.30
                      and min(x)>.2 and max(x)<width-.2 and max(p.z for p in pts)-min(p.z for p in pts)>1.7)
            if internal:
                # Original high-quality uprights only had endpoint rings: just
                # moving their existing vertices could not bend them at all.
                nr=len(pts)//8;steps=24;rings=[]
                for k in range(steps+1):
                    t=k/steps;f=t*(nr-1);n=min(int(f),nr-2);u=f-n
                    center=pts[n*8].lerp(pts[(n+1)*8],u)
                    envelope=math.sin(math.pi*t)*min(1,max(0,(center.z-.40)/.24),max(0,(1.55-center.z)/.30))
                    ring=[]
                    for j in range(8):
                        p=pts[n*8+j].lerp(pts[(n+1)*8+j],u)
                        p.x+=sign*(.07,.16,.28)[stage-1]*envelope*math.sin(t*4+sign*p.x*4)
                        p.y+=(.04,.10,.18)[stage-1]*envelope
                        ring.append(len(vs));vs.append(p)
                    rings.append(ring)
                for k in range(steps):
                    for j in range(8):
                        a,b=rings[k],rings[k+1];n=(j+1)%8
                        wireface((a[j],a[n],b[n],b[j]),[(uv0.x,uv0.y)]*4,True)
                wireface(tuple(reversed(rings[0])),[(uv0.x,uv0.y)]*8,False)
                wireface(tuple(rings[-1]),[(uv0.x,uv0.y)]*8,False)
                continue
            for p in pts:
                vs.append(p)
            if not internal:preserved+=len(ids)
            for p in ps:
                face([remap[i] for i in p.vertices],
                     [tuple(source.uv_layers.active.data[li].uv) for li in p.loop_indices],p.use_smooth)
    mesh=bpy.data.meshes.new(source.name+'_Damage'+str(stage))
    mesh.from_pydata(vs,[],faces);mesh.update()
    for mat in source.materials:mesh.materials.append(mat)
    uv=mesh.uv_layers.new(name='AtlasUV')
    for p,coords,shading in zip(mesh.polygons,uvs,smooth):
        p.use_smooth=shading
        for li,co in zip(p.loop_indices,coords):uv.data[li].uv=co
    # Some inherited quality scrap straps had inward winding. Correct all
    # closed shells without changing positions, smoothing or atlas UVs.
    orient_shells(mesh)
    # Source forward and mirrored winding is retained by ring index order.
    assert all(p.area>1e-10 for p in mesh.polygons)
    assert min(sign*v.co.x for v in mesh.vertices)>=-1e-6
    assert max(sign*v.co.x for v in mesh.vertices)<=width+1e-6
    assert max_gap<.065, max_gap
    return mesh,dict(broken_wire_spans=broken,max_removed_span=max_gap,mechanical_vertices_preserved=preserved)


reports=[]
for source in sources:
    original_rig=next(o for o in source.objects if o.type=='ARMATURE' and o.get('gate_width_cells'))
    original_leaf=next(o for o in source.objects if o.type=='MESH' and o.parent==original_rig)
    width=int(original_rig['gate_width_cells']);reverse=original_rig.get('gate_direction')=='reverse'
    before=fingerprint(original_leaf.data)
    for stage in (1,2,3):
        scene=bpy.data.scenes.new(source.name.replace('_Workbench',f'_Damage{stage}_Workbench'))
        scene.render.fps=source.render.fps;scene.frame_start=source.frame_start;scene.frame_end=source.frame_end
        scene.world=source.world;scene['sg_damage']=stage;scene['sg_quality']=source.get('sg_quality','high')
        clones={}
        for obj in source.objects:
            if obj!=original_rig and not (obj.type=='MESH' and obj.name.startswith('SG_')):continue
            clone=obj.copy();clone.name=obj.name+f'_Damage{stage}'
            if obj==original_rig:clone.data=obj.data.copy()
            if obj==original_leaf:clone.data,report=damage_mesh(obj.data,width,reverse,stage)
            scene.collection.objects.link(clone);clones[obj]=clone
        rig,leaf=clones[original_rig],clones[original_leaf];leaf.parent=rig
        for mod in leaf.modifiers:
            if mod.type=='ARMATURE':mod.object=rig
        group=leaf.vertex_groups.get('DoorBone') or leaf.vertex_groups.new(name='DoorBone')
        group.add(list(range(len(leaf.data.vertices))),1,'REPLACE')
        bpy.context.window.scene=scene;scene.frame_set(1)
        report.update(scene=scene.name,width=width,reverse=reverse,quality=scene['sg_quality'],stage=stage,
                      source_sha256=before,vertices=len(leaf.data.vertices))
        reports.append(report);print(json.dumps(report))
    assert fingerprint(original_leaf.data)==before
bpy.context.window.scene=previous
with open(os.path.join(ART,'damage_checks.json'),'w') as f:json.dump(reports,f,indent=2)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART,'SG_ChainLink.blend'))
print('DAMAGE_WORKBENCHES',len(reports))
