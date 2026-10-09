"""Drive transactions and motor salvage on SP/authority/client (Lua 5.1 mocks)."""
import ast
import json
from pathlib import Path
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
LUA = ROOT/'mod/SlidingGates/42/media/lua'
tree = ast.parse((ROOT/'tests/test_gate_widths.py').read_text())
MOCK = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == 'MOCK' for t in n.targets))


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().package.path = ';'.join(str(LUA/p/'?.lua').replace('\\', '/') for p in ('shared', 'client', 'server')) + ';' + lua.globals().package.path
    lua.execute(MOCK)
    lua.execute(r'''
    setmetatable(Events,{__index=function(t,k)
      local e={Add=function(fn) table.insert(callbacks,fn) end}; t[k]=e; return e
    end})
    callbacks={}; Events.OnGameBoot=nil
    function copyTable(t)
      local c={}; for k,v in pairs(t) do c[k]=type(v)=='table' and copyTable(v) or v end; return c
    end
    function ZombRand() return 99 end
    ItemTag={SCREWDRIVER='screwdriver',WRENCH='wrench'}
    Perks={Electricity='electrical',Mechanics='mechanics'}
    function instanceof(o,kind) return kind=='InventoryContainer' and o.bag or false end
    function list(t) return {size=function() return #t end,get=function(_,i) return t[i+1] end} end
    function container()
      local c={items={}}
      function c:getItems() return list(self.items) end
      function c:Remove(item)
        for i,v in ipairs(self.items) do if v==item then table.remove(self.items,i);item.container=nil;return end end
        error('removing an item twice')
      end
      function c:AddItem(item) item.container=self;table.insert(self.items,item);return item end
      function c:getFirstTagEvalRecurse(tag,predicate)
        for _,item in ipairs(self.items) do
          if item.tag==tag and predicate(item) then return item end
          if item.bag then local found=item.inv:getFirstTagEvalRecurse(tag,predicate);if found then return found end end
        end
      end
      return c
    end
    itemSerial=0
    function instanceItem(kind)
      itemSerial=itemSerial+1
      local i={kind=kind,md={},id=itemSerial}
      function i:getID() return self.id end
      function i:getName() return self.kind end
      function i:syncItemFields() self.syncs=(self.syncs or 0)+1 end
      function i:getFullType() return self.kind end
      function i:getContainer() return self.container end
      function i:getModData() return self.md end
      function i:isBroken() return self.broken or false end
      function i:getInventory() return self.inv end
      return i
    end
    function add(inv,kind,tag)
      local i=instanceItem(kind);i.tag=tag;return inv:AddItem(i)
    end
    removedItems=0;addedItems=0
    function sendRemoveItemFromContainer() removedItems=removedItems+1 end
    function sendAddItemToContainer() addedItems=addedItems+1 end
    function character(sq)
      local p={x=sq.x+.5,y=sq.y+.5,z=sq.z,inv=container(),skills={electrical=1,mechanics=1}}
      function p:getX() return self.x end
      function p:getY() return self.y end
      function p:getCurrentSquare() return square(math.floor(self.x),math.floor(self.y),self.z) end
      function p:getPerkLevel(skill) return self.skills[skill] or 0 end
      function p:isDead() return self.dead or false end
      function p:getInventory() return self.inv end
      function p:removeFromHands() end
      function p:isTimedActionInstant() return false end
      function p:setHaloNote(message) self.message=message end
      return p
    end
    function count(inv,kind)
      local n=0;for _,i in ipairs(inv.items) do
        if i.kind==kind then n=n+1 end
        if i.bag then n=n+count(i.inv,kind) end
      end;return n
    end
    ''')
    return lua


