"""Real Lua 5.1: weakest part, persistence, in-motion deferral and late MP client."""
import ast
from pathlib import Path
import json
import re
import struct

ROOT=Path(__file__).resolve().parents[1]
tree=ast.parse((ROOT/'tests/test_gate_drive.py').read_text())
prefix=tree.body[:next(i for i,n in enumerate(tree.body) if isinstance(n,ast.For))]
ns={'__file__':str(ROOT/'tests/test_gate_drive.py')}
exec(compile(ast.Module(body=prefix,type_ignores=[]),'<damage-fixture>','exec'),ns)
ns['MOCK']=ns['MOCK'].replace('function o:setHealth(v) self.health=v end',
    'function o:setHealth(v) self.health=v end\n function o:getHealth() return self.health end\n function o:getMaxHealth() return self.maxHealth end\n function o:invalidateRenderChunkLevel(flags) self.redraw=flags end')
for width in (2,4):
    for orientation in ('N','W'):
        for direction in ('forward','reverse'):
            for quality in ('low','medium','high'):
                lua=ns['runtime']()
                for k,v in locals().copy().items():
                    if k in ('width','orientation','direction','quality'):lua.globals()[k]=v
                lua.execute(r'''
require 'SG_Gate'
id=SGGate.build(square(30,20,0),width==2 and 'chainlink' or 'chainlink4',5,orientation,direction,quality)
local leaf=SGGate.findRole(id,'leaf');local base=leaf.md.sgBase
for _,p in ipairs(SGGate.parts(id)) do
 function p:getHealth() return self.health end
 function p:getMaxHealth() return self.maxHealth end
end
local slave=SGGate.findRole(id,'slave')
local publications=0;SGGate.onStateChanged=function() publications=publications+1 end
assert(SGGate.updateDamage(id)==0)
assert(SGGate.damageForRatio(.7501)==0 and SGGate.damageForRatio(.75)==1)
assert(SGGate.damageForRatio(.5)==2 and SGGate.damageForRatio(.25)==3)
slave:setHealth(slave.maxHealth*.74)
assert(SGGate.updateDamage(id)==1 and publications==1)
assert(leaf.model=='Base.'..base..'_Damage1_Closed')
assert(leaf.redraw==256)
SGGate.updateDamage(id);assert(publications==1)
assert(SGGate.toggle(id));local motionModel=leaf.model
slave:setHealth(slave.maxHealth*.24)
assert(SGGate.updateDamage(id)==3)
assert(leaf.model==motionModel and leaf.md.sgVisualDamage==1)
leaf.animating=false;for i=1,400 do if tick then tick() end end
SGGate.updateDamage(id)
assert(leaf.model=='Base.'..base..'_Damage3_Open')
assert(leaf.md.sgQuality==quality and SGGate.snapshot(id).damage==3)
slave:setHealth(slave.maxHealth) -- unloading/recreated carriers cannot heal the appearance
assert(SGGate.updateDamage(id)==3)
gridLoaded(leaf:getSquare());assert(leaf.md.sgDamage==3)
state=SGGate.snapshot(id);leaf.md.sgDamage=nil;leaf.md.sgVisualDamage=0
clientMode=true;now=0;function getTimestampMs() return now end
Events.OnServerCommand={Add=function(fn) receiveDamage=fn end}
Events.LoadGridsquare={Add=function(fn) clientLoad=fn end}
function sendClientCommand() end
require 'SG_GateNetwork'
receiveDamage('SlidingGates','snapshot',state)
assert(leaf.md.sgDamage==3 and SGGate.registry()[id].damage==3)
assert(leaf.model=='Base.'..base..'_Damage3_Open')
clientLoad(leaf:getSquare());assert(SGGate.registry()[id].damage==3)
local stale=copyTable(state);stale.revision=state.revision-1;stale.damage=0
receiveDamage('SlidingGates','state',stale);assert(leaf.md.sgDamage==3)
''')
print('PASS 24 assemblies: thresholds, weakest slave, one publish per stage, motion deferral, saved damage, late/stale MP snapshots')

lua=ns['runtime']()
lua.execute(r'''
now=0;function getTimestampMs() return now end
Events.OnTick={Add=function(fn) damagePoll=fn end}
require 'SG_GateDamage'
local calls=0;SGGate.registry()['test']={}
SGGate.updateDamage=function() calls=calls+1 end
damagePoll();now=499;damagePoll();assert(calls==1)
now=500;damagePoll();assert(calls==2)
''')
print('PASS authority polling every 500ms')

media=ROOT/'mod/SlidingGates/42/media'
defs=(media/'scripts/SG_models_damage.txt').read_text()
assert len(re.findall(r'\bmodel ',defs))==36
assert len(re.findall(r'\bspriteModel ',defs))==144
for p in (ROOT/'art/exports/damage').glob('*.glb'):
    raw=p.read_bytes();doc=json.loads(raw[20:20+struct.unpack_from('<I',raw,12)[0]])
    assert [a['name'] for a in doc['animations']]==['Open','Close']
    assert len(doc['meshes'])==1 and len(doc['skins'])==1
    assert len(doc['meshes'][0]['primitives'])==1
    assert raw==(media/'models_X/IsoObject'/p.name).read_bytes()
assert len(list((ROOT/'art/exports/damage').glob('*.glb')))==36
print('PASS 36 deployed GLBs, 144 poses and exact clips')

def positions(path):
    raw=path.read_bytes();length=struct.unpack_from('<I',raw,12)[0]
    doc=json.loads(raw[20:20+length]);buf=raw[28+length:]
    index=doc['meshes'][0]['primitives'][0]['attributes']['POSITION']
    a=doc['accessors'][index];v=doc['bufferViews'][a['bufferView']]
    offset=v.get('byteOffset',0)+a.get('byteOffset',0);step=v.get('byteStride',12)
    return [struct.unpack_from('<fff',buf,offset+i*step) for i in range(a['count'])]

for forward in (ROOT/'art/exports/damage').glob('*_Right_Damage*.glb'):
    reverse=forward.with_name(forward.name.replace('_Right_Damage','_Reverse_Damage'))
    expected={tuple(round(v,5) for v in (-x,y,z)) for x,y,z in positions(forward)}
    actual={tuple(round(v,5) for v in p) for p in positions(reverse)}
    assert expected==actual,forward
print('PASS exact reflected geometry of all 18 forward/reverse damage pairs')

reports=json.loads((ROOT/'art/damage_checks.json').read_text())
assert len(reports)==36 and sum(r['frames_checked'] for r in reports)==7848
assert all(r['surface_collisions']==0 and r['rail_capture'] for r in reports)
assert all(r['closed_components_outward_signed_volume'] for r in reports)
assert all(r['max_removed_span']<.065 for r in reports)
assert all(r['projected_empty_circle_diameter_upper_bound']<.35 for r in reports if r['stage']==3)
print('PASS full-frame clearance evidence and conservative stage-3 aperture bounds')
