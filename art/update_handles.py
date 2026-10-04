"""Run through Blender MCP: replace only handle fittings, keep all other art."""
import bpy, math, os, json, io, contextlib
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=r'E:\git\SlidingGates\art'
assert bpy.data.filepath==os.path.join(ROOT,'SG_ChainLink.blend')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'SG_ChainLink_before_vertical_handles.blend'),copy=True)
previous=bpy.context.window.scene
source=open(os.path.join(ROOT,'build_chainlink.py'),encoding='utf-8').read()
reports=[]
for width,name in [(2,'SG_ChainLink_Workbench'),(4,'SG_ChainLink_4_Workbench')]:
    scene=bpy.data.scenes[name]; bpy.context.window.scene=scene
    rig=next(o for o in scene.objects if o.type=='ARMATURE' and 'gate_width_cells' in o)
    gate=next(o for o in scene.objects if o.type=='MESH' and o.parent==rig)
    data=gate.data; uv=data.uv_layers.active
    keep=[]; removed=set(); crossmember_faces=0
    for p in data.polygons:
        u,v=uv.data[p.loop_indices[0]].uv; sw=int(u*4)+4*int(v*2)
        if sw in (2,5) and all(.7999<=data.vertices[i].co.z<=1.1001 for i in p.vertices):
            removed.update(p.vertices)
        elif sw==0 and all(.9274<=data.vertices[i].co.z<=.9726 for i in p.vertices):
            removed.update(p.vertices); crossmember_faces+=1
        else: keep.append(p)
    # Copy all retained vertices/faces/UV exactly; no rebuilding the gate.
    ids=sorted({i for p in keep for i in p.vertices}); remap={old:new for new,old in enumerate(ids)}
    mesh=bpy.data.meshes.new(data.name+'_NewHandles')
    mesh.from_pydata([tuple(data.vertices[i].co) for i in ids],[],[[remap[i] for i in p.vertices] for p in keep])
    mesh.update()
    for mat in data.materials:mesh.materials.append(mat)
    newuv=mesh.uv_layers.new(name='AtlasUV')
    for p,old in zip(mesh.polygons,keep):
        p.use_smooth=old.use_smooth; p.material_index=old.material_index
        for li,oldli in zip(p.loop_indices,old.loop_indices):newuv.data[li].uv=uv.data[oldli].uv
    # Restore exact rack-backbone end bounds: an earlier clearance migration
    # treated its lower corners as tooth vertices because both share Z=.26.
    rack_indices=set()
    for p in mesh.polygons:
        u,v=newuv.data[p.loop_indices[0]].uv
        if int(u*4)+4*int(v*2)==2 and all(.2599<=mesh.vertices[i].co.z<=.3001 for i in p.vertices):
            rack_indices.update(p.vertices)
    for i in rack_indices:mesh.vertices[i].co.x=0 if mesh.vertices[i].co.x<width/2 else width
    gate.data=mesh
    env={'bpy':bpy,'math':math,'Vector':Vector,'WIDTH':width,'CLEARANCE':.10,
         'col':gate.users_collection[0],'mat':mesh.materials[0]}
    exec(source[source.index('def rod('):source.index('def leaf(')],env)
    def grips(v,f,s):
        env['handle'](.025 if width==2 else width-.025,v,f,s)
        if width==4:env['handle'](.025,v,f,s)
    extra=env['mesh']('SG_HandlePolish',grips)
    for v in extra.data.vertices:v.co.y+=.10
    # The entire new fitting is on the same outward face, safely beyond posts.
    assert min(v.co.y for v in extra.data.vertices)>.120
    for o in bpy.context.view_layer.objects:o.select_set(False)
    gate.select_set(True); extra.select_set(True); bpy.context.view_layer.objects.active=gate
    bpy.ops.object.join()
    group=gate.vertex_groups.get('DoorBone') or gate.vertex_groups.new(name='DoorBone')
    group.add(list(range(len(gate.data.vertices))),1,'REPLACE')
    assert min(v.co.x for v in gate.data.vertices)>=-1e-6
    assert max(v.co.x for v in gate.data.vertices)<=width+1e-6
    gate['handle_style']='rounded_pull_with_two_standoffs'
    static=[o for o in scene.objects if o.type=='MESH' and any(t in o.name for t in ('Post_Left','Post_Right','Drive','Rail_'))]
    def tree(obj,verts=None):
        return BVHTree.FromPolygons(verts if verts is not None else [obj.matrix_world@v.co for v in obj.data.vertices],
                                   [list(p.vertices) for p in obj.data.polygons])
    bpy.context.view_layer.update(); trees=[(o.name,tree(o)) for o in static]
    count=0
    for track in rig.animation_data.nla_tracks:
        for t in rig.animation_data.nla_tracks:t.mute=True
        rig.animation_data.action=track.strips[0].action
        for frame in range(1,scene.frame_end+1):
            scene.frame_set(frame); deps=bpy.context.evaluated_depsgraph_get(); e=gate.evaluated_get(deps)
            moving=tree(gate,[e.matrix_world@v.co for v in e.data.vertices])
            for obj_name,fixed in trees:assert not moving.overlap(fixed),(width,track.name,frame,obj_name)
            count+=1
    reports.append({'width':width,'handles':2 if width==4 else 1,'frames_checked':count,'surface_collisions':0,
                    'grip_diameter':.028,'hand_gap':.053,'mount':'outer_vertical_frame',
                    'handle_x':[width-.025,.025] if width==4 else [.025],
                    'crossmember_faces_removed':crossmember_faces})
    log=io.StringIO()
    with contextlib.redirect_stdout(log):
        exec(compile(open(os.path.join(ROOT,'export_chainlink.py'),encoding='utf-8').read(),'export_chainlink.py','exec'),{})
bpy.context.window.scene=previous
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'SG_ChainLink.blend'))
with open(os.path.join(ROOT,'handle_checks.json'),'w',encoding='utf-8') as f:json.dump(reports,f,indent=2)
print(json.dumps(reports))
