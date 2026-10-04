"""Lua integration logic with mocked PZ objects (requires lupa).

Does not replace in-game collision/rendering validation.
"""
from pathlib import Path
from lupa import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]
MOCK=r'''
Events={OnContainerUpdate={Add=function(fn) sync=fn end},OnFillWorldObjectContextMenu={Add=function(fn) end}}
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
local function object(_,sq)
 local o={sq=sq,md={},open=false,door=false}
 function o:getModData() return self.md end
 function o:getSquare() return self.sq end
 function o:setSpriteModelName(name) self.model=name end
 function o:setMaxHealth() end
 function o:setHealth() end
 function o:setIsDoor(v) self.door=v end
 function o:setCanPassThrough() end
 function o:setIsThumpable() end
 function o:IsOpen() return self.open end
 function o:isAnimating() return false end
 function o:ToggleDoor() self.open=not self.open; if sync then sync() end end
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
    lua.execute(MOCK)
    lua.execute((ROOT/'mod/SlidingGates/42/media/lua/client/SG_Gate.lua').read_text(encoding='utf-8'))
    lua.globals().width=width
    lua.execute(r'''
local kind=width==2 and 'chainlink' or 'chainlink4'
local id=SGGate.build(square(30,20,0),kind)
assert(id=='30,20,0')
assert(#partsWithRole(id,'slave')==width-1)
assert(#partsWithRole(id,'rail')==2*width)
for k=1,width do assert(blocked(30-k)) end
for k=width+1,2*width do assert(not blocked(30-k)) end
local count=#SGGate.parts(id)
assert(SGGate.build(square(30,20,0),kind)==nil)
assert(#SGGate.parts(id)==count)
SGGate.installDrive(id)
assert(partsWithRole(id,'drive')[1]:getSquare():getX()==30-width)
SGGate.toggle(id)
for k=1,width do assert(not blocked(30-k)) end
for k=width+1,2*width do assert(blocked(30-k)) end
-- Clicking the farthest slave must close every opening cell.
partsWithRole(id,'slave')[1]:ToggleDoor()
for k=1,width do assert(blocked(30-k)) end
for k=width+1,2*width do assert(not blocked(30-k)) end
-- Existing fence in the parking area gets no redundant blocker.
square(30-width-1,20,0).fence=true
SGGate.toggle(id)
assert(#partsWithRole(id,'block')==width-1)
if width==2 then data.SlidingGates.gates[id]=true end -- legacy registry entry
SGGate.remove(id)
for k=0,2*width do assert(#square(30-k,20,0).objects==0) end
assert(data.SlidingGates.gates[id]==nil)
-- No partial construction if a required square is unloaded.
missing='50,20,0'
assert(SGGate.build(square(51,20,0),kind)==nil)
assert(#square(51,20,0).objects==0)
''')
    print(f'PASS {width} cells: build, anchors, slave sync, pocket blockers, removal, legacy, preflight')
