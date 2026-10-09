"""Conservative sampled empty-circle bound in the XZ projection of stage-3 infill.

Nearest projected vertex distance overestimates distance to the actual wires.
Add half the grid-cell diagonal to cover unsampled locations. This is a
geometric diagnostic, not a humanoid collision simulation or gameplay proof.
"""
import bpy
import json
import math
import os
from mathutils import Vector
from mathutils.kdtree import KDTree

ART=r'E:\git\SlidingGates\art'
reports=json.load(open(os.path.join(ART,'damage_checks.json')))
for report in reports:
    if report['stage']!=3:continue
    scene=bpy.data.scenes[report['scene']]
    rig=next(o for o in scene.objects if o.type=='ARMATURE' and o.get('gate_width_cells'))
    leaf=next(o for o in scene.objects if o.type=='MESH' and o.parent==rig)
    sign=-1 if report['reverse'] else 1
    tree=KDTree(len(leaf.data.vertices))
    for v in leaf.data.vertices:tree.insert(Vector((sign*v.co.x,0,v.co.z)),v.index)
    tree.balance();step=.025;maximum=0
    nx=math.ceil((report['width']-.24)/step);nz=math.ceil(1.4/step)
    for ix in range(nx+1):
        for iz in range(nz+1):
            x=.12+(report['width']-.24)*ix/nx;z=.36+1.4*iz/nz
            maximum=max(maximum,tree.find(Vector((x,0,z)))[2])
    bound=2*(maximum+step/math.sqrt(2))
    assert bound<.35,(scene.name,bound)
    report['projected_empty_circle_diameter_upper_bound']=bound
    report['aperture_sampling_step']=step
    print('APERTURE',scene.name,round(bound,4))
json.dump(reports,open(os.path.join(ART,'damage_checks.json'),'w'),indent=2)
