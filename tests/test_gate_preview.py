"""Construction ghost regression: native sprite cache, placement, tint and no world objects."""
from pathlib import Path
from lupa import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
lua = LuaRuntime()
lua.globals().package.path = str(ROOT/'mod/SlidingGates/42/media/lua/shared/?.lua').replace('\\', '/') + ';' + lua.globals().package.path
lua.execute(r'''
Events={OnGameBoot={Add=function(fn) install=fn end},OnGameStart={Add=function() end}}
calls={}; foreign=0; worldWrites=0; valid=true
function square(x,y,z)
 return {getX=function() return x end,getY=function() return y end,getZ=function() return z end}
end
function getCell() return {getGridSquare=function(_,x,y,z) return square(x,y,z) end} end
SGGate={width=function(kind) return kind=='chainlink4' and 4 or 2 end,
 canBuild=function() return valid end,build=function() worldWrites=worldWrites+1 end}
sprites={}
function getSprite(name)
 if not sprites[name] then
  sprites[name]={model=true,RenderGhostTileColor=function(_,...) table.insert(calls,{name,...}) end}
 end
 return sprites[name]
end
function face(width)
 local start=width==2 and 0 or 2
 return {getzLayers=function() return 1 end,getWidth=function() return width end,getHeight=function() return 1 end,
 getTileInfo=function(_,x) return {getSpriteName=function() return 'sg_gates_preview_01_'..(start+x) end} end}
end
ISBuildIsoEntity={new=function(self,character,info)
 return setmetatable({objectInfo=info,spriteCache={}}, {__index=self}) end,
 isValid=function() return valid end,setInfo=function() foreign=foreign+1 end,
 cacheSprites=function() foreign=foreign+1 end,
 render=function(self,x,y,z,sq)
  if not self.width then foreign=foreign+1; return end
  self:cacheSprites(face(self.width))
  for xx=0,self.width-1 do
   local start=self.width==2 and 0 or 2
   local sprite=self.spriteCache['sg_gates_preview_01_'..(start+xx)]
   assert(sprite.model, 'texture-only cache lost spriteModel')
   local r,g,b=1,1,1
   if not self:isValid(sq) then r,g,b=.65,.2,.2 end
   sprite:RenderGhostTileColor(x+xx,y,z,r,g,b,.6)
  end
 end,create=function(self) self:setInfo() end}
function builder(width)
 local name=width==2 and 'SlidingGateChainLink2' or 'SlidingGateChainLink4'
 local info={getScript=function() return {getName=function() return name end} end}
 local o=ISBuildIsoEntity:new(nil,info)
 o.width=width; return o
end
''')
lua.execute((ROOT/'mod/SlidingGates/42/media/lua/client/SG_GateBuild.lua').read_text(encoding='utf-8'))
lua.execute(r'''
install()
for _,width in ipairs({2,4}) do
 local b=builder(width)
 assert(b.nSprite==2 and b.north)
 for _,good in ipairs({true,false}) do
  valid=good; calls={}
  b:render(100,200,0,square(100,200,0))
  assert(#calls==width+2+2*width)
  local leaf=calls[width]
  assert(leaf[1]==(width==2 and 'sg_gates_preview_01_1' or 'sg_gates_preview_01_5'))
  assert(leaf[2]==100+width-1)
  assert(calls[width+1][1]=='sg_gates_preview_01_8' and calls[width+1][2]==100+width)
  assert(calls[width+2][1]=='sg_gates_preview_01_9' and calls[width+2][2]==100)
  for k=0,2*width-1 do
   local rail=calls[width+3+k]
   assert(rail[1]=='sg_gates_preview_01_10' and rail[2]==100+width-k)
  end
  for _,c in ipairs(calls) do
   assert(c[3]==200 and c[4]==0)
   assert(c[5]==(good and 1 or .65) and c[6]==(good and 1 or .2))
  end
  -- Re-render at the same cell after validity changed: tint must not be cached.
  assert(worldWrites==0 and foreign==0)
 end
 calls={}; b:render(100,200,0,nil)
 assert(#calls==width) -- only base cursor; no additional assembly without a square
 b:setInfo(); assert(b.sgPlaceholdersReached and worldWrites==0)
end
local other=setmetatable({objectInfo={getScript=function() return {getName=function() return 'Other' end} end}},
 {__index=ISBuildIsoEntity})
other:render(); other:cacheSprites(nil); other:setInfo()
assert(foreign==3 and worldWrites==0)
''')
print('PASS native cache, 2/4 anchors, rails, validity tint, no world writes, foreign builders')
