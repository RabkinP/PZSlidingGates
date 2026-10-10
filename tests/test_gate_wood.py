"""Wood skill boundaries, four orientations, persistence, damage, drive and resource budgets."""
import ast
import re
import json
import struct
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];MEDIA=ROOT/'mod/SlidingGates/42/media'
tree=ast.parse((ROOT/'tests/test_gate_drive.py').read_text())
prefix=tree.body[:next(i for i,n in enumerate(tree.body) if isinstance(n,ast.For))]
ns={'__file__':str(ROOT/'tests/test_gate_drive.py')}
exec(compile(ast.Module(body=prefix,type_ignores=[]),'<wood-fixture>','exec'),ns)
ns['MOCK']=ns['MOCK'].replace('function o:setHealth(v) self.health=v end',
    'function o:setHealth(v) self.health=v end\n function o:getHealth() return self.health end\n function o:getMaxHealth() return self.maxHealth end\n function o:invalidateRenderChunkLevel(flags) self.redraw=flags end')
for width in (2,4):
    for orientation in ('N','W'):
        for direction in ('forward','reverse'):
            for level,quality in ((4,'low'),(5,'medium'),(6,'medium'),(7,'high'),(10,'high')):
                lua=ns['runtime']()
                for key,value in dict(width=width,orientation=orientation,direction=direction,level=level,quality=quality).items():lua.globals()[key]=value
                lua.execute(r'''
require 'SG_Gate'
print=function() end
local kind=width==2 and 'wood' or 'wood4'
Perks={Woodwork='carpentry',MetalWelding='welding'}
local player={getPerkLevel=function(_,perk) return perk=='carpentry' and level or 10 end}
assert(SGGate.buildLevel(player,kind)==level)
assert(SGGate.qualityForLevel(level,kind)==quality)
local id=SGGate.build(square(30,20,0),kind,level,orientation,direction,quality)
local leaf=SGGate.findRole(id,'leaf')
assert(leaf.md.sgBase:find('SG_Wood',1,true)==1)
assert(leaf.md.sgBase==SGGate.leafModel(kind,orientation,direction,quality))
assert(leaf.maxHealth==level*300)
for _,part in ipairs(SGGate.parts(id)) do
 if part.md.sgRole=='post' or part.md.sgRole=='rail' then assert(part.md.sgStatic:find('SG_Wood_',1,true)==1) end
end
local drive=SGGate.installDrive(id);assert(drive and drive.md.sgStatic:find('SG_Wood_Drive',1,true)==1)
local base=leaf.md.sgBase;local slave=SGGate.findRole(id,'slave')
slave:setHealth(slave.maxHealth*.7);assert(SGGate.updateDamage(id)==1)
assert(leaf.model=='Base.'..base..'_Damage1_Closed')
assert(SGGate.toggle(id));local previous=leaf.model
slave:setHealth(slave.maxHealth*.2);assert(SGGate.updateDamage(id)==3 and leaf.model==previous)
leaf.animating=false;for i=1,400 do if tick then tick() end end
SGGate.updateDamage(id);assert(leaf.model=='Base.'..base..'_Damage3_Open')
assert(SGGate.snapshot(id).type==kind and SGGate.snapshot(id).quality==quality)
player.getPerkLevel=function() return 10 end
gridLoaded(leaf:getSquare());assert(SGGate.quality(id)==quality) -- no automatic improvement
state=SGGate.snapshot(id);leaf.md.sgBase='incorrect';leaf.md.sgQuality=nil
clientMode=true;now=0;function getTimestampMs() return now end
Events.OnServerCommand={Add=function(fn) receiveWood=fn end}
Events.LoadGridsquare={Add=function(fn) clientLoad=fn end}
function sendClientCommand() end
require 'SG_GateNetwork'
receiveWood('SlidingGates','snapshot',state)
assert(leaf.md.sgBase==base and leaf.md.sgQuality==quality and leaf.model=='Base.'..base..'_Damage3_Open')
''')
print('PASS 40 wood assemblies: carpentry, health, static parts/drive, animation, damage deferral, persistence and late MP')

# Native recipes consume exactly the configured salvage budget and share no footprints.
lua=ns['runtime']();lua.execute("require 'SG_GateCommon'")
recipe=(MEDIA/'scripts/entity_sliding_gates_wood.txt').read_text();seen=set()
for width,kind in ((2,'wood'),(4,'wood4')):
    for suffix,level in (('Low',4),('Medium',5),('',7)):
        name=f'SlidingGateWood{width}{suffix}'
        start=re.search(r'    entity '+name+r'\s*\{',recipe).end();end=start;depth=1
        while depth:depth+=(recipe[end]=='{')-(recipe[end]=='}');end+=1
        block=recipe[start:end]
        assert f'SkillRequired = Woodwork:{level},' in block
        assert 'category = Carpentry,' in block and 'BuildWallHammer' in block
        assert f'OnAddToMenu = SGGateWood{suffix or "High"}RecipeTest,' in block
        for item,amount in lua.globals().SGGateTypes[kind].materials.items():
            assert f'item {amount} [{item}],' in block,(name,item,amount)
        indices=set(map(int,re.findall(r'sg_gates_preview_01_(\d+)',block)))
        assert len(indices)==4*width and not indices&seen;seen|=indices
