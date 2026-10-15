"""Check exported leaf clips, rigid skinning, travel and deployed bytes."""
import json, math, struct
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def accessor(doc,buf,index):
    a=doc['accessors'][index]; v=doc['bufferViews'][a['bufferView']]
    n={'SCALAR':1,'VEC3':3,'VEC4':4}[a['type']]
    fmt='<'+{5126:'f',5125:'I',5123:'H',5121:'B'}[a['componentType']]*n
    step=v.get('byteStride',struct.calcsize(fmt))
    offset=v.get('byteOffset',0)+a.get('byteOffset',0)
    return [struct.unpack_from(fmt,buf,offset+j*step) for j in range(a['count'])]

for path in sorted((ROOT/'art/exports').rglob('SG_ChainLink*.glb')):
    if 'six' in path.relative_to(ROOT/'art/exports').parts:
        continue  # Source-only exports are covered by test_six_cell_exports.py; not deployed yet.
    raw=path.read_bytes(); length=struct.unpack_from('<I',raw,12)[0]
    doc=json.loads(raw[20:20+length]); buf=raw[28+length:]
    width=4 if '_4_' in path.name else 2
    assert len(doc['meshes'])==1 and len(doc['meshes'][0]['primitives'])==1,path
    attrs=doc['meshes'][0]['primitives'][0]['attributes']
    assert all(abs(sum(w)-1)<1e-5 for w in accessor(doc,buf,attrs['WEIGHTS_0'])),path
    assert {a['name'] for a in doc['animations']}=={'Open','Close'},path
    for clip in doc['animations']:
        ch=next(c for c in clip['channels'] if c['target']['path']=='translation')
        sample=clip['samplers'][ch['sampler']]
        times=accessor(doc,buf,sample['input']); poses=accessor(doc,buf,sample['output'])
        assert abs(math.dist(poses[0],poses[-1])-width)<1e-5,(path,clip['name'])
        duration=width*1.5
        assert abs(times[-1][0]-times[0][0]-duration)<1e-5,path
        assert abs(times[0][0])<1e-5 and abs(times[-1][0]-duration)<1e-5,path
    installed=ROOT/'mod/SlidingGates/42/media/models_X/IsoObject'/path.name
    assert raw==installed.read_bytes(),path
    print(path.name,'PASS clips, stroke, duration, weights, deployment')


def glb(path):
    raw=path.read_bytes();length=struct.unpack_from('<I',raw,12)[0]
    return json.loads(raw[20:20+length]),raw[28+length:]


for name in ('SG_ChainLink','SG_ChainLink_4','SG_CatcherPost','SG_GuidePost','SG_Rail','SG_Drive'):
    is_leaf='ChainLink' in name
    old=ROOT/'art/exports'/(name+('_N_Right' if is_leaf else '')+'.glb')
    new=ROOT/'art/exports'/(name+('_N_Reverse' if is_leaf else '_Reverse')+'.glb')
    source,sbuf=glb(old);target,tbuf=glb(new)
    primitive=target['meshes'][0]['primitives'][0]
    old_attrs=source['meshes'][0]['primitives'][0]['attributes']
    vertices=accessor(target,tbuf,primitive['attributes']['POSITION'])
    normals=accessor(target,tbuf,primitive['attributes']['NORMAL'])
    original=accessor(source,sbuf,old_attrs['POSITION'])
    old_normals=accessor(source,sbuf,old_attrs['NORMAL'])
    from collections import defaultdict
    # Positions must reflect exactly; normals are re-quantized on export, so
    # match them per position within a small tolerance.
    expected=defaultdict(list);actual=defaultdict(list)
    for pos,normal in zip(original,old_normals):
        expected[tuple(round(v,5) for v in (-pos[0],pos[1],pos[2]))].append((-normal[0],normal[1],normal[2]))
    for pos,normal in zip(vertices,normals):
        actual[tuple(round(v,5) for v in pos)].append(tuple(normal))
    assert expected.keys()==actual.keys(),(new,'reflected positions')
    for key,wanted in expected.items():
        remaining=list(actual[key])
        assert len(wanted)==len(remaining),(new,'reflected positions',key)
        for n in wanted:
            match=next((i for i,m in enumerate(remaining) if max(abs(n[j]-m[j]) for j in range(3))<1e-3),None)
            assert match is not None,(new,'reflected normals',key,n)
            remaining.pop(match)
    assert all(all(s>0 for s in node.get('scale',[1,1,1])) for node in target['nodes'])
    def winding_errors(doc,buf,positions,normals):
        indices=[entry[0] for entry in accessor(doc,buf,doc['meshes'][0]['primitives'][0]['indices'])]
        errors=[]
        for i in range(0,len(indices),3):
            ids=indices[i:i+3];a,b,c=[positions[j] for j in ids]
            u=[b[j]-a[j] for j in range(3)];v=[c[j]-a[j] for j in range(3)]
            cross=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
            normal=[sum(normals[k][j] for k in ids) for j in range(3)]
            dot=sum(cross[j]*normal[j] for j in range(3))
            if dot < -1e-8: errors.append(round(dot,8))
        return sorted(errors)
    # The source leaf has two existing triangles whose averaged vertex normal
    # opposes the face. Reflection must not introduce or worsen such anomalies.
    assert winding_errors(target,tbuf,vertices,normals)==winding_errors(source,sbuf,original,old_normals),(new,'winding regression')
    if is_leaf:
        clip=next(a for a in target['animations'] if a['name']=='Open')
        ch=next(c for c in clip['channels'] if c['target']['path']=='translation')
        poses=accessor(target,tbuf,clip['samplers'][ch['sampler']]['output'])
        width=4 if name.endswith('_4') else 2
        assert abs(poses[-1][0]-poses[0][0]+width)<1e-5
    assert new.read_bytes()==(ROOT/'mod/SlidingGates/42/media/models_X/IsoObject'/new.name).read_bytes()
    print(new.name,'PASS exact X reflection, source winding/normals preserved, positive scales, reverse stroke and deployment')
