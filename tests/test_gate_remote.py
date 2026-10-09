"""RF pairing, inventory/hotkey routing and authority/network regressions."""
import ast
from pathlib import Path
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
source = ast.parse((ROOT/'tests/test_gate_drive.py').read_text())
prefix = source.body[:next(i for i, node in enumerate(source.body) if isinstance(node, ast.For))]
ns = {'__file__': str(ROOT/'tests/test_gate_drive.py')}
exec(compile(ast.Module(body=prefix, type_ignores=[]), '<drive-fixture>', 'exec'), ns)

for server in (False, True):
    for width in (2, 4):
        for orientation in ('N', 'W'):
            lua = ns['runtime']()
            lua.globals().serverMode, lua.globals().width, lua.globals().orientation = server, width, orientation
            lua.execute(r'''
require 'SG_GateRemote'
function getText(key) return key end
function settle(id)
 local leaf=SGGate.findRole(id,'leaf');leaf.animating=false
 for i=1,400 do if tick then tick() end end
end
local kind=width==2 and 'chainlink' or 'chainlink4'
a=SGGate.build(square(30,20,0),kind,0,orientation)
b=SGGate.build(square(60,20,0),kind,0,orientation)
da=SGGate.installDrive(a,{});db=SGGate.installDrive(b,{})
assert(da.md.sgDriveIdentity~=db.md.sgDriveIdentity)
da:getSquare().electricity=true;db:getSquare().electricity=true
p=character(da:getSquare());q=character(da:getSquare())
r1=add(p.inv,SGGateRemote.itemType);r2=add(p.inv,SGGateRemote.itemType)
local bag=add(p.inv,'Base.KeyRing');bag.bag=true;bag.inv=container()
r3=add(bag.inv,SGGateRemote.itemType)
local ia=SGGate.findRole(a,'leaf').md.sgInstance
local ib=SGGate.findRole(b,'leaf').md.sgInstance
assert(not SGGateRemote.pair(q,a,ia,r1.id,da.md.sgDriveIdentity))
assert(not SGGateRemote.pair(p,a,ia+1,r1.id,da.md.sgDriveIdentity))
assert(not SGGateRemote.pair(p,a,ia,r1.id,da.md.sgDriveIdentity+1))
assert(SGGateRemote.pair(p,a,ia,r1.id,da.md.sgDriveIdentity))
assert(SGGateRemote.pair(p,a,ia,r3.id,da.md.sgDriveIdentity))
assert(SGGateRemote.linked(r1,da) and SGGateRemote.linked(r3,da))
if serverMode then assert(r1.syncs==1 and r3.syncs==1) end
-- Borrowing another remote's metadata cannot authorise a different physical item.
r2.md=copyTable(r1.md);assert(not SGGateRemote.linked(r2,da));r2.md={}
assert(SGGateRemote.pair(p,a,ia,r2.id,da.md.sgDriveIdentity))
p.x=db:getSquare().x+.5;p.y=db:getSquare().y+.5
assert(SGGateRemote.pair(p,b,ib,r2.id,db.md.sgDriveIdentity))
assert(not SGGateRemote.linked(r2,da) and SGGateRemote.linked(r2,db))
assert(da.md.sgDriveData.sgRemotes[r2.md.sgRemoteKey]==nil)
-- Hotkey target is the nearest linked gate; explicit inventory selection uses that remote.
p.x=(da:getSquare().x+db:getSquare().x)/2+.5
p.y=da:getSquare().y+.5
assert(SGGateRemote.nearest(p)==a)
assert(SGGateRemote.nearest(p,r2)==b)
assert(SGGateRemote.activate(p))
assert(SGGate.findRole(a,'leaf'):IsOpen() and not SGGate.findRole(b,'leaf'):IsOpen())
assert(not SGGateRemote.activate(p)) -- busy closest gate never falls through to b
settle(a)
assert(SGGateRemote.activate(p,r2));settle(b)
-- Exactly 20 cells succeeds; 20.01, wrong floor, death, missing power reject.
p.x=da:getSquare().x+.5-20;p.y=da:getSquare().y+.5
assert(SGGateRemote.nearest(p,r1)==a)
p.x=p.x-.01;assert(not SGGateRemote.nearest(p,r1));p.x=p.x+.01
p.z=1;assert(not SGGateRemote.nearest(p,r1));p.z=0
p.dead=true;assert(not SGGateRemote.activate(p,r1));p.dead=false
da:getSquare().electricity=false;assert(not SGGateRemote.activate(p,r1))
assert(p.message=='Tooltip_SG_Drive_power');da:getSquare().electricity=true
-- Packet validation rejects stolen IDs, stale state, wrong drive and rebuilt gate.
local state=SGGate.snapshot(a)
local args={id=a,instance=ia,revision=state.revision,open=false,remoteId=r1.id,driveIdentity=da.md.sgDriveIdentity}
assert(not SGGateRemote.handleRequest(q,args))
args.revision=args.revision-1;assert(not SGGateRemote.handleRequest(p,args));args.revision=state.revision
args.driveIdentity=db.md.sgDriveIdentity;assert(not SGGateRemote.handleRequest(p,args));args.driveIdentity=da.md.sgDriveIdentity
SGGate.findRole(a,'leaf').obstructed=true
assert(not SGGateRemote.handleRequest(p,args));SGGate.findRole(a,'leaf').obstructed=false
assert(SGGateRemote.handleRequest(p,args));assert(not SGGateRemote.handleRequest(p,args));settle(a)
assert(SGGateRemote.handleRequest(p,args)) -- repeated desired state does not toggle back
r1.broken=true;assert(not SGGateRemote.activate(p,r1));r1.broken=false
-- Physical remote can change hands without losing its legitimate association.
p.inv:Remove(r1);q.inv:AddItem(r1)
assert(SGGateRemote.activate(q,r1));settle(a)
-- Portable drive preserves identity and pairing across removal/reinstallation.
local saved=copyTable(da.md.sgDriveData);local oldToken=da.md.sgDriveIdentity
assert(SGGate.removeDrive(a));da=SGGate.installDrive(a,saved)
da:getSquare().electricity=true
assert(da.md.sgDriveIdentity==oldToken and SGGateRemote.linked(r1,da))
SGGate.remove(a);a=SGGate.build(square(30,20,0),kind,0,orientation)
da=SGGate.installDrive(a,{});assert(da.md.sgDriveIdentity~=oldToken)
assert(not SGGateRemote.linked(r1,da))
clientMode=true
assert(not SGGateRemote.pair(q,a,SGGate.findRole(a,'leaf').md.sgInstance,r1.id,da.md.sgDriveIdentity))
assert(not SGGateRemote.handleRequest(q,args))
''')
            print(f'PASS RF server={server} width={width} {orientation}: pairing, bags, nearest, range, state, possession and lifecycle')

