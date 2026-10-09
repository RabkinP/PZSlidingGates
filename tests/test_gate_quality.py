"""Persisted quality, model selection, recipe tiers, assets and MP snapshots."""
import ast
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
tree=ast.parse((ROOT/'tests/test_gate_drive.py').read_text())
prefix=tree.body[:next(i for i,n in enumerate(tree.body) if isinstance(n,ast.For))]
ns={'__file__':str(ROOT/'tests/test_gate_drive.py')}
exec(compile(ast.Module(body=prefix,type_ignores=[]),'<quality-fixture>','exec'),ns)
for width in (2,4):
    for orientation in ('N','W'):
        for direction in ('forward','reverse'):
            for quality in ('low','medium','high'):
                lua=ns['runtime']()
                lua.globals().width=width;lua.globals().orientation=orientation
                lua.globals().direction=direction;lua.globals().quality=quality
                lua.execute(r'''
require 'SG_Gate'
local kind=width==2 and 'chainlink' or 'chainlink4'
local id=SGGate.build(square(30,20,0),kind,200,orientation,direction,quality)
assert(id and SGGate.quality(id)==quality and SGGate.snapshot(id).quality==quality)
local leaf=SGGate.findRole(id,'leaf')
local prefix=width==2 and 'SG_ChainLink' or 'SG_ChainLink_4'
local suffix=orientation=='W' and '_W' or '_N'
suffix=suffix..(direction=='reverse' and '_Reverse' or (orientation=='N' and '_Right' or ''))..'_G'
local expected=prefix..(quality=='high' and '' or (quality=='low' and '_Low' or '_Medium'))..suffix
assert(leaf.md.sgBase==expected and leaf.model=='Base.'..expected..'_Closed')
for _,part in ipairs(SGGate.parts(id)) do assert(part.md.sgQuality==quality) end
assert(SGGate.toggle(id));for i=1,300 do if tick then tick() end end
assert(leaf.model=='Base.'..expected..'_Open')
SGGate.registry()[id].quality=nil -- restore from saved object metadata
assert(SGGate.ensureIdentity(id).quality==quality)
gridLoaded(leaf:getSquare());assert(leaf.md.sgQuality==quality)
SGGate.registry()[id].quality=nil
for _,part in ipairs(SGGate.parts(id)) do part.md.sgQuality=nil end
assert(SGGate.ensureIdentity(id).quality=='high') -- legacy metadata
''')
print('PASS 24 assemblies: quality models, Open/Close, persistence, metadata, snapshots and legacy default')

# Native recipes each own their footprint: never share carriers between entities.
media=ROOT/'mod/SlidingGates/42/media'
source='\n'.join(p.read_text() for p in (media/'scripts').glob('entity_sliding_gates*.txt'))
seen=set()
for width in (2,4):
    for suffix,quality,level in (('Low','Low',4),('Medium','Medium',6),('','High',8)):
        name=f'SlidingGateChainLink{width}{suffix}'
        match=re.search(r'    entity '+name+r'\s*\{',source);assert match,name
        start=match.end();end=start;depth=1
        while depth:
            depth+=(source[end]=='{')-(source[end]=='}');end+=1
        block=source[start:end]
        assert f'SkillRequired = MetalWelding:{level},' in block
        assert f'OnAddToMenu = SGGate{quality}RecipeTest,' in block
        carriers=set(map(int,re.findall(r'sg_gates_preview_01_(\d+)',block)))
        assert len(carriers)==4*width and not seen.intersection(carriers)
        seen.update(carriers)
        title=json.loads((media/'lua/shared/Translate/RU/Recipes.json').read_text(encoding='utf-8'))[name]
        assert title.endswith('('+{'Low':'Низкое качество','Medium':'Среднее качество','High':'Высокое качество'}[quality]+')')
manifest=json.loads((ROOT/'art/tiles/gate_tiles.json').read_text())['indices']
definitions=(media/'scripts/SG_models_quality.txt').read_text()
for quality,start in (('Low',48),('Medium',72)):
    for width,offset in ((2,0),(4,8)):
        prefix='SG_ChainLink' if width==2 else 'SG_ChainLink_4'
        for face,leaf_index in ((0,width-1),(1,0),(2,0),(3,width-1)):
            props=manifest[str(start+offset+face*width+leaf_index)]
            orientation='W' if face in (1,3) else 'N';reverse=face>=2
            model=f'{prefix}_{quality}_N_'+('Reverse' if reverse else 'Right')
            base=f'{prefix}_{quality}_{orientation}'+('_Reverse' if reverse else ('_Right' if orientation=='N' else ''))+'_G_Closed'
            block=re.search(r'\bspriteModel '+base+r'\s*\{([^}]+)\}',definitions)[1]
            expected=dict(re.findall(r'(\w+)\s*=\s*([^,]+),',block))
            assert props['modelScript']=='Base.'+model
            for key in ('translate','rotate','scale','animationTime'):
                assert list(map(float,props[key].split()))==list(map(float,expected[key].split()))
print('PASS six native recipe tiers/titles, unique entity footprints and all 16 quality preview anchors')

# Quality survives authority snapshots even before a late client's modData arrives.
lua=ns['runtime']()
lua.execute(r'''
require 'SG_Gate'
id=SGGate.build(square(30,20,0),'chainlink4',200,'W','reverse','low')
local leaf=SGGate.findRole(id,'leaf');state=SGGate.snapshot(id)
leaf.md.sgQuality=nil;leaf.md.sgBase='SG_ChainLink_4_W_Reverse_G'
clientMode=true;now=0
function getTimestampMs() return now end
Events.OnServerCommand={Add=function(fn) receiveQuality=fn end}
Events.LoadGridsquare={Add=function(fn) clientLoad=fn end}
function sendClientCommand() end
require 'SG_GateNetwork'
receiveQuality('SlidingGates','snapshot',state)
assert(leaf.md.sgQuality=='low' and SGGate.registry()[id].quality=='low')
assert(leaf.model=='Base.SG_ChainLink_4_Low_W_Reverse_G_Closed')
clientLoad(leaf:getSquare())
assert(SGGate.registry()[id].quality=='low')
''')
print('PASS late-client quality snapshot, model reconstruction and chunk metadata')
