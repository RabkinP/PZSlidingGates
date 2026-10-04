"""Check exported leaf clips, rigid skinning, travel and deployed bytes."""
import json, math, struct
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def accessor(doc,buf,index):
    a=doc['accessors'][index]; v=doc['bufferViews'][a['bufferView']]
    n={'SCALAR':1,'VEC3':3,'VEC4':4}[a['type']]
    fmt='<'+{5126:'f',5123:'H',5121:'B'}[a['componentType']]*n
    step=v.get('byteStride',struct.calcsize(fmt))
    offset=v.get('byteOffset',0)+a.get('byteOffset',0)
    return [struct.unpack_from(fmt,buf,offset+j*step) for j in range(a['count'])]

for path in sorted((ROOT/'art/exports').glob('SG_ChainLink*.glb')):
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
        assert abs(times[-1][0]-times[0][0]-2)<1e-5,path
        if width==4: # new exports have an explicit zero-based timeline
            assert abs(times[0][0])<1e-5 and abs(times[-1][0]-2)<1e-5,path
    installed=ROOT/'mod/SlidingGates/42/media/models_X/IsoObject'/path.name
    assert raw==installed.read_bytes(),path
    print(path.name,'PASS clips, stroke, duration, weights, deployment')
