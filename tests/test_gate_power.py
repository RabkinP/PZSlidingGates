"""Authority battery container, charge, powered movement and teardown regression."""
import ast
from pathlib import Path
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
source = ast.parse((ROOT / 'tests/test_gate_drive.py').read_text())
prefix = source.body[:next(i for i, node in enumerate(source.body) if isinstance(node, ast.For))]
ns = {'__file__': str(ROOT / 'tests/test_gate_drive.py')}
exec(compile(ast.Module(body=prefix, type_ignores=[]), '<drive-fixture>', 'exec'), ns)

for server in (False, True):
    for orientation in ('N', 'W'):
        for width in (2, 4):
            lua = ns['runtime']()
            lua.globals().serverMode = server
            lua.globals().orientation = orientation
            lua.globals().width = width
            lua.execute(r'''
require 'SG_GateDrive'
oldInstance=instanceItem
function instanceItem(kind)
 local item=oldInstance(kind);item.charge=0.5;item.condition=80
 function item:getCondition() return self.condition end
 function item:getCurrentUsesFloat() return self.charge end
 function item:setUsedDelta(v) self.charge=v end
 return item
end
function instanceof(item,kind)
 if kind=='DrainableComboItem' then return item.kind and item.kind:match('^Base.CarBattery%d$')~=nil end
 return kind=='InventoryContainer' and item.bag or false
end
stats=0;function sendItemStats() stats=stats+1 end
id=SGGate.build(square(30,20,0),width==2 and 'chainlink' or 'chainlink4',0,orientation)
leaf=SGGate.findRole(id,'leaf');identity=leaf.md.sgInstance
drive=SGGate.installDrive(id,{owned=true});sq=drive:getSquare()
p=character(sq);c=drive:getContainer()
assert(c.capacity==5 and c.explored and c.accept=='SGGatePower.acceptBattery')
for _,kind in ipairs({'Base.CarBattery1','Base.CarBattery2','Base.CarBattery3'}) do
 assert(SGGatePower.acceptBattery(c,instanceItem(kind)))
end
assert(not SGGatePower.acceptBattery(c,instanceItem('PSR.SuperBattery')))
assert(not SGGatePower.acceptBattery(c,instanceItem('Base.Battery')))
b=instanceItem('Base.CarBattery1');c:AddItem(b)
assert(SGGatePower.acceptBattery(c,b))
assert(not SGGatePower.acceptBattery(c,instanceItem('Base.CarBattery2')))
assert(SGGatePower.source(drive)=='battery')
assert(not SGGate.removeDrive(id))
assert(not SGGateDrive.check(p,id,identity,false))
assert(SGGatePower.complete(p,id,identity,true))
assert(math.abs(b.charge-0.49)<1e-6)
assert(drive.hotSave)
assert(not SGGatePower.complete(p,id,identity,true))
assert(math.abs(b.charge-0.49)<1e-6)
-- Finish the native movement; blocked powered closing has no energy cost.
leaf.animating=false
for i=1,400 do if tick then tick() end end
square(sq.x,sq.y,sq.z).vehicle=true
assert(not SGGatePower.complete(p,id,identity,false));assert(math.abs(b.charge-0.49)<1e-6)
sq.vehicle=false
b.charge=0.009;assert(SGGatePower.source(drive)=='none')
assert(not SGGatePower.complete(p,id,identity,false))
b.charge=0.01;assert(SGGatePower.complete(p,id,identity,false))
assert(math.abs(b.charge)<1e-6)
leaf.animating=false;for i=1,400 do if tick then tick() end end
sq.electricity=true
assert(SGGatePower.complete(p,id,identity,true));assert(b.charge==0)
leaf.animating=false;for i=1,400 do if tick then tick() end end
-- Charging depends on observed elapsed game time, never on repeated ticks/reloads.
SGGatePower.charge(drive,10);SGGatePower.charge(drive,10+1/60)
assert(math.abs(b.charge-0.1/60)<1e-6)
local before=b.charge;SGGatePower.charge(drive,10+1/60);assert(b.charge==before)
sq.electricity=false;SGGatePower.charge(drive,10+2/60);assert(b.charge==before)
sq.electricity=true;b.condition=0;SGGatePower.charge(drive,10+3/60);assert(b.charge==before)
b.condition=80;b.charge=0.9999;SGGatePower.charge(drive,10+4/60);assert(b.charge==1)
local beforeStats=stats;clientMode=true
assert(not SGGatePower.complete(p,id,identity,false))
SGGatePower.charge(drive,11);assert(stats==beforeStats and b.charge==1)
clientMode=false
assert(not SGGatePower.complete(p,id,identity+1,false))
p.dead=true;assert(not SGGatePower.complete(p,id,identity,false));p.dead=false
p.x=p.x+10;assert(not SGGatePower.complete(p,id,identity,false));p.x=p.x-10
-- Successful dismantle returns the original battery and drive exactly once.
drops={};local dropSq=leaf:getSquare()
function dropSq:AddWorldInventoryItem(item) table.insert(drops,item);return item end
function ZombRand() return 99 end
assert(SGGate.destroyGate(id,nil,70,true));assert(#drops==2)
assert(drops[1]==b and b.charge==1 and b.condition==80)
assert(drops[2].kind=='SlidingGates.GateDrive')
assert(not SGGate.destroyGate(id,nil,70,true) and #drops==2)
assert(stats==(serverMode and beforeStats or 0))
''')
            print(f'PASS battery power server={server} {orientation} width={width}: filtering, cost, grid, charging, authority, teardown')

lua = LuaRuntime()
compile_lua = lua.eval('function(s) local f,e=loadstring(s);assert(f,e) end')
for path in (ROOT/'mod/SlidingGates/42/media/lua').rglob('*.lua'):
    compile_lua(path.read_text(encoding='utf-8'))
print('PASS Lua 5.1 syntax')

lua = ns['runtime']()
lua.execute(r'''
require 'SG_GateDrive'
ISBaseTimedAction={derive=function(_,name) local c={Type=name};c.__index=c;return c end,
 new=function(class,character) return setmetatable({character=character},class) end,
 perform=function() performed=true end}
package.preload['TimedActions/ISBaseTimedAction']=function() return true end
require 'SG_GatePowerAction'
id=SGGate.build(square(30,20,0),'chainlink')
leaf=SGGate.findRole(id,'leaf');drive=SGGate.installDrive(id,{})
drive:getSquare().electricity=true;p=character(drive:getSquare())
local action=ISSlidingGatePower:new(p,id,leaf.md.sgInstance,true)
assert(action.gateId==id and action.instance==leaf.md.sgInstance and action.opening and action.maxTime==1)
assert(action:isValid())
clientMode=true;action:perform();assert(performed and not leaf:IsOpen())
assert(not action:complete() and not leaf:IsOpen())
clientMode=false;assert(action:complete() and leaf:IsOpen())
assert(not action:complete())
''')
print('PASS powered timed action: primitive fields, authority-only completion and no duplicate movement')
