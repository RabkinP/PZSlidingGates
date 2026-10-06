"""Independent readers validate deployed binary metadata and transparent PNG payload."""
from io import BytesIO
from pathlib import Path
import re
import struct
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT/'mod/SlidingGates/42/media'


def integer(stream):
    return struct.unpack('<i', stream.read(4))[0]


def string(stream):
    return stream.read(integer(stream)).decode('ascii')


pack = BytesIO((MEDIA/'texturepacks/SG_GatesPreview.pack').read_bytes())
assert pack.read(4) == b'PZPK' and integer(pack) == 1 and integer(pack) == 1
assert string(pack) == 'SG_GatesPreview_0'
assert integer(pack) == 16 and integer(pack) == 1
for index in range(16):
    assert string(pack) == f'sg_gates_preview_01_{index}'
    assert [integer(pack) for _ in range(8)] == [index%8*128,index//8*256,128,256,0,0,128,256]
image = Image.open(BytesIO(pack.read(integer(pack))))
assert image.size == (1024,512) and image.mode == 'RGBA'
assert image.getchannel('A').getextrema() == (0,0)
assert not pack.read()

tiles = BytesIO((MEDIA/'SG_GatesPreview.tiles').read_bytes())
assert tiles.read(4) == b'tdef' and integer(tiles) == 1 and integer(tiles) == 1
assert tiles.readline() == b'sg_gates_preview_01\n'
assert tiles.readline() == b'sg_gates_preview_01.png\n'
assert [integer(tiles) for _ in range(4)] == [8,2,1,16]
assert all(integer(tiles)==0 for _ in range(16))  # no inadvertent collision flags
assert not tiles.read()

bindings=(ROOT/'mod/SlidingGates/common/media/spriteModels.txt').read_text()
assert len(re.findall(r'\bxy\s*=',bindings)) == 16
assert 'xy = 1 0,' in bindings and 'xy = 5 0,' in bindings
assert 'Base.SG_ChainLink_N_Right,' in bindings and 'Base.SG_ChainLink_4_N_Right,' in bindings
model_scripts = (MEDIA/'scripts/SG_models.txt').read_text()


def properties(block):
    return dict(re.findall(r'(\w+)\s*=\s*([^,]+),', block))


tiles_by_index = {}
for block in re.findall(r'\btile\s*\{([^}]+)\}', bindings):
    props = properties(block)
    x, y = map(int, props.pop('xy').split())
    tiles_by_index[x+y*8] = props
for index, name in ((1,'SG_ChainLink_N_Right_G_Closed'),
                    (5,'SG_ChainLink_4_N_Right_G_Closed'),
                    (8,'SG_CatcherPost_Static'), (9,'SG_GuidePost_Static'),
                    (10,'SG_Rail_Static'), (11,'SG_Drive_Static')):
    block = re.search(r'\bspriteModel\s+'+name+r'\s*\{([^}]+)\}',model_scripts).group(1)
    expected = properties(block)
    actual = tiles_by_index[index]
    assert actual['modelScript'].strip() == expected['modelScript'].strip()
    for key in ('translate','rotate','scale','animationTime'):
        if key in expected:
            assert list(map(float,actual[key].split())) == list(map(float,expected[key].split())), (index,key)
    if 'animation' in expected:
        assert actual['animation'].strip() == expected['animation'].strip()
info=(MEDIA.parent/'mod.info').read_text()
assert 'pack=SG_GatesPreview' in info and 'tiledef=SG_GatesPreview 6842' in info
entities=(MEDIA/'scripts/entity_sliding_gates.txt').read_text()
assert 'street_trafficlines' not in entities
for index in range(6):
    assert f'sg_gates_preview_01_{index}' in entities
print('PASS pack v1, tdef v1, alpha, properties, entity carriers, registration and calibrated model poses')
