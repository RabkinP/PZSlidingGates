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
assert pack.read(4) == b'PZPK' and integer(pack) == 1 and integer(pack) == 2
# Page 0: inner tileset _01 (unchanged layout); page 1: outer tileset _02 with the same indices.
for page, tileset in enumerate(('sg_gates_preview_01', 'sg_gates_preview_02')):
    assert string(pack) == f'SG_GatesPreview_{page}'
    assert integer(pack) == 328 and integer(pack) == 1
    for index in range(328):
        assert string(pack) == f'{tileset}_{index}'
        assert [integer(pack) for _ in range(8)] == [index%8*128,index//8*256,128,256,0,0,128,256]
    image = Image.open(BytesIO(pack.read(integer(pack))))
    assert image.size == (1024,10496) and image.mode == 'RGBA'
    assert image.getchannel('A').getextrema() == (0,0)
assert not pack.read()

tiles = BytesIO((MEDIA/'SG_GatesPreview.tiles').read_bytes())
# Installed loader rejects a whole tileset above 512 tiles: outer carriers are tileset 2.
assert tiles.read(4) == b'tdef' and integer(tiles) == 1 and integer(tiles) == 2
for tileset in ('sg_gates_preview_01', 'sg_gates_preview_02'):
    assert tiles.readline() == tileset.encode()+b'\n'
    assert tiles.readline() == tileset.encode()+b'.png\n'
    assert [integer(tiles) for _ in range(4)] == [8,41,1,328]
    assert all(integer(tiles)==0 for _ in range(328))  # no inadvertent collision flags
assert not tiles.read()

all_bindings=(ROOT/'mod/SlidingGates/common/media/spriteModels.txt').read_text()
assert len(re.findall(r'\bxy\s*=',all_bindings)) == 656
bindings, outer_bindings = all_bindings.split('name = sg_gates_preview_02,')
assert 'name = sg_gates_preview_01,' in bindings
assert 'xy = 1 0,' in bindings and 'xy = 5 0,' in bindings
assert 'Base.SG_ChainLink_N_Right,' in bindings and 'Base.SG_ChainLink_4_N_Right,' in bindings
model_scripts = (MEDIA/'scripts/SG_models.txt').read_text()
model_scripts += (MEDIA/'scripts/SG_models_reverse.txt').read_text()


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
                    (10,'SG_Rail_Static'), (11,'SG_Drive_Static'),
                    (6,'SG_ChainLink_W_G_Closed'), (12,'SG_ChainLink_4_W_G_Closed'),
                    (16,'SG_CatcherPost_W_Static'), (17,'SG_GuidePost_W_Static'),
                    (18,'SG_Rail_W_Static'), (19,'SG_Drive_W_Static'),
                    (24,'SG_ChainLink_N_Reverse_G_Closed'), (26,'SG_ChainLink_4_N_Reverse_G_Closed'),
                    (31,'SG_ChainLink_W_Reverse_G_Closed'), (35,'SG_ChainLink_4_W_Reverse_G_Closed'),
                    (36,'SG_CatcherPost_Reverse_Static'),(37,'SG_GuidePost_Reverse_Static'),
                    (38,'SG_Rail_Reverse_Static'),(39,'SG_Drive_Reverse_Static'),
                    (40,'SG_CatcherPost_Reverse_W_Static'),(41,'SG_GuidePost_Reverse_W_Static'),
                    (42,'SG_Rail_Reverse_W_Static'),(43,'SG_Drive_Reverse_W_Static')):
    block = re.search(r'\bspriteModel\s+'+name+r'\s*\{([^}]+)\}',model_scripts).group(1)
    expected = properties(block)
    actual = tiles_by_index[index]
    assert actual['modelScript'].strip() == expected['modelScript'].strip()
    for key in ('translate','rotate','scale','animationTime'):
        if key in expected:
            assert list(map(float,actual[key].split())) == list(map(float,expected[key].split())), (index,key)
    if 'animation' in expected:
        assert actual['animation'].strip() == expected['animation'].strip()
# Independent anchor check: W is the same assembly rotated around the catcher.
# Native rotate.y=90 gives world (x,y)->(y,-x); cell convention adds +1 to Y.
for width in (2,4):
    for n_index,w_index,k,n_leaf in ((1 if width==2 else 5,6 if width==2 else 12,1,True),
                                    (8,16,0,False),(9,17,width,False),
                                    (10,18,width,False),(11,19,width,False)):
        n_pose=tiles_by_index[n_index]; w_pose=tiles_by_index[w_index]
        ntx,_,nty=map(float,n_pose['translate'].split())
        wtx,_,wty=map(float,w_pose['translate'].split())
        nx,ny=-k+.5+ntx,.5+nty
        wx,wy=.5+wtx,k+.5+wty
        assert abs(wx-ny)<1e-6 and abs(wy-(1-nx))<1e-6,(n_index,w_index)
        assert list(map(float,w_pose['rotate'].split()))==[0,90,0]
