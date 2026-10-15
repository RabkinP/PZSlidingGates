"""Validate source-only six-cell GLBs without requiring game registration."""
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'art'
manifest = json.loads((ART / 'six_export_manifest.json').read_text())
assert len(manifest) == 48


def accessor(doc, buf, index):
    a = doc['accessors'][index]
    view = doc['bufferViews'][a['bufferView']]
    count = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[a['type']]
    fmt = '<' + {5126: 'f', 5125: 'I', 5123: 'H', 5121: 'B'}[a['componentType']] * count
    stride = view.get('byteStride', struct.calcsize(fmt))
    offset = view.get('byteOffset', 0) + a.get('byteOffset', 0)
    return [struct.unpack_from(fmt, buf, offset + i * stride) for i in range(a['count'])]


expected = set()
for material in ('Wood', 'ChainLink'):
    for quality in ('', '_Medium', '_Low'):
        for direction in ('Right', 'Reverse'):
            for damage in ('', '_Damage1', '_Damage2', '_Damage3'):
                expected.add(f'SG_{material}_6{quality}_N_{direction}{damage}.glb')
assert {Path(r['path']).name for r in manifest} == expected
assert {p.name for p in (ART / 'exports/six').rglob('*.glb')} == expected
reports = []
for row in manifest:
    path = ART / row['path']
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == row['sha256']
    assert raw[:4] == b'glTF' and struct.unpack_from('<II', raw, 4) == (2, len(raw))
    length = struct.unpack_from('<I', raw, 12)[0]
    doc, buf = json.loads(raw[20:20 + length]), raw[28 + length:]
    assert len(doc['meshes']) == len(doc['skins']) == 1
    assert len(doc['meshes'][0]['primitives']) == 1
    attrs = doc['meshes'][0]['primitives'][0]['attributes']
    assert all(k in attrs for k in ('POSITION', 'NORMAL', 'TEXCOORD_0', 'JOINTS_0', 'WEIGHTS_0'))
    positions = accessor(doc, buf, attrs['POSITION'])
    normals = accessor(doc, buf, attrs['NORMAL'])
    uv = accessor(doc, buf, attrs['TEXCOORD_0'])
    assert all(math.isfinite(v) for p in positions for v in p)
    assert all(abs(sum(v*v for v in normal) - 1) < 1e-4 for normal in normals)
    assert all(math.isfinite(v) and -1e-6 <= v <= 1+1e-6 for p in uv for v in p)
    assert all(abs(max(w) - 1) < 1e-6 and abs(sum(w) - 1) < 1e-6
               for w in accessor(doc, buf, attrs['WEIGHTS_0']))
    skin = doc['skins'][0]
    assert any(doc['nodes'][j].get('name') == 'DoorBone' for j in skin['joints'])
    assert len(doc['nodes']) == 3  # Only rigid leaf, its rig and DoorBone.
    assert [a['name'] for a in doc['animations']] == ['Open', 'Close']
    sign = -1 if '_Reverse' in path.name else 1
    xs = [sign * p[0] for p in positions]
    assert min(xs) >= -1e-5 and max(xs) <= 6 + 1e-5
    for clip in doc['animations']:
        channel = next(c for c in clip['channels'] if c['target']['path'] == 'translation')
        assert doc['nodes'][channel['target']['node']]['name'] == 'DoorBone'
        sampler = clip['samplers'][channel['sampler']]
        times = accessor(doc, buf, sampler['input'])
        poses = accessor(doc, buf, sampler['output'])
        assert abs(times[0][0]) < 1e-5 and abs(times[-1][0] - 9) < 1e-5
        assert abs(math.dist(poses[0], poses[-1]) - 6) < 1e-5
        ends = (0, 6) if clip['name'] == 'Open' else (6, 0)
        assert all(abs(sign * pose[0] - end) < 1e-5 for pose, end in zip((poses[0], poses[-1]), ends))
    reports.append(dict(path=row['path'], vertices=len(positions), clips=['Open', 'Close'],
                        seconds=9, stroke=6, normals=True, uv=True, rigid_weights=True))
(ART / 'six_glb_checks.json').write_text(json.dumps(reports, indent=2), encoding='utf-8')
print('PASS 48 six-cell GLBs: exact variant set, single meshes, normals/UV/weights, 9s clips and 6-unit stroke')
