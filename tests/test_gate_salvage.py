"""Recipe/salvage conservation and dismantling success/re-entry regression (requires lupa)."""
import ast
import re
from pathlib import Path
from lupa import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
tree = ast.parse((ROOT/'tests/test_gate_widths.py').read_text())
mock = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
            and any(isinstance(t,ast.Name) and t.id=='MOCK' for t in n.targets))
for width in (2,4):
    lua=LuaRuntime()
    lua.globals().package.path = str(ROOT/'mod/SlidingGates/42/media/lua/shared/?.lua').replace('\\', '/') + ';' + lua.globals().package.path
    lua.execute(mock)
    lua.execute(r'''
    setmetatable(Events,{__index=function(t,key)
      local event={Add=function() end,Remove=function() end}; t[key]=event; return event
    end})
    Events.OnGameBoot={Add=function(fn) installScrap=fn end}
    drops={}; function ZombRand() return 0 end
    function instanceItem(kind)
      return {kind=kind,getUseDelta=function() return .1 end,setUsedDelta=function(self,v) self.delta=v end}
    end
    function withDrops(sq)
      function sq:AddWorldInventoryItem(item)
        table.insert(drops,type(item)=='string' and {kind=item,delta=1} or item)
      end
    end
    ''')
    lua.execute((ROOT/'mod/SlidingGates/42/media/lua/client/SG_Gate.lua').read_text())
    lua.globals().width=width
    lua.execute(r'''
    kind=width==2 and 'chainlink' or 'chainlink4'
    id=SGGate.build(square(30,20,0),kind)
    withDrops(square(29,20,0))
    assert(SGGate.destroyGate(id,nil,100))
    local counts={}; local uses=0
    for _,item in ipairs(drops) do
      counts[item.kind]=(counts[item.kind] or 0)+1
      if item.kind=='Base.Wire' then uses=uses+item.delta/.1 end
    end
    assert(counts['Base.Wire']==1 and math.abs(uses-(width==2 and 4 or 8))<.00001)
    assert(counts['Base.MetalPipe']==(width==2 and 6 or 10))
    assert(counts['Base.SmallSheetMetal']==(width==2 and 1 or 2))
    local before=#drops
    assert(not SGGate.destroyGate(id,nil,100) and #drops==before)
    -- Zero recovery produces no full or empty coil.
    id=SGGate.build(square(30,20,0),kind); drops={}
    assert(SGGate.destroyGate(id,nil,0) and #drops==0)
    -- Vanilla scrapping must not add carrier-tile loot; failure must leave the gate intact.
    removed=false; foreign=0; vanillaLoot=0
    package.preload['ISUI/ISDisassembleMenu']=function() return true end
    ISDisassembleMenu={createMenu=function(objects) menuObjects=objects end}
    ISMoveableSpriteProps={
      new=function() return setmetatable({canScrap=false,material='Undefined'}, {__index=ISMoveableSpriteProps}) end,
      fromObject=function(obj) return {object=obj,foreign=true} end,
      canScrapObject=function(self)
        return {craftValid=self.canScrap and self.material=='MetalPipe',canScrap=self.canScrap}
      end,
      getScrapItemsList=function() foreign=foreign+1; return {usable={'Base.Wire'},unusable={}} end,
      scrapObject=function(self)
        local items=self:getScrapItemsList()
        vanillaLoot=vanillaLoot+#items.usable
        if removed then self.object:getSquare():transmitRemoveItemFromSquare(self.object) end
      end}
    ''')
    lua.execute((ROOT/'mod/SlidingGates/42/media/lua/client/SG_GateDismantle.lua').read_text())
    lua.execute(r'''
    installScrap()
    id=SGGate.build(square(30,20,0),kind)
    local obj=partsWithRole(id,'leaf')[1]
    function obj:getObjectIndex()
      local list=self:getSquare().objects
      for i,o in ipairs(list) do if o==self then return i-1 end end
      return -1
    end
    function obj:getSprite() return {} end
    function obj:getName() return 'Sliding gate' end
    local allParts=SGGate.parts(id)
    local foreignObject={getModData=function() return {} end}
    allParts[#allParts+1]=obj
    allParts[#allParts+1]=foreignObject
    ISDisassembleMenu.createMenu(allParts)
    assert(#menuObjects==2 and menuObjects[1]==obj and menuObjects[2]==foreignObject)
    local post=assert(partsWithRole(id,'post')[1])
    ISDisassembleMenu.createMenu({post})
    assert(#menuObjects==1 and menuObjects[1]==obj)
    local props=ISMoveableSpriteProps.fromObject(obj)
    assert(props:canScrapObject().craftValid and props.canScrap and props.isFromObject)
    assert(props.scrapUseTool and props.scrapUseSkill and props.scrapToolUses==5)
    assert(props.material2==nil and props.material3==nil and props.isMultiSprite==false)
    assert(ISMoveableSpriteProps.fromObject({getModData=function() return {} end}).foreign)
    props:scrapObject(nil)
    assert(data.SlidingGates.gates[id] and #drops==0 and vanillaLoot==0 and props.sgGateScrap==nil)
    removed=true; props:scrapObject(nil)
    assert(data.SlidingGates.gates[id]==nil and vanillaLoot==0 and #drops>0)
    local count=#drops; props:scrapObject(nil); assert(#drops==count)
    local other=setmetatable({}, {__index=ISMoveableSpriteProps})
    other:getScrapItemsList(); assert(foreign==1)
    ''')
    print(f'PASS {width}: limited wire uses, recipe amounts, no duplicate drops, zero yield, successful/failed dismantle')

# Preserve correspondence between consumed recipe resources and the maximum salvage budget.
recipe=(ROOT/'mod/SlidingGates/42/media/scripts/entity_sliding_gates.txt').read_text()
for entity,pipes,wire,scrap,sheets in [('SlidingGateChainLink2',6,4,2,1),('SlidingGateChainLink4',10,8,3,2)]:
    block=recipe.split('entity '+entity+'\n',1)[1].split('inputs',1)[1].split('}',1)[0]
    for name,count in [('MetalPipe',pipes),('Wire',wire),('ScrapMetal',scrap),('SmallSheetMetal',sheets)]:
        assert re.search(r'item '+str(count)+r' \[Base\.'+name+r'[;\]]',block),(entity,name)

# The native entity preview and the actual gate must agree about base health.
for kind, definition in lua.globals().SGGateTypes.items():
    block = recipe.split('entity ' + definition.entity + '\n', 1)[1].split('component CraftRecipe', 1)[0]
    health = int(re.search(r'skillBaseHealth\s*=\s*(\d+)', block).group(1))
    assert health == definition.baseHealth, (kind, health, definition.baseHealth)
print('PASS shared gate definitions agree with entity base health')
