"""Authority/client regressions; mocks do not prove native packet delivery or gameplay."""
import ast
from pathlib import Path
from lupa import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
LUA = ROOT/'mod/SlidingGates/42/media/lua'
tree = ast.parse((ROOT/'tests/test_gate_widths.py').read_text())
MOCK = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == 'MOCK' for target in node.targets))

def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().package.path = ';'.join(str(LUA/path/'?.lua').replace('\\','/') for path in ('shared','client','server')) + ';' + lua.globals().package.path
    lua.execute(MOCK)
    lua.execute(r'''
    function character(x,y,z)
      local p={x=x,y=y,z=z,dead=false}
      function p:getX() return self.x end
      function p:getY() return self.y end
      function p:getCurrentSquare() return square(math.floor(self.x),math.floor(self.y),self.z) end
      function p:isDead() return self.dead end
      function p:setHaloNote() end
      return p
    end
    ''')
    return lua

for width in (2,4):
    lua = runtime()
    lua.execute(r'''
    serverMode=true
    Events.OnClientCommand={Add=function(fn) command=fn end}
    sent={}; function sendServerCommand(...) table.insert(sent,{...}) end
    ''')
    lua.execute('require "SG_GateServer"')
    lua.globals().width = width
    lua.execute(r'''
    local kind=width==2 and 'chainlink' or 'chainlink4'
    id=SGGate.build(square(30,20,0),kind)
    leaf=partsWithRole(id,'leaf')[1]
    for _,o in ipairs(SGGate.parts(id)) do
      assert(o.sent==1 and o.md.sgInstance and o.md.sgWidth==width)
    end
    player=character(29.5,20.5,0)
    function request(open)
      local s=SGGate.snapshot(id)
      return {id=id,instance=s.instance,revision=s.revision,open=open,request=1}
    end
    -- Native/Java packets alone cannot switch authoritative state or lock the server forever.
    leaf:ToggleDoor()
    assert(not leaf:IsOpen() and not SGGate.isMoving(id))
    assert(not SGGate.snapshot(id).open)
    local instance=SGGate.snapshot(id).instance
    local bad=request(true); bad.instance=instance+1
    local ok,reason=SGGate.handleRequest(player,bad); assert(not ok and reason=='instance')
    bad=request(true); bad.revision=bad.revision-1
    ok,reason=SGGate.handleRequest(player,bad); assert(not ok and reason=='stale')
    player.z=1; ok,reason=SGGate.handleRequest(player,request(true)); assert(not ok and reason=='distance')
    player.z=0; player.x=50
    ok,reason=SGGate.handleRequest(player,request(true)); assert(not ok and reason=='distance')
    player.x=29.5; player.dead=true
    assert(not SGGate.handleRequest(player,request(true))); player.dead=false
    leaf.obstructed=true
    ok,reason=SGGate.handleRequest(player,request(true)); assert(not ok and reason=='blocked')
    leaf.obstructed=false
    local normalObstruction=leaf.isObstructed
    local previousSync=leaf.synced or 0
    leaf.isObstructed=function(self) return self.open end -- obstruction changes after native preflight
    ok,reason=SGGate.handleRequest(player,request(true))
    assert(not ok and reason=='blocked' and not leaf:IsOpen() and not SGGate.snapshot(id).open)
    assert((leaf.synced or 0)>previousSync) -- rollback is also sent to native clients
    leaf.isObstructed=normalObstruction
    local first=request(true)
    assert(SGGate.handleRequest(player,first))
    local revision=SGGate.snapshot(id).revision
    assert(SGGate.handleRequest(player,first)) -- duplicate desired state is idempotent
    assert(SGGate.snapshot(id).revision==revision)
    ok,reason=SGGate.handleRequest(player,request(false)); assert(not ok and reason=='busy')
    -- Server ignores render flags, even if native isAnimating remains true forever.
    delta=1
    for step=1,width do tick() end
    assert(SGGate.isMoving(id))
    tick()
    assert(not SGGate.isMoving(id) and leaf:IsOpen() and not leaf:isAnimating())
    for k=1,width do assert(not blocked(30-k)) end
    for k=width+1,2*width do assert(blocked(30-k)) end
    -- A competing native packet on a slave must not bypass the command validation.
    partsWithRole(id,'slave')[width]:ToggleDoor()
    assert(leaf:IsOpen() and partsWithRole(id,'slave')[width]:IsOpen())
    assert(not SGGate.isMoving(id))
    -- Closing marker false survives save/restart and delayed chunk load.
    assert(SGGate.handleRequest(player,request(false)))
    assert(data.SlidingGates.gates[id].moving==false)
    ''')
    # Reload controller locals while preserving world objects/global modData, like a server restart.
    lua.execute('SGGate.coreLoaded=nil; tick=nil')
    lua.execute((LUA/'shared/SG_GateCore.lua').read_text())
    lua.execute(r'''
    missing=(30-2*width)..',20,0'; serverStart()
    assert(data.SlidingGates.gates[id].moving==false and SGGate.isMoving(id))
    missing=nil
    for step=1,60 do if tick then tick() end end
    assert(not SGGate.isMoving(id) and not leaf:IsOpen())
    assert(data.SlidingGates.gates[id].moving==nil)
    local previous=SGGate.snapshot(id)
    local orphan=partsWithRole(id,'rail')[1]
    local orphanSquare=orphan:getSquare()
    SGGate.remove(id)
    orphanSquare:AddTileObject(orphan) -- old chunk loads after the rest was removed
    gridLoaded(orphanSquare)
    assert(#orphanSquare.objects==0)
    id=SGGate.build(square(30,20,0),width==2 and 'chainlink' or 'chainlink4')
    assert(SGGate.snapshot(id).instance>previous.instance)
    local ok,reason=SGGate.handleRequest(player,{id=id,instance=previous.instance,revision=previous.revision,open=true})
    assert(not ok and reason=='instance')
    command('SlidingGates','toggle',player,{id='invalid',open=true})
    command('SlidingGates','toggle',player,request(true))
    assert(#sent>0 and sent[#sent][3]=='result' and sent[#sent][4].accepted)
    ''')
    print(f'PASS server {width}: authority, replication, identity, revision, proximity, concurrent commands, clock, restart')