# True edge-axis reflection: every calibrated N X anchor changes sign; the
# perpendicular anchor remains fixed. W then applies the same quarter turn.
for width in (2,4):
    for f,r,w,k in ((1 if width==2 else 5,24 if width==2 else 26,31 if width==2 else 35,1),
                    (8,36,40,0),(9,37,41,width),(10,38,42,width),(11,39,43,width)):
        fx,fy,fz=map(float,tiles_by_index[f]['translate'].split())
        rx,ry,rz=map(float,tiles_by_index[r]['translate'].split())
        wx,wy,wz=map(float,tiles_by_index[w]['translate'].split())
        assert (rx,ry,rz)==(-fx,fy,fz)
        assert (wx,wy,wz)==(rz,ry,-rx)
        assert list(map(float,tiles_by_index[w]['rotate'].split()))==[0,90,0]
        fnx=-k+.5+fx; rnx=k+.5+rx
        assert abs(rnx-(1-fnx))<1e-6
info=(MEDIA.parent/'mod.info').read_text()
assert 'pack=SG_GatesPreview' in info and 'tiledef=SG_GatesPreview 6842' in info
entities=(MEDIA/'scripts/entity_sliding_gates.txt').read_text()
assert 'street_trafficlines' not in entities
for index in (0,1,2,3,4,5,6,7,12,13,14,15,*range(24,36)):
    assert f'sg_gates_preview_01_{index}' in entities
# Six-cell footprints 184..327: leaf carriers match the registered resting poses.
six=(MEDIA/'scripts/SG_models_six.txt').read_text(encoding='utf-8')
six_entities=(MEDIA/'scripts/entity_sliding_gates_six.txt').read_text(encoding='utf-8')
for (material,quality),start in ((('ChainLink','_Low'),184),(('ChainLink','_Medium'),208),(('ChainLink',''),232),
                                 (('Wood','_Low'),256),(('Wood','_Medium'),280),(('Wood',''),304)):
    for index in range(start,start+24):
        assert f'sg_gates_preview_01_{index},' in six_entities or f'sg_gates_preview_01_{index} ' in six_entities
    stem=f'SG_{material}_6{quality}'
    for offset,pose in ((5,'_N_Right_G'),(6,'_W_G'),(12,'_N_Reverse_G'),(23,'_W_Reverse_G')):
        expected=properties(re.search(r'\bspriteModel\s+'+stem+pose+r'_Closed\s*\{([^}]+)\}',six)[1])
        actual=tiles_by_index[start+offset]
        assert actual['modelScript'].strip()==expected['modelScript'].strip(),(start+offset)
        for key in ('translate','rotate','scale','animationTime'):
            assert list(map(float,actual[key].split()))==list(map(float,expected[key].split())),(start+offset,key)
# Outer tileset: each carrier is the inner one mirrored across the fence line; leaf carriers
# match the registered outer resting poses (tests/test_gate_outer.py checks the geometry).
outer_scripts=(MEDIA/'scripts/SG_models_outer.txt').read_text(encoding='utf-8')
outer_by_index={}
for block in re.findall(r'\btile\s*\{([^}]+)\}', outer_bindings):
    props=properties(block); x,y=map(int,props.pop('xy').split()); outer_by_index[x+y*8]=props
assert sorted(outer_by_index)==list(range(328))
for index,name in ((1,'SG_ChainLink_N_Right_G_Out_Closed'),(6,'SG_ChainLink_W_G_Out_Closed'),
                   (24,'SG_ChainLink_N_Reverse_G_Out_Closed'),(35,'SG_ChainLink_4_W_Reverse_G_Out_Closed'),
                   (11,'SG_Drive_Out_Static'),(43,'SG_Drive_Reverse_W_Out_Static')):
    source=model_scripts+outer_scripts
    expected=properties(re.search(r'\bspriteModel\s+'+name+r'\s*\{([^}]+)\}',source)[1])
    actual=outer_by_index[index]
    assert actual['modelScript'].strip()==expected['modelScript'].strip(),index
    for key in ('translate','rotate','scale'):
        assert list(map(float,actual[key].split()))==list(map(float,expected[key].split())),(index,key)
for index in range(328):
    hidden=tiles_by_index[index]['scale'].strip()=='0.001'
    assert hidden==(outer_by_index[index]['scale'].strip()=='0.001')
print('PASS pack v1, tdef v1, alpha, properties, entity carriers, registration and calibrated model poses')
