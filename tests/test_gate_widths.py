"""Lua integration logic with mocked PZ objects (requires lupa).

Does not replace in-game collision/rendering validation.
"""
from pathlib import Path
from lupa import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]
MOCK=r'''
Events={OnContainerUpdate={Add=function(fn) sync=fn end},
 OnFillWorldObjectContextMenu={Add=function(fn) gateMenu=fn end},
 OnGameStart={Add=function(fn) gameStart=fn end},
 OnServerStarted={Add=function(fn) serverStart=fn end},
 LoadGridsquare={Add=function(fn) gridLoaded=fn end},
 OnDestroyIsoThumpable={Add=function(fn) destroyed=fn end},
 OnTick={Add=function(fn) tick=fn end,Remove=function() tick=nil end}}
debug=false
clientMode=false; serverMode=false
function isClient() return clientMode end
function isServer() return serverMode end
function isDebugEnabled() return debug end
gameSpeed=1; delta=1/48
UIManager={getSpeedControls=function() return {getCurrentGameSpeed=function() return gameSpeed end} end}
function getGameTime() return {getTimeDelta=function() return delta end} end
data={}; ModData={getOrCreate=function(name) data[name]=data[name] or {}; return data[name] end}
function getPlayer() return nil end
local squares={}
missing=nil
function square(x,y,z)
 local key=x..','..y..','..z
 if missing==key then return nil end
 if squares[key] then return squares[key] end
 local s={x=x,y=y,z=z,objects={},fence=false}
 function s:getX() return self.x end
 function s:getY() return self.y end
 function s:getZ() return self.z end
 function s:getObjects() return {size=function() return #self.objects end,get=function(_,i) return self.objects[i+1] end} end
 function s:AddSpecialObject(o) table.insert(self.objects,o) end
 function s:AddTileObject(o) table.insert(self.objects,o) end
 function s:RecalcAllWithNeighbours() end
 function s:isVehicleIntersecting() return self.vehicle or false end
 function s:transmitRemoveItemFromSquare(o)
   for i,v in ipairs(self.objects) do if v==o then table.remove(self.objects,i); break end end
   if sync then sync() end
 end
 function s:isBlockedTo(north)
   if self.fence then return true end
   for _,o in ipairs(self.objects) do if o.door and not o.open then return true end end
   return false
 end
 squares[key]=s; return s
end
local cell={getGridSquare=function(_,x,y,z) return square(x,y,z) end}
function getCell() return cell end
function getWorld() return {getCell=function() return cell end} end
local function object(_,sq,sprite,openSprite,north)
 local o={sq=sq,md={},open=false,door=false,sprite=sprite,north=north}
 function o:getModData() return self.md end
 function o:getSquare() return self.sq end
 function o:setSpriteModelName(name) self.model=name end
 function o:setMaxHealth(v) self.maxHealth=v end
 function o:setHealth(v) self.health=v end
 function o:setIsDoor(v) self.door=v end
 function o:setCanPassThrough() end
 function o:setIsThumpable() end
 function o:IsOpen() return self.open end
 function o:isAnimating() return self.animating or false end
 function o:setAnimating(value) self.animating=value end
 function o:transmitCompleteItemToClients() self.sent=(self.sent or 0)+1 end
 function o:transmitModData() self.mdSent=(self.mdSent or 0)+1 end
 function o:sync() self.synced=(self.synced or 0)+1 end
 function o:isObstructed() return self.obstructed or false end
 function o:ToggleDoorSilent() self.open=not self.open end
 function o:ToggleDoor()
   if self.obstructed or self.refuseNext or self.locked then
     self.refuseNext=nil
     return -- native door refusal changes neither state nor animation
   end
   self.open=not self.open
   if self.md.sgRole=='leaf' then self.animating=true end
   if sync then sync() end
 end
 return o
end
IsoThumpable={new=object}; IsoObject={new=object}
function partsWithRole(id,role)
 local res={}
 for _,o in ipairs(SGGate.parts(id)) do if o.md.sgRole==role then res[#res+1]=o end end
 return res
end
function blocked(x) return square(x,20,0):isBlockedTo(square(x,19,0)) end
'''