lua = ns['runtime']()
lua.execute(r'''
require 'SG_GateRemote'
function getText(key) return key end
id=SGGate.build(square(30,20,0),'chainlink')
drive=SGGate.installDrive(id,{});drive:getSquare().electricity=true
leaf=SGGate.findRole(id,'leaf');p=character(drive:getSquare())
remote=add(p.inv,SGGateRemote.itemType)
assert(SGGateRemote.pair(p,id,leaf.md.sgInstance,remote.id,drive.md.sgDriveIdentity))
ISBaseTimedAction={derive=function(_,name) local c={Type=name};c.__index=c;return c end,
 new=function(class,character) return setmetatable({character=character},class) end,
 perform=function() performed=true end}
package.preload['TimedActions/ISBaseTimedAction']=function() return true end
require 'SG_GateRemoteAction'
local action=ISSlidingGateRemotePair:new(p,id,leaf.md.sgInstance,remote.id,drive.md.sgDriveIdentity)
assert(action.remoteId==remote.id and action.driveIdentity==drive.md.sgDriveIdentity and action.maxTime==30)
assert(action:isValid())
clientMode=true;action:perform();assert(performed and not action:complete())
clientMode=false;assert(action:complete())
-- Client presses generate versioned commands only, sharing normal pending/result handling.
clientMode=true;serverMode=false
function getPlayer() return p end
function getSpecificPlayer() return p end
function getTimestampMs() return 100 end
packets={};function sendClientCommand(player,module,command,args)
 table.insert(packets,{player=player,module=module,command=command,args=args}) end
Events.OnServerCommand={Add=function(fn) receive=fn end}
require 'SG_GateNetwork'
assert(SGGateRemote.activate(p,remote));assert(#packets==1 and not leaf:IsOpen())
assert(packets[1].command=='remote' and packets[1].args.remoteId==remote.id)
assert(packets[1].args.driveIdentity==drive.md.sgDriveIdentity)
assert(not SGGateRemote.activate(p,remote) and #packets==1)
receive('SlidingGates','result',{id=id,request=packets[1].args.request,remote=true,accepted=false,reason='power'})
assert(p.message=='Tooltip_SG_Drive_power')
assert(SGGateRemote.activate(p,remote) and #packets==2)
-- Menu and hotkey use the same activation function, including grouped inventory entries.
ISTimedActionQueue={add=function(action) queued=action end}
package.preload['TimedActions/ISTimedActionQueue']=function() return true end
luautils={walkAdj=function() return true end}
Events.OnFillInventoryObjectContextMenu={Add=function(fn) inventoryMenu=fn end}
require 'SG_GateRemoteMenu'
local options={};local context={addOption=function(_,label,target,callback,...)
 local o={label=label,target=target,callback=callback,args={...}};table.insert(options,o);return o end}
local original=SGGateRemote.activate;uses=0
SGGateRemote.activate=function(character,item) assert(character==p);uses=uses+1;selected=item end
inventoryMenu(0,context,{{items={remote}},remote})
assert(#options==1 and options[1].label=='ContextMenu_SG_UseRemote')
options[1].callback(options[1].target,unpack(options[1].args));assert(uses==1 and selected==remote)
keyBinding={};Keyboard={KEY_F9=67};package.preload['keyBinding']=function() return true end
local core={text=false,key=67}
function core:isDoingTextEntry() return self.text end
function core:isKey(_,key) return key==self.key or key==68 end -- alternate binding too
function getCore() return core end
paused=false;function isGamePaused() return paused end
Events.OnKeyPressed={Add=function(fn) pressed=fn end}
require 'SG_GateRemoteKey'
assert(#keyBinding==2 and keyBinding[2].value=='SG_UseRemote' and keyBinding[2].key==67)
pressed(66);assert(uses==1)
core.text=true;pressed(67);assert(uses==1);core.text=false
paused=true;pressed(67);assert(uses==1);paused=false
pressed(67);assert(uses==2 and selected==nil)
pressed(68);assert(uses==3 and selected==nil)
p.dead=true;pressed(67);assert(uses==3)
SGGateRemote.activate=original
''')
print('PASS RF client: pair action fields, no client mutation, command/pending/result, inventory and remappable hotkey')