for server in (False, True):
    for orientation in ('N', 'W'):
        for width in (2, 4):
            lua = runtime()
            lua.globals().serverMode = server
            lua.globals().orientation = orientation
            lua.globals().width = width
            lua.execute(r'''
            require 'SG_GateDrive'
            id=SGGate.build(square(30,20,0),width==2 and 'chainlink' or 'chainlink4',0,orientation)
            local leaf=SGGate.findRole(id,'leaf'); identity=leaf.md.sgInstance
            p=character(SGGateDrive.square(id))
            screwdriver=add(p.inv,'Base.Screwdriver','screwdriver');add(p.inv,'Base.Wrench','wrench')
            local bag=add(p.inv,'Base.Bag');bag.bag=true;bag.inv=container()
            local drive=add(bag.inv,'SlidingGates.GateDrive');drive.md.serial='kept';drive.md.nested={v=7}
            add(p.inv,'Base.Screws');add(p.inv,'Base.Screws')
            add(bag.inv,'Base.NutsBolts');add(bag.inv,'Base.NutsBolts')
            local revision=SGGate.snapshot(id).revision
            assert(not SGGateDrive.complete(p,id,identity+1,true))
            p.dead=true;assert(not SGGateDrive.complete(p,id,identity,true));p.dead=false
            p.z=1;assert(not SGGateDrive.complete(p,id,identity,true));p.z=0
            p.x=p.x+10;assert(not SGGateDrive.complete(p,id,identity,true));p.x=p.x-10
            p.skills.electrical=0;assert(not SGGateDrive.complete(p,id,identity,true));p.skills.electrical=1
            screwdriver.broken=true;assert(not SGGateDrive.complete(p,id,identity,true));screwdriver.broken=false
            local bolt=bag.inv.items[#bag.inv.items];bag.inv:Remove(bolt)
            assert(not SGGateDrive.complete(p,id,identity,true));bag.inv:AddItem(bolt)
            assert(removedItems==0 and not SGGate.findRole(id,'drive'))
            assert(SGGateDrive.complete(p,id,identity,true))
            assert(removedItems==5 and count(p.inv,'SlidingGates.GateDrive')==0)
            assert(count(p.inv,'Base.Screws')==0 and count(p.inv,'Base.NutsBolts')==0)
            assert(count(p.inv,'Base.Screwdriver')==1 and count(p.inv,'Base.Wrench')==1)
            local obj=SGGate.findRole(id,'drive')
            assert(obj:getSquare()==SGGateDrive.square(id))
            assert(obj.md.sgDriveData.serial=='kept' and obj.md.sgDriveData.nested.v==7)
            assert(obj.model==(orientation=='W' and 'Base.SG_Drive_W_Static' or 'Base.SG_Drive_Static'))
            assert((obj.sent or 0)==(serverMode and 1 or 0))
            assert(SGGate.snapshot(id).revision==revision+1 and SGGate.snapshot(id).hasDrive)
            assert(not SGGateDrive.complete(p,id,identity,true) and removedItems==5)
            -- A moving gate cannot be edited; no refunded item appears.
            assert(SGGate.toggle(id))
            assert(not SGGateDrive.complete(p,id,identity,false) and addedItems==0)
            leaf.animating=false
            for i=1,300 do if tick then tick() end end
            local settledRevision=SGGate.snapshot(id).revision
            assert(SGGateDrive.complete(p,id,identity,false))
            assert(not SGGate.findRole(id,'drive') and not SGGate.snapshot(id).hasDrive)
            assert(addedItems==1 and p.inv.items[#p.inv.items].md.serial=='kept')
            assert(not SGGateDrive.complete(p,id,identity,false) and addedItems==1)
            assert(SGGate.snapshot(id).revision==settledRevision+1)
            -- Dismantling the entire assembly refunds the mounted drive once;
            -- destructive damage loses it, without refunding its recipe parts.
            for i=1,4 do add(p.inv,'Base.Screws') end
            assert(SGGateDrive.complete(p,id,identity,true))
            local drops={};function leaf.sq:AddWorldInventoryItem(item) table.insert(drops,item) end
            assert(SGGate.destroyGate(id,nil,0,true))
            assert(#drops==1 and drops[1].kind=='SlidingGates.GateDrive' and drops[1].md.serial=='kept')
            assert(not SGGate.destroyGate(id,nil,0,true) and #drops==1)
            -- An old action cannot consume materials after replacement at the same coordinates.
            SGGate.build(square(30,20,0),width==2 and 'chainlink' or 'chainlink4',0,orientation)
            assert(not SGGateDrive.complete(p,id,identity,true) and removedItems==10)
            local replacement=SGGate.findRole(id,'leaf').md.sgInstance
            p.inv:AddItem(drops[1]);for i=1,4 do add(p.inv,'Base.NutsBolts') end
            assert(SGGateDrive.complete(p,id,replacement,true))
            drops={};assert(SGGate.destroyGate(id,nil,0) and #drops==0)
            ''')
    print(f'PASS drive server={server}: 2/4 N/W, bag items, mixed fasteners, validation, replication, refund, duplicate/replacement rejection')