assert seen==set(range(96,168))
assert (MEDIA/'textures/SG_BuildWood2.png').exists() and (MEDIA/'textures/SG_BuildWood4.png').exists()
print('PASS six native carpentry recipes: materials, quality thresholds and unique preview footprints')

# Exercise the authority's construction hooks before resource consumption.
tree=ast.parse((ROOT/'tests/test_gate_preview.py').read_text())
stop=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)
    and n.value.args and isinstance(n.value.args[0],ast.Constant) and isinstance(n.value.args[0].value,str)
    and 'install()\nfor _,width' in n.value.args[0].value)
preview={'__file__':str(ROOT/'tests/test_gate_preview.py')}
exec(compile(ast.Module(body=tree.body[:stop],type_ignores=[]),'<wood-preview-fixture>','exec'),preview)
preview['lua'].execute(r'''
print=function() end
install()
Perks={Woodwork='carpentry',MetalWelding='welding'}
SGGate.width=function(kind) return (kind=='wood4' or kind=='chainlink4') and 4 or 2 end
for _,width in ipairs({2,4}) do
 for _,tier in ipairs({{'Low',4,'low'},{'Medium',5,'medium'},{'',7,'high'}}) do
  local level=tier[2]
  local player={getPerkLevel=function(_,perk) return perk=='carpentry' and level or 10 end}
  local name='SlidingGateWood'..width..tier[1]
  local info={getScript=function() return {getName=function() return name end} end}
  local b=ISBuildIsoEntity:new(player,info,2);b.character=player
  local sq=square(100,200,0)
  assert(b:isValid(sq))
  level=3;assert(not b:isValid(sq))
  level=tier[2];b:create(100,200,0,true)
  assert(built[4]==(width==2 and 'wood' or 'wood4') and built[5]==level and built[8]==tier[3])
  level=10;if tier[3]~='high' then assert(not b:isValid(sq)) end
 end
end
''')
print('PASS authority construction: min carpentry 4, exact recipe quality and skill-level vanilla health')

# Deployed single meshes, exact animation intervals, rigid weights and normals.
tree=ast.parse((ROOT/'tests/test_model_variants.py').read_text())
accessor_node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='accessor')
accessor_ns={'struct':struct};exec(compile(ast.Module(body=[accessor_node],type_ignores=[]),'<accessors>','exec'),accessor_ns)
accessor=accessor_ns['accessor']
paths=list((ROOT/'art/exports/wood').glob('*.glb'));assert len(paths)==56
for path in paths:
    raw=path.read_bytes();length=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+length]);buf=raw[28+length:]
    assert raw==(MEDIA/'models_X/IsoObject'/path.name).read_bytes()
    assert len(doc['meshes'])==1 and len(doc['meshes'][0]['primitives'])==1
    attrs=doc['meshes'][0]['primitives'][0]['attributes']
    normals=accessor(doc,buf,attrs['NORMAL'])
    assert all(abs(sum(v*v for v in n)-1)<1e-4 for n in normals)
    if '_N_' not in path.name:continue
    width=4 if '_4_' in path.name else 2
    assert [a['name'] for a in doc['animations']]==['Open','Close']
    assert all(abs(sum(w)-1)<1e-6 for w in accessor(doc,buf,attrs['WEIGHTS_0']))
    for clip in doc['animations']:
        channel=next(c for c in clip['channels'] if c['target']['path']=='translation')
        sampler=clip['samplers'][channel['sampler']]
        times=accessor(doc,buf,sampler['input']);poses=accessor(doc,buf,sampler['output'])
        assert abs(times[0][0])<1e-5 and abs(times[-1][0]-width*1.5)<1e-5
        assert abs(sum((a-b)**2 for a,b in zip(poses[0],poses[-1]))-width**2)<1e-4
motion=json.loads((ROOT/'art/wood_motion_checks.json').read_text())
assert len(motion)==48 and sum(r['frames'] for r in motion)==10464
assert all(not r['collisions'] and r['rail_capture'] for r in motion)
print('PASS 56 deployed GLBs: single meshes, normals, rigid weights, clips/stroke/duration and 10,464 checked frames')