for width in (2,4):
    lua=LuaRuntime()
    lua.globals().package.path = str(ROOT/'mod/SlidingGates/42/media/lua/shared/?.lua').replace('\\', '/') + ';' + lua.globals().package.path
    lua.execute(MOCK)
    lua.execute((ROOT/'mod/SlidingGates/42/media/lua/client/SG_Gate.lua').read_text(encoding='utf-8'))
    lua.globals().width=width
    lua.execute(r'''
local kind=width==2 and 'chainlink' or 'chainlink4'
local id=SGGate.build(square(30,20,0),kind,100)
assert(id=='30,20,0')
local leaf=partsWithRole(id,'leaf')[1]
assert(leaf.health==(width==2 and 400 or 550))
assert(#partsWithRole(id,'slave')==width)
assert(#partsWithRole(id,'rail')==2*width)
assert(#partsWithRole(id,'collider')==width)
for k=1,width do assert(blocked(30-k)) end
for k=width+1,2*width do assert(not blocked(30-k)) end
local count=#SGGate.parts(id)
assert(SGGate.build(square(30,20,0),kind)==nil)
assert(#SGGate.parts(id)==count)
SGGate.installDrive(id)
assert(partsWithRole(id,'drive')[1]:getSquare():getX()==30-width)
-- A car pressed against the closed leaf can obstruct it while the pocket is empty.
local farSlave=partsWithRole(id,'slave')[width]
leaf.obstructed=true
assert(SGGate.toggle(id)==false)
farSlave:ToggleDoor() -- E key at another opening cell requests the same obstructed gate
assert(not leaf:IsOpen() and not farSlave:IsOpen())
assert(not SGGate.isMoving(id) and tick==nil)
assert(not leaf.md.sgOpen and data.SlidingGates.gates[id].moving==nil)
assert(leaf.model=='Base.'..SGGateTypes[kind].leafModel..'_Closed')
for k=1,width do assert(blocked(30-k)) end
leaf.obstructed=false
-- The native toggle can still refuse AFTER preflight (lock, or changed obstruction).
for _,reason in ipairs({'refuseNext','locked'}) do
 leaf[reason]=true
 farSlave:ToggleDoor()
 assert(not leaf:IsOpen() and not farSlave:IsOpen() and not SGGate.isMoving(id))
 assert(not leaf.md.sgOpen and data.SlidingGates.gates[id].moving==nil and tick==nil)
 for k=1,width do assert(blocked(30-k)) end
 leaf[reason]=nil
end
-- Motion keeps collision on occupied cells and transfers it at each cell boundary.
assert(SGGate.toggle(id))
assert(SGGate.isMoving(id))
assert(SGGate.toggle(id)==nil) -- concurrent request cannot restart the motion
for k=1,width do assert(blocked(30-k)) end
assert(blocked(30-width-1)) -- first pocket cell blocks before the leaf arrives
gameSpeed=0; tick()
for k=1,width do assert(blocked(30-k)) end
gameSpeed=1; delta=1 -- advances one cell: delta * speed = 1.5 clip seconds
for p=1,width do
 tick()
 for k=1,width do assert(blocked(30-k)==(k>p)) end
 for j=1,width do assert(blocked(30-width-j)==(j<=math.min(width,p+1))) end
end
leaf.animating=false; tick()
assert(not SGGate.isMoving(id) and tick==nil)
for k=1,width do assert(not blocked(30-k)) end
for k=width+1,2*width do assert(blocked(30-k)) end
-- E on the retracted leaf operates its pocket proxy, including a refused close.
local pocket=partsWithRole(id,'block')[width]
square(29,20,0).vehicle=true
pocket:ToggleDoor()
assert(leaf:IsOpen() and not pocket:IsOpen() and not SGGate.isMoving(id))
square(29,20,0).vehicle=false
pocket:ToggleDoor()
assert(not leaf:IsOpen() and not pocket:IsOpen() and SGGate.isMoving(id))
-- A second pocket input during motion cannot reverse or restart the gate.
pocket:ToggleDoor()
assert(not leaf:IsOpen() and data.SlidingGates.gates[id].moving==false)
for p=1,width do tick() end
leaf.animating=false; tick()
for k=1,width do assert(blocked(30-k)) end
assert(SGGate.toggle(id))
for p=1,width do tick() end
leaf.animating=false; tick()
-- Clicking the farthest slave must close every opening cell.
partsWithRole(id,'slave')[1]:ToggleDoor()
for p=1,width do tick() end
leaf.animating=false; tick()
for k=1,width do assert(blocked(30-k)) end
for k=width+1,2*width do assert(not blocked(30-k)) end
-- Existing fence keeps an opaque damage proxy but needs no extra vehicle collider.
square(30-width-1,20,0).fence=true
assert(SGGate.toggle(id))
for p=1,width do tick() end
leaf.animating=false; tick()
assert(#partsWithRole(id,'block')==width)
assert(#partsWithRole(id,'collider')==width-1)
-- Vehicle and unloaded destination cells refuse the move without changing its state.
square(29,20,0).vehicle=true
assert(SGGate.toggle(id)==false and leaf:IsOpen())
-- Java/E-key may have toggled a slave already: rejection must undo it immediately.
local slave=partsWithRole(id,'slave')[width]
slave:ToggleDoor()
assert(slave:IsOpen() and leaf:IsOpen() and not SGGate.isMoving(id))
square(29,20,0).vehicle=false
missing='29,19,0'
assert(SGGate.toggle(id)==false and leaf:IsOpen())
missing=nil
-- Recovery must not clear the persistent marker while another chunk is absent.
data.SlidingGates.gates[id].moving=true
leaf.md.sgMoving=true
missing=(30-2*width)..',20,0'
gameStart()
assert(data.SlidingGates.gates[id].moving==true and SGGate.isMoving(id))
missing=nil
for n=1,60 do if tick then tick() end end
assert(data.SlidingGates.gates[id].moving==nil and not SGGate.isMoving(id) and tick==nil)
assert(SGGate.finalize(id)) -- repeated recovery must not duplicate parts
assert(#partsWithRole(id,'block')==width)
-- Losing the leaf mid-animation must retain recovery work until the chunk returns.
assert(SGGate.toggle(id))
missing='29,20,0'; tick()
assert(SGGate.isMoving(id) and data.SlidingGates.gates[id].moving==false)
missing=nil; leaf.animating=false
for n=1,60 do if tick then tick() end end
assert(not SGGate.isMoving(id) and not leaf:IsOpen() and tick==nil)
for k=1,width do assert(blocked(30-k)) end
if width==2 then data.SlidingGates.gates[id]=true end -- legacy registry entry
SGGate.remove(id)
for k=0,2*width do assert(#square(30-k,20,0).objects==0) end
assert(data.SlidingGates.gates[id]==nil)
-- No partial construction if a required square is unloaded.
missing='50,20,0'
assert(SGGate.build(square(51,20,0),kind)==nil)
assert(#square(51,20,0).objects==0)
''')
    print(f'PASS {width} cells: health, motion collision, pause, concurrency, fences, vehicles, chunk recovery, removal, legacy, preflight')

# Debug tooling must not create ordinary player menu entries.
lua.execute("gateMenu(0,nil,{},false)")