# Clients never load world constructors. Replicated doors/objects are mocked as already received.
client = runtime()
client.execute(r'''
clientMode=true; now=0; commands={}
function getTimestampMs() return now end
Events.OnServerCommand={Add=function(fn) receive=fn end}
Events.LoadGridsquare={Add=function(fn) loaded=fn end}
function sendClientCommand(...) table.insert(commands,{...}) end
player=character(29.5,20.5,0)
function getPlayer() return player end
''')
client.execute('require "SG_Gate"')
client.execute(r'''
assert(SGGate.build==nil and SGGate.destroyGate==nil and SGGate.finalize==nil)
local id='30,20,0'
leaf=IsoThumpable.new(nil,square(29,20,0))
leaf.md={sgGate=id,sgRole='leaf',sgBase='SG_ChainLink_4_N_Right_G',sgType='chainlink4',sgWidth=4,sgInstance=1,sgRevision=1}
square(29,20,0):AddSpecialObject(leaf)
data.SlidingGates={gates={[id]={width=4}}}
receive('SlidingGates','snapshot',{id=id,instance=1,revision=1,width=4,type='chainlink4',open=false,moving=false,slavesOpen=false})
assert(SGGate.toggle(id,player))
assert(not leaf:IsOpen() and #commands==1 and SGGate.isMoving(id))
local request=commands[1][4]
receive('SlidingGates','state',{id=id,instance=1,revision=2,width=4,type='chainlink4',open=true,moving=true,slavesOpen=false})
-- A state notification cannot pre-toggle and suppress the upcoming native animation packet.
assert(not leaf:IsOpen() and SGGate.isMoving(id))
receive('SlidingGates','result',{id=id,request=request.request,accepted=true})
leaf.open=true; sync() -- native packet/animation arrives
assert(#commands==1) -- no echo command while the gate moves
receive('SlidingGates','state',{id=id,instance=1,revision=3,width=4,type='chainlink4',open=true,moving=false,slavesOpen=true})
assert(not SGGate.isMoving(id) and leaf.model=='Base.SG_ChainLink_4_N_Right_G_Open')
receive('SlidingGates','state',{id=id,instance=1,revision=2,width=4,type='chainlink4',open=false,moving=false,slavesOpen=false})
assert(leaf.md.sgOpen and leaf.md.sgRevision==3) -- reordered stale update is ignored
-- Load snapshot during a late join uses the target resting pose, with no local blockers/animation.
receive('SlidingGates','snapshot',{id=id,instance=1,revision=4,width=4,type='chainlink4',open=false,moving=true,slavesOpen=true})
assert(not leaf:IsOpen() and leaf.md.sgMoving==false and SGGate.isMoving(id))
receive('SlidingGates','state',{id=id,instance=1,revision=5,width=4,type='chainlink4',open=false,moving=false,slavesOpen=false})
assert(SGGate.toggle(id,player)); now=6000
assert(not SGGate.isMoving(id)) -- unanswered requests expire and ask for a snapshot
assert(commands[#commands][3]=='snapshot')
receive('SlidingGates','removed',{id=id,instance=1,revision=6})
receive('SlidingGates','state',{id=id,instance=1,revision=5,width=4,type='chainlink4',open=true,moving=false,slavesOpen=true})
assert(data.SlidingGates.gates[id]==nil) -- removed assembly cannot be resurrected by stale state
assert(#square(29,20,0).objects==1) -- no client-created parts
''')
print('PASS client: no world mutation, requests, native animation ordering, stale state, late join, timeout, removal')

