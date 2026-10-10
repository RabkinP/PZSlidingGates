"""Real Lua 5.1: versioned save migration of legacy gate health to the vanilla formula."""
import ast
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
tree=ast.parse((ROOT/'tests/test_gate_drive.py').read_text())
prefix=tree.body[:next(i for i,n in enumerate(tree.body) if isinstance(n,ast.For))]
ns={'__file__':str(ROOT/'tests/test_gate_drive.py')}
exec(compile(ast.Module(body=prefix,type_ignores=[]),'<migration-fixture>','exec'),ns)
ns['MOCK']=ns['MOCK'].replace('function o:setHealth(v) self.health=v end',
    'function o:setHealth(v) self.health=v end\n function o:getHealth() return self.health end\n function o:getMaxHealth() return self.maxHealth end\n function o:invalidateRenderChunkLevel(flags) self.redraw=flags end')
# kind, legacy recorded health, expected new maximum
for kind,legacy,expected in (('chainlink',600,1800),('chainlink4',950,3000),('chainlink',400,1200),('chainlink4',None,1200)):
    lua=ns['runtime']()
    g=lua.globals();g.kind=kind;g.legacy=legacy;g.expected=expected
    lua.execute(r'''
loaders={};starts={}
Events.OnGameStart={Add=function(fn) table.insert(starts,fn) end}
Events.LoadGridsquare={Add=function(fn) table.insert(loaders,fn) end}
function loadSquare(sq) for _,fn in ipairs(loaders) do fn(sq) end end
require 'SG_Gate'
id=SGGate.build(square(30,20,0),kind,6)
local entry=SGGate.registry()[id]
assert(entry.version==SGGate.DATA_VERSION and entry.health==1800)
for _,p in ipairs(SGGate.parts(id)) do
 function p:getHealth() return self.health end
 function p:getMaxHealth() return self.maxHealth end
 assert(p.md.sgVersion==SGGate.DATA_VERSION)
end
for _,fn in ipairs(starts) do fn() end -- recovery ready
-- Rewind to a version 1 save: no versions, old-formula health on the registry and carriers.
local old=legacy or (kind=='chainlink4' and 450 or 300)
entry.version=nil;entry.health=legacy
local doors={}
for _,p in ipairs(SGGate.parts(id)) do
 p.md.sgVersion=nil
 if p.md.sgRole=='leaf' or p.md.sgRole=='slave' or p.md.sgRole=='block' then
  p.maxHealth=old;p.health=old;doors[#doors+1]=p
 end
end
local slave=SGGate.findRole(id,'slave');slave.health=old*0.4
local before=SGGate.damageForRatio(0.4)
for _,p in ipairs(SGGate.parts(id)) do loadSquare(p:getSquare()) end
assert(entry.version==SGGate.DATA_VERSION and entry.health==expected)
for _,p in ipairs(SGGate.parts(id)) do assert(p.md.sgVersion==SGGate.DATA_VERSION) end
for _,p in ipairs(doors) do assert(p.maxHealth==expected) end
assert(slave.health==math.floor(expected*0.4+0.5))
assert(SGGate.findRole(id,'leaf').health==expected)
assert(SGGate.updateDamage(id)==before)
-- A second load must not rescale again.
slave.health=1
for _,p in ipairs(SGGate.parts(id)) do loadSquare(p:getSquare()) end
assert(slave.health==1 and slave.maxHealth==expected)
''')
    print(f'PASS {kind} legacy health {legacy} -> {expected}: registry/part versions, damage fraction kept, idempotent')
