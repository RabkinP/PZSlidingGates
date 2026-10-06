"""Construction ghost regression: native sprite cache, placement, tint and no world objects."""
from pathlib import Path
from lupa import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
lua = LuaRuntime()
lua.globals().package.path = str(ROOT/'mod/SlidingGates/42/media/lua/shared/?.lua').replace('\\', '/') + ';' + lua.globals().package.path
lua.execute('require "SG_GateCommon"')
lua.execute(r'''
Events={OnGameBoot={Add=function(fn) install=fn end},OnGameStart={Add=function() end},OnServerStarted={Add=function() end}}
clientMode=false; serverMode=false
function isClient() return clientMode end
function isServer() return serverMode end
KeybindId={ROTATE_BUILDING='rotate'}
function getCore() return {isKey=function(_,binding,key) return key==binding end} end
calls={}; foreign=0; worldWrites=0; valid=true
function square(x,y,z)
 return {getX=function() return x end,getY=function() return y end,getZ=function() return z end}
end
function getCell() return {getGridSquare=function(_,x,y,z) return square(x,y,z) end} end
SGGate={width=function(kind) return kind=='chainlink4' and 4 or 2 end,
 canBuild=function() return valid end,build=function(sq,kind,bonus,orientation)
 worldWrites=worldWrites+1; built={sq:getX(),sq:getY(),sq:getZ(),kind,bonus,orientation}; return 'gate' end}
sprites={}
function getSprite(name)
 if not sprites[name] then
  sprites[name]={model=true,RenderGhostTileColor=function(_,...) table.insert(calls,{name,...}) end}
 end
 return sprites[name]
end
function face(width,west)
 local start=west and (width==2 and 6 or 12) or (width==2 and 0 or 2)
 return {getzLayers=function() return 1 end,getWidth=function() return west and 1 or width end,getHeight=function() return west and width or 1 end,
 getTileInfo=function(_,x,y) local k=west and y or x; return {getSpriteName=function() return 'sg_gates_preview_01_'..(start+k) end} end}
end
ISBuildIsoEntity={new=function(self,character,info)
 return setmetatable({objectInfo=info,spriteCache={}}, {__index=self}) end,
 rotateKey=function() foreign=foreign+1 end,
 isValid=function() return valid end,setInfo=function() foreign=foreign+1 end,
 cacheSprites=function() foreign=foreign+1 end,
 render=function(self,x,y,z,sq)
  if not self.width then foreign=foreign+1; return end
  local west=self.nSprite==1
  self:cacheSprites(face(self.width,west))
  for xx=0,self.width-1 do
   local start=west and (self.width==2 and 6 or 12) or (self.width==2 and 0 or 2)
   local sprite=self.spriteCache['sg_gates_preview_01_'..(start+xx)]
   assert(sprite.model, 'texture-only cache lost spriteModel')
   local r,g,b=1,1,1
   if not self:isValid(sq) then r,g,b=.65,.2,.2 end
   sprite:RenderGhostTileColor(x+(west and 0 or xx),y+(west and xx or 0),z,r,g,b,.6)
  end
 end,create=function(self) baseCreates=(baseCreates or 0)+1; self:setInfo() end}
function builder(width,nSprite)
 local name=width==2 and 'SlidingGateChainLink2' or 'SlidingGateChainLink4'
 local info={getScript=function() return {getName=function() return name end} end}
 local o=ISBuildIsoEntity:new(nil,info,nSprite)
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
-- R changes the footprint and all static preview cells; unrelated keys do nothing.
for _,width in ipairs({2,4}) do
 local b=builder(width)
 valid=true; b:rotateKey('other'); assert(b.nSprite==2)
 b:rotateKey('rotate'); assert(b.nSprite==1 and not b.north and b.nSpriteCache==-1)
 for _,good in ipairs({true,false}) do
  valid=good; calls={}; b:render(100,200,0,square(100,200,0))
  assert(#calls==width+2+2*width)
  local leaf=calls[1]
  assert(leaf[1]==(width==2 and 'sg_gates_preview_01_6' or 'sg_gates_preview_01_12'))
  assert(leaf[2]==100 and leaf[3]==200)
  assert(calls[width+1][1]=='sg_gates_preview_01_16' and calls[width+1][3]==199)
  assert(calls[width+2][1]=='sg_gates_preview_01_17' and calls[width+2][3]==199+width)
  for k=0,2*width-1 do
   local rail=calls[width+3+k]
   assert(rail[1]=='sg_gates_preview_01_18' and rail[2]==100 and rail[3]==199+k)
  end
  for _,c in ipairs(calls) do assert(c[5]==(good and 1 or .65)) end
  assert(worldWrites==0 and foreign==0)
 end
 b:rotateKey('rotate'); assert(b.nSprite==2 and b.north)
 assert(builder(width,1).nSprite==1) -- native server reconstruction preserves W
end
-- Native server transaction consumes materials in base create exactly once;
-- the replacement assembly is created only after reaching placeholder placement.
valid=true; serverMode=true; Perks={MetalWelding='welding'}
for _,width in ipairs({2,4}) do
 local b=builder(width)
 b.character={getPerkLevel=function() return 3 end}
 b:create(100,200,0,true)
 assert(built[1]==100+width and built[4]==(width==2 and 'chainlink' or 'chainlink4') and built[5]==150)
end
assert(worldWrites==2 and baseCreates==2)
for _,width in ipairs({2,4}) do
 local b=builder(width,1); b.character={getPerkLevel=function() return 3 end}
 valid=true; b:create(100,200,0,false)
 assert(built[1]==100 and built[2]==199 and built[6]=='W' and built[5]==150)
end
assert(worldWrites==4 and baseCreates==4)
clientMode=true; builder(2):create(100,200,0,true)
assert(worldWrites==4 and baseCreates==4)
clientMode=false; valid=false; builder(2):create(100,200,0,true)
valid=true; builder(2):create(100,200,0,false)
assert(worldWrites==4 and baseCreates==4)
serverMode=false; worldWrites=0
local other=setmetatable({objectInfo={getScript=function() return {getName=function() return 'Other' end} end}},
 {__index=ISBuildIsoEntity})
other:render(); other:cacheSprites(nil); other:setInfo()
assert(foreign==3 and worldWrites==0)
''')
print('PASS R rotation, N/W native reconstruction/cache, 2/4 anchors, rails, validity tint, no world writes, foreign builders')
