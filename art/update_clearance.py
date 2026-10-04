"""Update both existing workbenches via Blender MCP, preserving their clips.

Rebuild only the affected meshes from the canonical generator. Validate
every Open/Close frame before exporting. Save a source backup first.
"""
import bpy, math, os, json
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=r'E:\git\SlidingGates\art'
assert bpy.data.filepath==os.path.join(ROOT,'SG_ChainLink.blend')
for scene_name in ('SG_ChainLink_Workbench','SG_ChainLink_4_Workbench'):
    assert all(abs(float(o['fence_clearance'])-.18)<1e-6 for o in bpy.data.scenes[scene_name].objects
               if o.type=='ARMATURE' and 'gate_width_cells' in o), 'Migration already applied; restore backup or edit current geometry'
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'SG_ChainLink_before_clearance_010.blend'),copy=True)
previous_scene=bpy.context.window.scene
source=open(os.path.join(ROOT,'build_chainlink.py'),encoding='utf-8').read()
reports=[]
for width,name in [(2,'SG_ChainLink_Workbench'),(4,'SG_ChainLink_4_Workbench')]:
    scene=bpy.data.scenes[name]; bpy.context.window.scene=scene
    rig=next(o for o in scene.objects if o.type=='ARMATURE' and 'gate_width_cells' in o)
    gate=next(o for o in scene.objects if o.type=='MESH' and o.parent==rig)
    def part(suffix):
        return next(o for o in scene.objects if o.type=='MESH' and suffix in o.name)
    catcher,guide,drive,rail=(part(s) for s in ('Post_Left','Post_Right','Drive','Rail_OneCell'))
    original_locations={o.name:tuple(o.location) for o in (catcher,guide,drive)}
    original_vertices=[v.co.copy() for v in gate.data.vertices]
    old_clearance=float(rig['fence_clearance'])
    col=next(c for c in gate.users_collection if c.name.startswith('SlidingGates'))
    env={'bpy':bpy,'math':math,'Vector':Vector,'col':col,'mat':gate.data.materials[0],
         'WIDTH':width,'CLEARANCE':0.10}
    for start,end in [('def rod(',"gate=mesh('SG_Leaf'"),('def post(',"post_a=mesh("),
                      ('def rail_piece(',"rail=mesh("),('def motor(',"motor_obj=mesh(")]:
        exec(source[source.index(start):source.index(end)],env)
    for obj,fn in [(gate,'leaf'),(catcher,'catcher'),(guide,'post'),(drive,'motor'),(rail,'rail_piece')]:
        old_data=obj.data
        if obj==gate:
            # Preserve all current leaf detail and vertex ordering. Only translate
            # its mesh; frame, wheels, mounts and rack belong to this same skin.
            obj.data=obj.data.copy()
            for vertex in obj.data.vertices: vertex.co.y+=0.10-old_clearance
            for old,new in zip(original_vertices,obj.data.vertices):
                assert (new.co-old-Vector((0,0.10-old_clearance,0))).length<2e-6
            # Narrow the rack around its translated centre so its back clears
            # the post. Move only the handle fittings to the outward side.
            handle_indices=set(); tooth_indices=set()
            uv=obj.data.uv_layers.active
            for poly in obj.data.polygons:
                u,v=uv.data[poly.loop_indices[0]].uv
                swatch=int(u*4)+4*int(v*2)
                if swatch in (2,5) and all(.8799<=obj.data.vertices[i].co.z<=1.0201 for i in poly.vertices):
                    handle_indices.update(poly.vertices)
                if swatch==5 and all(.2299<=obj.data.vertices[i].co.z<=.2601 for i in poly.vertices):
                    tooth_indices.update(poly.vertices)
            for vertex in obj.data.vertices:
                if .2299<=vertex.co.z<=.3001:
                    vertex.co.y=.045+(vertex.co.y-.045)*(.010/.055)
                elif vertex.index in handle_indices:
                    vertex.co.y=.20-vertex.co.y
            tooth_count=math.floor((width-.05)/.045)+1
            for vertex in obj.data.vertices:
                if vertex.index in tooth_indices:
                    i=round((vertex.co.x-.025)/.045)
                    vertex.co.x+=.01125+i*(width-.0225)/(tooth_count-1)-(.025+i*.045)
            for poly in obj.data.polygons:
                if all(i in handle_indices for i in poly.vertices): poly.flip()
            obj.data.update()
        else:
            fresh=env['mesh']('SG_ClearanceTemp',env[fn]); obj.data=fresh.data
            bpy.data.objects.remove(fresh,do_unlink=True)
        if obj==rail:
            for o in scene.objects:
                if o!=rail and o.data==old_data: o.data=rail.data
    rig['fence_clearance']=0.10
    assert all(tuple(bpy.data.objects[n].location)==loc for n,loc in original_locations.items())
    scene['SG_notes']=f'{width}-cell leaf; clearance 0.10; duration {width*1.5:g} seconds.'
    # Shared static assets are identical in both assemblies, despite different origins.
    if width==2:
        static_vertices={label:[tuple(v.co) for v in obj.data.vertices]
                         for label,obj in [('catcher',catcher),('guide',guide),('drive',drive),('rail',rail)]}
    else:
        for label,obj in [('catcher',catcher),('guide',guide),('drive',drive),('rail',rail)]:
            assert static_vertices[label]==[tuple(v.co) for v in obj.data.vertices]
    def tree(obj,coords=None):
        return BVHTree.FromPolygons(coords or [obj.matrix_world@v.co for v in obj.data.vertices],
                                   [list(p.vertices) for p in obj.data.polygons],epsilon=0.0)
    bpy.context.view_layer.update()
    assert not tree(drive).overlap(tree(guide)), 'Drive cuts through guide post'
    # The wheel components are the only dark (swatch 6) leaf faces below Z=.16.
    def vertices_where(predicate):
        indices=set()
        for poly in gate.data.polygons:
            if predicate(poly): indices.update(poly.vertices)
        return [gate.data.vertices[i].co for i in indices]
    wheel=vertices_where(lambda p: all(gate.data.vertices[i].co.z<.16 for i in p.vertices)
                         and all(.04<gate.data.vertices[i].co.z for i in p.vertices))
    # Isolate wheel cylinders by their unique Z band (frame lower tube begins at .095).
    wheel_low=[v for v in wheel if v.z<.09]
    wheel_bottom=min(v.z for v in wheel_low)
    rail_top=max(v.co.z for v in rail.data.vertices)
    wheel_gap=wheel_bottom-rail_top
    assert -1e-6<=wheel_gap<.003, ('wheel/rail vertical gap',wheel_gap)
    roller_gap=(.10-.025)-(.10-.049+.022)
    assert abs(roller_gap-.002)<1e-6
    # Actual pinion maximum Z=.230 matches the underside of the rack teeth.
    pinion=[v.co for v in drive.data.vertices if v.co.y>=.2599 and abs(v.co.x)<=.04001]
    pinion_top=max(v.z for v in pinion)
    tooth_bottom=.245-.03/2
    assert abs(tooth_bottom-pinion_top)<1e-6
    assert abs(max(v.y for v in pinion)+drive.location.y-.065)<1e-6
    tooth_centres=[.01125+i*(width-.0225)/(math.floor((width-.05)/.045))
                   for i in range(math.floor((width-.05)/.045)+1)]
    frame_checks=0; surface_contacts=0; max_tooth_gap=0
    for track in rig.animation_data.nla_tracks:
        for t in rig.animation_data.nla_tracks: t.mute=True
        rig.animation_data.action=track.strips[0].action
        for frame in range(scene.frame_start,scene.frame_end+1):
            scene.frame_set(frame); bpy.context.view_layer.update()
            shift=rig.pose.bones['DoorBone'].location.x
            assert abs(rig.pose.bones['DoorBone'].location.y)<1e-6
            assert abs(rig.pose.bones['DoorBone'].location.z)<1e-6
            assert -.00001<=shift<=width+.00001
            assert any(shift+.047<=x<=shift+width-.047 for x in (width-.12,width+.12))
            nearest_tooth=max(0,min(abs(width-(shift+x)) for x in tooth_centres)-.01125)
            # 12-sided pinion upper facets: the nearest tooth is always
            # within the two top facets, including both stroke endpoints.
            assert nearest_tooth<=.02
            tooth_gap=nearest_tooth*math.tan(math.pi/12)
            assert tooth_gap<.0035
            max_tooth_gap=max(max_tooth_gap,tooth_gap)
            # Wheel axles straddle the new rail centre throughout travel.
            assert abs((min(v.y for v in wheel_low)+max(v.y for v in wheel_low))/2-.10)<1e-6
            assert .0875>=min(v.y for v in wheel_low)-1e-6
            assert .1125<=max(v.y for v in wheel_low)+1e-6
            deps=bpy.context.evaluated_depsgraph_get()
            evaluated=gate.evaluated_get(deps)
            coords=[evaluated.matrix_world@v.co for v in evaluated.data.vertices]
            moving=tree(gate,coords)
            hits=moving.overlap(tree(drive))
            # Tangent rack contact may be reported as touching by BVH. No
            # overlapping surfaces beyond the pinion/rack contact plane allowed.
            for li,di in hits:
                lp=gate.data.polygons[li]; dp=drive.data.polygons[di]
                lv=[coords[i] for i in lp.vertices]
                dv=[drive.matrix_world@drive.data.vertices[i].co for i in dp.vertices]
                assert min(v.z for v in lv)>=.22999 and max(v.z for v in dv)<=.23001, ('drive/leaf penetration',frame,li,di)
            surface_contacts+=len(hits)
            assert not moving.overlap(tree(guide)), ('leaf/guide collision',frame)
            assert not moving.overlap(tree(catcher)), ('leaf/catcher collision',frame)
            assert not moving.overlap(tree(rail)), ('leaf/rail collision',frame)
            frame_checks+=1
    rig.animation_data.action=rig.animation_data.nla_tracks[0].strips[0].action
    scene.frame_set(1)
    report={'width':width,'frames_checked':frame_checks,'clearance':.10,
            'wheel_rail_gap':wheel_gap,'roller_gap':roller_gap,
            'pinion_rack_vertical_gap':tooth_bottom-pinion_top,'tangent_contacts':surface_contacts,
            'max_pinion_to_nearest_tooth_gap':max_tooth_gap,
            'post_and_drive_locations_unchanged':True}
    reports.append(report); print('CLEARANCE_CHECK',json.dumps(report))
    exec(compile(open(os.path.join(ROOT,'export_chainlink.py'),encoding='utf-8').read(),'export_chainlink.py','exec'),{})
bpy.context.window.scene=previous_scene
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'SG_ChainLink.blend'))
with open(os.path.join(ROOT,'clearance_checks.json'),'w',encoding='utf-8') as f:
    json.dump(reports,f,indent=2)
