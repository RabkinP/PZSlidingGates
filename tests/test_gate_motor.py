"""Motor audio/noise lifecycle and client replication; not a listening/gameplay test."""
import ast
from array import array
from pathlib import Path
import wave

ROOT = Path(__file__).resolve().parents[1]
tree = ast.parse((ROOT/'tests/test_gate_drive.py').read_text())
prefix = tree.body[:next(i for i, node in enumerate(tree.body) if isinstance(node, ast.For))]
ns = {'__file__': str(ROOT/'tests/test_gate_drive.py')}
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
id=SGGate.build(square(30,20,0),width==2 and 'chainlink' or 'chainlink4',0,orientation)
drive=SGGate.installDrive(id,{});drive:getSquare().electricity=true
leaf=SGGate.findRole(id,'leaf');instance=leaf.md.sgInstance;p=character(drive:getSquare())
function settle()
 leaf.animating=false
 for i=1,400 do if tick then tick() end end
end
-- A mounted drive does not make manual opening audible.
assert(SGGate.toggle(id,p));assert(not SGGate.snapshot(id).motor)
tick();assert(#soundEmitters==0 and #worldSounds==0);settle()
assert(SGGatePower.complete(p,id,instance,false))
local state=SGGate.snapshot(id)
assert(state.motor and state.moving and state.motionRemaining==width*1.5)
assert(#worldSounds==1 and worldSounds[1].source==drive)
assert(worldSounds[1].radius==20 and worldSounds[1].volume==15)
tick();local audioCount=serverMode and 0 or 1
assert(#soundEmitters==audioCount)
if not serverMode then
 assert(soundEmitters[1].name=='SG_GateMotorRunning' and soundEmitters[1].parent==drive)
 -- Pause silences the loop and resume gets a new world-owned emitter.
 gameSpeed=0;tick();assert(soundEmitters[1].stops==1)
 assert(#worldSounds==1);gameSpeed=1;tick();assert(#soundEmitters==2)
 audioCount=2
end
-- Repeated accepted state refresh never adds a second simultaneous loop.
SGGateMotor.sync(SGGate.snapshot(id));tick();assert(#soundEmitters==audioCount)
assert(not SGGatePower.complete(p,id,instance,false))
settle();assert(not SGGate.snapshot(id).motor)
for _,e in ipairs(soundEmitters) do assert(e.stops==1) end
local sounds=#worldSounds;SGGateMotor.update();assert(#worldSounds==sounds)
-- Blocked and unpowered requests produce no noise or playback.
SGGate.isBlocked=function() return true end
assert(not SGGatePower.complete(p,id,instance,true));assert(#worldSounds==sounds)
SGGate.isBlocked=function() return false end
drive:getSquare().electricity=false
assert(not SGGatePower.complete(p,id,instance,true));assert(#worldSounds==sounds)
drive:getSquare().electricity=true
assert(SGGatePower.complete(p,id,instance,true));tick()
-- Destroying a moving assembly releases audio immediately, before the next tick.
assert(SGGate.destroyGate(id,nil,0,false))
for _,e in ipairs(soundEmitters) do assert(e.stops==1) end
local sounds=#worldSounds;SGGateMotor.update();assert(#worldSounds==sounds)
''')
print('PASS motor SP/authority: manual silence, powered open/close, pause, repeats, finish, rejection and destruction')

lua = ns['runtime']()
lua.execute(r'''
clientMode=true;now=0;commands={}
function getTimestampMs() return now end
function sendClientCommand(...) table.insert(commands,{...}) end
Events.OnServerCommand={Add=function(fn) receive=fn end}
require 'SG_GateNetwork'
id='30,20,0'
leaf=IsoThumpable.new(nil,square(29,20,0))
leaf.md={sgGate=id,sgRole='leaf',sgType='chainlink',sgWidth=2,sgInstance=1,sgRevision=1}
leaf:getSquare():AddSpecialObject(leaf)
drive=IsoObject.new(nil,square(30,20,0));drive.md={sgGate=id,sgRole='drive',sgInstance=1}
drive:getSquare():AddTileObject(drive)
function state(revision,moving,motor,remaining)
 return {id=id,instance=1,revision=revision,width=2,type='chainlink',open=true,
 moving=moving,motor=motor,motionRemaining=remaining,slavesOpen=false}
end
receive('SlidingGates','state',state(2,true,true,3));tick()
assert(#soundEmitters==1 and #worldSounds==0)
receive('SlidingGates','result',{id=id,state=state(2,true,true,3),accepted=true});tick()
assert(#soundEmitters==1)
-- A stale motor state cannot restart playback after the authority finished.
receive('SlidingGates','state',state(3,false,false,0));assert(soundEmitters[1].stops==1)
receive('SlidingGates','state',state(2,true,true,3));tick();assert(#soundEmitters==1)
-- Late join to a powered move uses only its remaining duration, then times out
-- even if the final network packet is lost.
receive('SlidingGates','snapshot',state(4,true,true,0.1));tick();assert(#soundEmitters==2)
for i=1,10 do tick() end
assert(soundEmitters[2].stops==1 and #worldSounds==0)
receive('SlidingGates','state',state(5,true,true,3));tick();assert(#soundEmitters==3)
missing='30,20,0';tick();assert(soundEmitters[3].stops==1);missing=nil
receive('SlidingGates','state',state(6,true,true,3));tick();assert(#soundEmitters==4)
receive('SlidingGates','removed',{id=id,instance=1,revision=7})
assert(soundEmitters[4].stops==1 and #worldSounds==0)
''')
print('PASS motor client: local loop, no zombie noise, deduplication, stale packets, late join, timeout, unload and removal')

sound = ROOT/'mod/SlidingGates/42/media/sound/SG_GateMotorRunning.wav'
with wave.open(str(sound), 'rb') as wav:
    assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 2, 48000)
    assert wav.getnframes() == 4*48000
    samples = array('h')
    samples.frombytes(wav.readframes(wav.getnframes()))
    steps = sorted(abs(samples[i]-samples[i-1]) for i in range(1, len(samples)))
    assert abs(samples[0]-samples[-1]) <= steps[round(len(steps)*0.99)]
    # Every 20ms window has audible content, including the circular crossfade.
    assert all(max(abs(v) for v in samples[i:i+960]) > 1000 for i in range(0,len(samples),960))
print('PASS synthetic motor loop: 4s mono PCM16/48kHz, continuous seam, no silent windows')
