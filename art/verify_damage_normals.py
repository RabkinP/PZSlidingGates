"""Read-only signed-volume validation of each closed connected damage shell."""
import bpy
import json
from mathutils import Vector

ART=r'E:\git\SlidingGates\art'
code=open(ART+r'\build_damage_variants.py',encoding='utf-8').read()
exec(code[code.index('def components'):code.index('def orient_shells')])
path=ART+r'\damage_checks.json';reports=json.load(open(path))
for report in reports:
    s=bpy.data.scenes[report['scene']]
    r=next(o for o in s.objects if o.type=='ARMATURE' and o.get('gate_width_cells'))
    m=next(o.data for o in s.objects if o.type=='MESH' and o.parent==r)
    m.calc_loop_triangles();labels={};centers=[]
    for ids in components(m):
        ci=len(centers);centers.append(sum((m.vertices[i].co for i in ids),Vector())/len(ids))
        for i in ids:labels[i]=ci
    volumes=[0.0]*len(centers)
    for t in m.loop_triangles:
        ci=labels[t.vertices[0]];c=centers[ci]
        a,b,d=[m.vertices[i].co-c for i in t.vertices]
        volumes[ci]+=a.dot(b.cross(d))/6
    assert min(volumes)>0,(s.name,min(volumes))
    report['closed_components_outward_signed_volume']=True
json.dump(reports,open(path,'w'),indent=2)
print('PASS outward signed volumes of all connected shells on all 36 damage meshes')