lua = ns['runtime']()
lua.execute(r'''
serverMode=true
Events.OnClientCommand={Add=function(fn) command=fn end}
sent={};function sendServerCommand(...) table.insert(sent,{...}) end
require 'SG_GateServer'
id=SGGate.build(square(30,20,0),'chainlink')
drive=SGGate.installDrive(id,{});drive:getSquare().electricity=true
leaf=SGGate.findRole(id,'leaf');p=character(drive:getSquare())
r=add(p.inv,SGGateRemote.itemType)
assert(SGGateRemote.pair(p,id,leaf.md.sgInstance,r.id,drive.md.sgDriveIdentity))
p.x=p.x+10 -- accepted RF distance exceeds the manual three-cell limit
local state=SGGate.snapshot(id)
local args={id=id,instance=state.instance,revision=state.revision,open=true,request=8,
 remoteId=r.id,driveIdentity=drive.md.sgDriveIdentity}
command('SlidingGates','remote',p,args)
local reply=sent[#sent][4]
assert(reply.accepted and reply.remote and reply.request==8 and leaf:IsOpen())
command('SlidingGates','remote',p,args)
reply=sent[#sent][4];assert(not reply.accepted and reply.reason=='busy')
command('SlidingGates','remote',p,{id='invalid',open=true})
reply=sent[#sent][4];assert(not reply.accepted and reply.reason=='invalid')
''')
print('PASS RF server command: 10-cell operation, replicated result, duplicate and malformed request rejection')