for mode in ('singleplayer', 'server', 'client'):
    lua = runtime()
    lua.globals().serverMode = mode == 'server'
    lua.globals().clientMode = mode == 'client'
    lua.execute(r'''
    drops={};rolls=0;originalCalls=0;roll=0;remove=true
    function ZombRand(n) rolls=rolls+1;return roll end
    ISMoveableSpriteProps={scrapObject=function(self)
      originalCalls=originalCalls+1
      if reentry then reentry=false; self:scrapObject({}) end
      if remove then self.object.index=-1;vanillaLoot=vanillaLoot+1 end
    end}
    vanillaLoot=0
    function appliance(name)
      local o={index=0,md={}}
      function o:getSprite() return {getName=function() return name end} end
      function o:getObjectIndex() return self.index end
      function o:getModData() return self.md end
      function o:getSquare() return {AddWorldInventoryItem=function(_,item) table.insert(drops,item) end} end
      return setmetatable({object=o},{__index=ISMoveableSpriteProps})
    end
    require 'SG_MotorSalvage'
    for _,fn in ipairs(callbacks) do fn() end
    for _,first in ipairs({0,4,12}) do
      for i=first,first+3 do
        local props=appliance('appliances_laundry_01_'..i)
        props:scrapObject({});props:scrapObject({})
      end
    end
    if clientMode then
      assert(#drops==0 and rolls==0 and vanillaLoot==0)
    else
      assert(#drops==12 and rolls==12 and vanillaLoot==12)
      for _,item in ipairs(drops) do assert(item.kind=='SlidingGates.ElectricMotor') end
      -- Failure does not roll; a later successful removal gets one roll.
      local props=appliance('appliances_laundry_01_4');remove=false
      props:scrapObject({});assert(rolls==12)
      remove=true;roll=30;props:scrapObject({});props:scrapObject({})
      assert(rolls==13 and #drops==12)
      roll=29;reentry=true;props=appliance('appliances_laundry_01_0')
      props:scrapObject({});assert(#drops==13 and rolls==14)
      for _,name in ipairs({'appliances_laundry_01_24','appliances_cooking_01_72','appliances_refrigeration_01_0','industry_04_20'}) do
        appliance(name):scrapObject({})
      end
      assert(#drops==13 and rolls==14 and vanillaLoot==18)
    end
    ''')
    print(f'PASS motor {mode}: whitelist, ordinary loot, one roll, reentry, failed removal and 30% boundary')