# Timed actions are present in shared: client completion sends one explicit
# command; server completion must not execute a second toggle.
for actor_mode in ('client', 'server', 'singleplayer'):
    action_runtime = runtime()
    action_runtime.globals().clientMode = actor_mode == 'client'
    action_runtime.globals().serverMode = actor_mode == 'server'
    action_runtime.execute(r'''
    require 'SG_GateCommon'
    local id='30,20,0'
    leaf=IsoThumpable.new(nil,square(29,20,0))
    leaf.md={sgGate=id,sgRole='leaf',sgInstance=42,sgWidth=2}
    square(29,20,0):AddSpecialObject(leaf)
    player=character(29.5,20.5,0)
    toggles=0; performed=0
    SGGate.toggle=function() toggles=toggles+1 end
    SGGate.isMoving=function() return false end
    ISBaseTimedAction={
      derive=function(_,name)
        local class={}; class.__index=class
        return setmetatable(class,{__index=ISBaseTimedAction})
      end,
      new=function(class,character) return setmetatable({character=character},class) end,
      perform=function() performed=performed+1 end,
    }
    package.preload['TimedActions/ISBaseTimedAction']=function() return true end
    require 'SG_GateToggleAction'
    local action=ISSlidingGateToggle:new(player,id)
    assert(action:isValid())
    assert(action:complete())
    action:perform()
    assert(toggles==(isServer() and 0 or 1) and performed==1)
    leaf.md.sgInstance=43
    assert(not action:isValid()) -- old queued action cannot operate a rebuilt assembly
    ''')
print('PASS shared timed action: one command, no server double toggle, identity after rebuild')

# Two independent client states converge on the same accepted desired state;
# concurrent open requests from both clients cannot produce open-then-close.
authority = runtime()
authority.execute(r'''
serverMode=true
Events.OnClientCommand={Add=function() end}
function sendServerCommand() end
require 'SG_GateServer'
id=SGGate.build(square(30,20,0),'chainlink4')
player=character(29.5,20.5,0)
''')
initial = dict(authority.globals().SGGate.snapshot('30,20,0').items())
peers = []
for _ in range(2):
    peer = runtime()
    peer.execute(r'''
    clientMode=true; now=0; commands={}
    function getTimestampMs() return now end
    function sendClientCommand(...) table.insert(commands,{...}) end
    Events.OnServerCommand={Add=function(fn) receive=fn end}
    Events.LoadGridsquare={Add=function() end}
    require 'SG_Gate'
    player=character(29.5,20.5,0)
    function getPlayer() return player end
    leaf=IsoThumpable.new(nil,square(29,20,0))
    leaf.md={sgGate='30,20,0',sgRole='leaf',sgBase='SG_ChainLink_4_N_Right_G',sgType='chainlink4',sgWidth=4}
    square(29,20,0):AddSpecialObject(leaf)
    ''')
    peer.globals().leaf.md.sgInstance = initial['instance']
    peer.globals().receive('SlidingGates','snapshot',peer.table_from(initial))
    assert peer.globals().SGGate.toggle('30,20,0',peer.globals().player)
    peers.append(peer)

for peer in peers:
    request = dict(peer.globals().commands[1][4].items())
    accepted, _ = authority.globals().SGGate.handleRequest(authority.globals().player, authority.table_from(request))
    assert accepted
moving_state = dict(authority.globals().SGGate.snapshot('30,20,0').items())
assert moving_state['open'] and moving_state['moving']
for peer in peers:
    peer.globals().receive('SlidingGates','state',peer.table_from(moving_state))
    peer.execute('leaf.open=true; sync()')  # native replication plays the accepted Open clip
    request_id = peer.globals().commands[1][4].request
    peer.globals().receive('SlidingGates','result',peer.table_from({'id':'30,20,0','request':request_id,'accepted':True}))
authority.execute('delta=1; for n=1,5 do tick() end')
settled = dict(authority.globals().SGGate.snapshot('30,20,0').items())
for peer in peers:
    peer.globals().receive('SlidingGates','state',peer.table_from(settled))
    assert peer.globals().leaf.IsOpen(peer.globals().leaf)
    assert not peer.globals().SGGate.isMoving('30,20,0')
    assert len(peer.globals().commands) == 1
print('PASS two-client protocol simulation: concurrent open, convergence and no echo/reversal')
