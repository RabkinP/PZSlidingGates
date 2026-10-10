"""Reflected assembly mechanics and metadata/MP regressions (Lua 5.1 mocks)."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
tree = ast.parse((ROOT/'tests/test_gate_drive.py').read_text())
prefix = tree.body[:next(i for i,n in enumerate(tree.body) if isinstance(n,ast.For))]
ns = {'__file__':str(ROOT/'tests/test_gate_drive.py')}
exec(compile(ast.Module(body=prefix,type_ignores=[]),'<drive-fixture>','exec'),ns)

for width in (2,4):
    for orientation in ('N','W'):
        for server in (False,True):
            lua=ns['runtime']()
            lua.globals().width=width
            lua.globals().orientation=orientation
            lua.globals().serverMode=server
            lua.execute(r'''
require 'SG_GateDrive'
require 'SG_GateRemote'
local kind=width==2 and 'chainlink' or 'chainlink4'
assert(not SGGate.canBuild(square(30,20,0),kind,orientation,'bad'))
function c(k) return SGGate.cellAt(30,20,0,k,orientation,'reverse') end
c(1).fence=true
assert(not SGGate.canBuild(square(30,20,0),kind,orientation,'reverse'));c(1).fence=false
id=SGGate.build(square(30,20,0),kind,5,orientation,'reverse')
assert(SGGate.direction(id)=='reverse' and SGGate.snapshot(id).direction=='reverse')
leaf=SGGate.findRole(id,'leaf');instance=leaf.md.sgInstance
assert(leaf:getSquare()==c(1) and leaf.north==(orientation=='N'))
local model=orientation=='N' and SGGateTypes[kind].reverseLeafModel or SGGateTypes[kind].westReverseLeafModel
assert(leaf.model=='Base.'..model..'_Closed')
for _,part in ipairs(SGGate.parts(id)) do
 assert(part.md.sgDirection=='reverse' and part.md.sgOrientation==orientation)
 if part.md.sgRole=='collider' then
  assert(part.sprite==(orientation=='N' and 'fixtures_doors_fences_01_36' or 'fixtures_doors_fences_01_38'))
 end
end
assert(#partsWithRole(id,'slave')==width and #partsWithRole(id,'rail')==2*width)
assert(SGGateDrive.square(id)==c(width))
p=character(c(width))
add(p.inv,SGGateDrive.itemType)
add(p.inv,'Base.Screwdriver','screwdriver');add(p.inv,'Base.Wrench','wrench')
for i=1,4 do add(p.inv,'Base.Screws') end
assert(SGGateDrive.complete(p,id,instance,true))
local drive=SGGate.findRole(id,'drive')
assert(drive:getSquare()==c(width))
assert(drive.model=='Base.SG_Drive_Reverse'..(orientation=='W' and '_W' or '')..'_Static')
drive:getSquare().electricity=true
-- Reflected destination checks; refusal never consumes energy or starts sound.
c(width+1).vehicle=true
assert(not SGGatePower.complete(p,id,instance,true));assert(#worldSounds==0)
c(width+1).vehicle=false
local neighbour=SGGate.edgeNeighbour(c(width+1),orientation)
missing=neighbour:getX()..','..neighbour:getY()..',0'
assert(not SGGate.toggle(id));missing=nil
local function blocked(k) return c(k):isBlockedTo(SGGate.edgeNeighbour(c(k),orientation)) end
function finish()
 delta=1
 for i=1,width do if tick then tick() end end
 leaf.animating=false;if tick then tick() end
 assert(not SGGate.isMoving(id))
end
-- A linked RF remote uses the reflected drive and preserves motion identity.
local r=add(p.inv,SGGateRemote.itemType)
assert(SGGateRemote.pair(p,id,instance,r.id,drive.md.sgDriveIdentity))
assert(SGGateRemote.activate(p,r))
assert(SGGate.snapshot(id).motor and SGGate.snapshot(id).direction=='reverse')
delta=1
for progress=1,width do
 tick()
 for k=1,width do assert(blocked(k)==(k>progress)) end
 for k=1,width do assert(blocked(width+k)==(k<=math.min(width,progress+1))) end
end
leaf.animating=false;if tick then tick() end
assert(leaf.model=='Base.'..model..'_Open')
c(1).vehicle=true;assert(not SGGatePower.complete(p,id,instance,false));c(1).vehicle=false
assert(SGGatePower.complete(p,id,instance,false));finish()
for k=1,width do assert(blocked(k)) end
for k=width+1,2*width do assert(not blocked(k)) end
-- Pocket E input closes the reflected leaf through its hidden proxy.
assert(SGGate.toggle(id));finish()
if not serverMode then
 local pocket=partsWithRole(id,'block')[width]
 pocket:ToggleDoor();assert(not leaf:IsOpen() and SGGate.isMoving(id));finish()
 assert(SGGate.toggle(id));finish()
end
-- Existing fences keep the correct edge/physics behavior in the new pocket.
c(width+1).fence=true
assert(SGGate.toggle(id));finish()
assert(SGGate.toggle(id));finish()
local opaque
for _,part in ipairs(partsWithRole(id,'block')) do if part.md.sgOpaque then opaque=part end end
assert(opaque and opaque.north==(orientation=='N'))
-- Interrupted motion and partial chunks restore direction and all collisions.
assert(SGGate.toggle(id))
neighbour=SGGate.edgeNeighbour(c(2*width),orientation)
missing=neighbour:getX()..','..neighbour:getY()..',0';gameStart()
assert(SGGate.isMoving(id));missing=nil
for i=1,120 do if tick then tick() end end
leaf.animating=false
assert(SGGate.direction(id)=='reverse' and not SGGate.isMoving(id))
-- Find parts before a client registry snapshot, from either side of the catcher.
local saved=SGGate.registry()[id];SGGate.registry()[id]=nil
assert(SGGate.direction(id)=='reverse' and SGGate.orientation(id)==orientation)
assert(SGGate.gateWidth(id)==width and SGGate.findRole(id,'leaf')==leaf)
SGGate.registry()[id]=saved
assert(SGGateDrive.complete(p,id,instance,false))
assert(not SGGate.findRole(id,'drive'))
SGGate.remove(id)
for k=0,2*width do assert(#c(k).objects==0) end
assert(SGGate.direction('99,99,0')=='forward')
''')
            print(f'PASS reverse {width}/{orientation}/server={server}: cells, models, vehicles, RF/power/audio, collision, pocket E, fences, reload and cleanup')

for orientation in ('N','W'):
    lua=ns['runtime']()
    lua.globals().orientation=orientation
    lua.execute(r'''
clientMode=true;now=0;commands={}
function getTimestampMs() return now end
function sendClientCommand(...) table.insert(commands,{...}) end
Events.OnServerCommand={Add=function(fn) receive=fn end}
require 'SG_GateNetwork'
id='30,20,0';kind='chainlink4'
function c(k) return SGGate.cellAt(30,20,0,k,orientation,'reverse') end
local slave=IsoThumpable.new(nil,c(2))
slave.md={sgGate=id,sgRole='slave',sgWidth=4,sgOrientation=orientation,sgDirection='reverse',sgInstance=1,sgBase='SG_Hidden'}
c(2):AddSpecialObject(slave)
gridLoaded(c(2))
assert(SGGate.direction(id)=='reverse' and SGGate.gateWidth(id)==4)
local model=orientation=='N' and SGGateTypes[kind].reverseLeafModel or SGGateTypes[kind].westReverseLeafModel
leaf=IsoThumpable.new(nil,c(1))
leaf.md={sgGate=id,sgRole='leaf',sgWidth=4,sgOrientation=orientation,sgDirection='reverse',sgInstance=1,sgBase=model,sgType=kind}
c(1):AddSpecialObject(leaf);p=character(c(1));function getPlayer() return p end
receive('SlidingGates','snapshot',{id=id,instance=1,revision=1,width=4,type=kind,orientation=orientation,direction='reverse',open=false,moving=false,slavesOpen=false})
assert(leaf.model=='Base.'..model..'_Closed' and SGGate.direction(id)=='reverse')
assert(SGGate.toggle(id,p));assert(commands[#commands][4].open==true)
receive('SlidingGates','state',{id=id,instance=1,revision=2,width=4,type=kind,orientation=orientation,direction='reverse',open=true,moving=true,slavesOpen=false})
assert(not leaf:IsOpen() and leaf.md.sgDirection=='reverse')
leaf.open=true;sync()
receive('SlidingGates','state',{id=id,instance=1,revision=3,width=4,type=kind,orientation=orientation,direction='reverse',open=true,moving=false,slavesOpen=true})
assert(leaf.model=='Base.'..model..'_Open')
receive('SlidingGates','state',{id=id,instance=1,revision=2,width=4,type=kind,orientation=orientation,direction='forward',open=false,moving=false,slavesOpen=false})
assert(SGGate.direction(id)=='reverse' and leaf.md.sgDirection=='reverse')
''')
    print(f'PASS reverse {orientation} client: slave-first loading, snapshots, native animation ordering and stale direction rejection')