lua = runtime()
lua.execute(r'''
require 'SG_GateDrive'
id=SGGate.build(square(30,20,0),'chainlink')
identity=SGGate.findRole(id,'leaf').md.sgInstance
p=character(SGGateDrive.square(id))
add(p.inv,'Base.Screwdriver','screwdriver');add(p.inv,'Base.Wrench','wrench')
add(p.inv,'SlidingGates.GateDrive');for i=1,4 do add(p.inv,'Base.Screws') end
ISBaseTimedAction={
 derive=function(_,name) local c={Type=name};c.__index=c;return c end,
 new=function(class,character) return setmetatable({character=character},class) end,
 perform=function() performed=(performed or 0)+1 end,
 stop=function() stopped=(stopped or 0)+1 end}
package.preload['TimedActions/ISBaseTimedAction']=function() return true end
require 'SG_GateDriveAction'
local action=ISSlidingGateDrive:new(p,id,identity,true)
assert(action.gateId==id and action.instance==identity and action.installing and action.maxTime==180)
assert(action:isValid())
action:stop();assert(removedItems==0 and not SGGate.findRole(id,'drive'))
clientMode=true;action:perform();assert(not action:complete())
assert(performed==1 and removedItems==0 and not SGGate.findRole(id,'drive'))
clientMode=false;assert(action:complete());assert(removedItems==5)
assert(not action:complete() and removedItems==5)
-- Menu deduplicates carriers and queues the captured identity at the guide post.
function getSpecificPlayer() return p end
function getText(key) return key end
function getItemDisplayName(kind) return kind end
ISToolTip={new=function() return {initialise=function() end} end}
package.preload['ISUI/ISToolTip']=function() return true end
ISTimedActionQueue={add=function(a) queued=a end}
package.preload['TimedActions/ISTimedActionQueue']=function() return true end
luautils={walkAdj=function(character,sq) walked=sq;return true end}
require 'SG_GateDriveMenu'
local options={};local context={addOption=function(_,label,target,callback,...)
 local o={label=label,target=target,callback=callback,args={...}};table.insert(options,o);return o end}
local objects=SGGate.parts(id)
gateMenu(0,context,objects,false)
assert(#options==2 and options[1].label=='ContextMenu_SG_RemoveDrive' and not options[1].notAvailable)
assert(options[2].label=='ContextMenu_SG_PowerOpen' and options[2].notAvailable)
local option=options[1];option.callback(option.target,unpack(option.args))
assert(walked==SGGateDrive.square(id) and queued.instance==identity and queued.installing==false)
assert(queued.maxTime==120 and queued:complete())
options={};gateMenu(0,context,objects,false)
assert(#options==1 and options[1].label=='ContextMenu_SG_InstallDrive' and options[1].notAvailable)
local description=options[1].toolTip.description
assert(description:find('<GHC> IGUI_perks_Electricity 1/1',1,true))
assert(description:find('<GHC> Base.Screwdriver 1/1',1,true))
assert(description:find('<GHC> SlidingGates.GateDrive 1/1',1,true))
assert(description:find('<BHC> Base.Screws / Base.NutsBolts 0/4',1,true))
-- Show all missing requirements together, even if validation stops at skills.
p.skills.electrical=0
for _,item in ipairs(p.inv.items) do if item.tag=='wrench' then item.broken=true end end
local bag=add(p.inv,'Base.Bag');bag.bag=true;bag.inv=container()
add(bag.inv,'Base.Screws');add(bag.inv,'Base.NutsBolts')
options={};gateMenu(0,context,objects,false);description=options[1].toolTip.description
assert(description:find('<BHC> IGUI_perks_Electricity 0/1',1,true))
assert(description:find('<GHC> IGUI_perks_Mechanics 1/1',1,true))
assert(description:find('<BHC> Base.Wrench 0/1',1,true))
assert(description:find('<BHC> Base.Screws / Base.NutsBolts 2/4',1,true))
p.skills.electrical=2
add(bag.inv,'Base.Wrench','wrench');add(bag.inv,'Base.NutsBolts');add(bag.inv,'Base.Screws')
options={};gateMenu(0,context,objects,false);description=options[1].toolTip.description
assert(not options[1].notAvailable)
assert(description:find('<GHC> Base.Wrench 1/1',1,true))
assert(description:find('<GHC> Base.Screws / Base.NutsBolts 4/4',1,true))
assert(not description:find('<BHC>',1,true))
assert(SGGateDrive.complete(p,id,identity,true))
options={};gateMenu(0,context,SGGate.parts(id),false)
description=options[1].toolTip.description
assert(options[1].label=='ContextMenu_SG_RemoveDrive' and not options[1].notAvailable)
assert(not description:find('Base.Screws',1,true) and not description:find('SlidingGates.GateDrive',1,true))
''')
print('PASS native-action contract: captured identity, cancellation, no client mutation/double completion; menu, walk and unavailable materials')

# All Lua files compile as Lua 5.1; all shipped translations parse as JSON.
lua = LuaRuntime()
compile_lua = lua.eval('function(source) local fn,err=loadstring(source);assert(fn,err) end')
for path in LUA.rglob('*.lua'):
    compile_lua(path.read_text(encoding='utf-8'))
for path in LUA.rglob('*.json'):
    json.loads(path.read_text(encoding='utf-8'))
print('PASS Lua 5.1 syntax and translation JSON')
