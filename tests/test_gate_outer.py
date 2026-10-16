"""Outer-side gates: same edge/cells/collision, assembly mirrored across the fence line.

Checks (1) every outer spriteModel against an independent rotation/reflection of the inner
pose, (2) every model name the Lua requests is registered, (3) gameplay parts, metadata and
the far-row vehicle check, (4) the eight-state construction cursor. Mocks do not establish
final in-game appearance.
"""
import ast
import re
from pathlib import Path
from lupa import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT/'mod/SlidingGates/42/media'
LUA = MEDIA/'lua'
FENCE = -0.38


def blocks(text):
    return {name: dict((k, v.strip()) for k, v in re.findall(r'(\w+)\s*=\s*([^,\n]+),', body))
            for name, body in re.findall(r'\bspriteModel\s+(\w+)\s*\{([^}]+)\}', text)}


scripts = {}
for path in MEDIA.glob('scripts/SG_models*.txt'):
    scripts.update(blocks(path.read_text(encoding='utf-8')))
models = set()
for path in MEDIA.glob('scripts/SG_models*.txt'):
    models.update(re.findall(r'^\s*model\s+(\w+)\s*$', path.read_text(encoding='utf-8'), re.M))


def turn(point, degrees):
    """Native rotate.y: each +90 maps the ground plane (x,z) -> (z,-x)."""
    x, z = point
    for _ in range(int(degrees) // 90 % 4):
        x, z = z, -x
    return x, z


def world(fields, point):
    tx, _, tz = map(float, fields['translate'].split())
    x, z = turn(point, float(fields['rotate'].split()[1]))
    return x + tx, z + tz


# (1) Each outer pose is the inner pose reflected through the fence plane.
samples = [(0.0, 0.0), (1.0, -0.2), (-0.21, 0.156), (2.0, -0.04), (0.3, 0.5)]
outer = {name: fields for name, fields in scripts.items() if '_Out_' in name or name.endswith('_Out_Static')}
assert len(outer) == 608, len(outer)
for name, fields in outer.items():
    inner_name = name.replace('_Out', '', 1)
    inner = scripts[inner_name]
    model = fields['modelScript'].split('.', 1)[1]
    assert model in models, model
    assert inner['modelScript'].split('.', 1)[1] != model  # the mirrored mesh, never a negative scale
    assert float(fields['scale']) > 0
    for key in ('scale', 'animation', 'animationTime'):
        assert fields.get(key) == inner.get(key), (name, key)
    west = float(inner['rotate'].split()[1]) == 90
    for px, pz in samples:
        ix, iz = world(inner, (px, pz))
        ox, oz = world(fields, (-px, pz))  # the same mesh point on the X-mirrored model
        expected = (2*FENCE - ix, iz) if west else (ix, 2*FENCE - iz)
        assert abs(ox-expected[0]) < 1e-6 and abs(oz-expected[1]) < 1e-6, (name, px, pz)
# Fence-line parts stay on the fence; the drive swaps sides of it.
assert scripts['SG_CatcherPost_Out_Static']['translate'] == '-0.46 0 -0.38'
assert scripts['SG_Drive_Out_Static']['translate'] == '-0.5 0 -0.16'
assert scripts['SG_Drive_W_Out_Static']['translate'] == '-0.16 0 0.5'

# (2) Every leaf/static name the Lua can request exists.
lua = LuaRuntime()
lua.globals().package.path = str(LUA/'shared/?.lua').replace('\\', '/') + ';' + lua.globals().package.path
lua.execute('require "SG_GateTypes"; require "SG_GateCommon"')
requested = 0
for kind in lua.eval('(function() local r={} for k in pairs(SGGateTypes) do r[#r+1]=k end return r end)()').values():
    static_prefix = lua.eval(f'SGGateTypes["{kind}"].staticPrefix') or 'SG'
    for orientation in ('N', 'W'):
        for direction in ('forward', 'reverse'):
            for quality in ('low', 'medium', 'high'):
                base = lua.eval(f'SGGate.leafModel("{kind}","{orientation}","{direction}","{quality}","outer")')
                assert base.endswith('_G_Out'), base
                for damage in ('', '_Damage1', '_Damage2', '_Damage3'):
                    for pose in ('_Open', '_Closed'):
                        assert base+damage+pose in scripts, base+damage+pose
                        requested += 1
            for part in ('CatcherPost', 'GuidePost', 'Rail', 'Drive'):
                name = f'{static_prefix}_{part}' + ('_Reverse' if direction == 'reverse' else '') + \
                    ('_W' if orientation == 'W' else '') + '_Out_Static'
                assert name in scripts, name
assert requested == 6*2*2*3*4*2

# (3) Gameplay: same cells and collision, outer metadata/models, far-row vehicles.
tree = ast.parse((ROOT/'tests/test_gate_widths.py').read_text())
MOCK = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == 'MOCK' for target in node.targets))
for server in (False, True):
    lua = LuaRuntime()
    lua.globals().package.path = str(LUA/'shared/?.lua').replace('\\', '/') + ';' + lua.globals().package.path
    lua.execute(MOCK)
    lua.globals().width, lua.globals().serverMode = 4, server
    lua.execute('require "SG_GateCore"')
    lua.execute(r'''
    assert(not SGGate.canBuild(square(30,20,0),'chainlink4','N','forward','sideways'))
    local id=SGGate.build(square(30,20,0),'chainlink4',100,'N','forward','high','outer')
    assert(id=='30,20,0' and SGGate.side(id)=='outer' and SGGate.snapshot(id).side=='outer')
    local leaf=SGGate.findRole(id,'leaf')
    assert(leaf.sq.x==29 and leaf.sq.y==20 and leaf.north==true)
    assert(leaf.model=='Base.SG_ChainLink_4_N_Right_G_Out_Closed')
    local statics={}
    for _,o in ipairs(SGGate.parts(id)) do
        assert(o.md.sgSide=='outer' and o.md.sgOrientation=='N')
        if o.md.sgRole=='slave' then assert(o.north==true and o.sq.y==20 and o.sq.x>=26 and o.sq.x<=29) end
        if o.md.sgStatic then statics[o.md.sgStatic]=(statics[o.md.sgStatic] or 0)+1 end
    end
    assert(statics.SG_CatcherPost_Out_Static==1 and statics.SG_GuidePost_Out_Static==1 and statics.SG_Rail_Out_Static==8)
    SGGate.installDrive(id)
    assert(SGGate.findRole(id,'drive').model=='Base.SG_Drive_Out_Static')
    -- The outer leaf runs over the far row: a vehicle there blocks it, but not an inner gate.
    square(25,19,0).vehicle=true
    assert(SGGate.isBlocked(id,true))
    local inner=SGGate.build(square(30,40,0),'chainlink4',100,'N','forward','high')
    assert(SGGate.side(inner)=='inner' and SGGate.findRole(inner,'leaf').model=='Base.SG_ChainLink_4_N_Right_G_Closed')
    square(25,39,0).vehicle=true
    assert(not SGGate.isBlocked(inner,true))
    square(25,19,0).vehicle=false; square(25,39,0).vehicle=false
    assert(not SGGate.isBlocked(id,true))
    -- Damage, quality and W/reverse names compose with the outer suffix.
    SGGate.registry()[id].damage=2; leaf.invalidateRenderChunkLevel=function() end; SGGate.applyModel(leaf)
    assert(leaf.model=='Base.SG_ChainLink_4_N_Right_G_Out_Damage2_Closed')
    assert(SGGate.leafModel('chainlink4','W','reverse','low','outer')=='SG_ChainLink_4_Low_W_Reverse_G_Out')
    assert(SGGate.leafModel('wood6','N','forward','medium','outer')=='SG_Wood_6_Medium_N_Right_G_Out')
    -- Metadata bootstraps the side before the registry; legacy gates are inner.
    local entry=SGGate.registry()[id]; SGGate.registry()[id]=nil
    assert(SGGate.side(id)=='outer'); SGGate.registry()[id]=entry
    assert(SGGate.side('99,99,0')=='inner')
    SGGate.remove(id); SGGate.remove(inner)
    ''')
    print(f'PASS outer gameplay server={server}: cells, collision, models, drive, far-row vehicles, metadata')

# (4) Construction cursor: eight R states; outer previews use tileset sg_gates_preview_02.
lua = LuaRuntime()
lua.globals().package.path = str(LUA/'shared/?.lua').replace('\\', '/') + ';' + lua.globals().package.path
lua.execute('require "SG_GateCommon"')
lua.execute(r'''
Events={OnGameBoot={Add=function(fn) install=fn end},OnGameStart={Add=function() end},OnServerStarted={Add=function() end}}
function isClient() return false end
function isServer() return true end
KeybindId={ROTATE_BUILDING='rotate'}
function getCore() return {isKey=function(_,binding,key) return key==binding end} end
function square(x,y,z) return {getX=function() return x end,getY=function() return y end,getZ=function() return z end} end
function getCell() return {getGridSquare=function(_,x,y,z) return square(x,y,z) end} end
SGGate.canBuild=function() return true end
SGGate.build=function(sq,kind,level,orientation,direction,quality,side) built={orientation,direction,side}; return 'gate' end
calls={}
function getSprite(name) return {name=name,RenderGhostTileColor=function(_,x,y) calls[#calls+1]={name,x,y} end} end
faceCalls=0
ISBuildIsoEntity={new=function(self,character,info,nSprite) return setmetatable({objectInfo=info,spriteCache={},nSprite=nSprite},{__index=self}) end,
 isValid=function() return true end, setInfo=function() end, rotateKey=function() end,
 render=function() end, create=function(self) self:setInfo() end,
 getFace=function(self) assert(self.nSprite>=1 and self.nSprite<=4); faceCalls=faceCalls+1; if not self.face then self.face={getzLayers=function() return 1 end,getWidth=function() return 1 end,getHeight=function() return 1 end,getTileInfo=function() return {getSpriteName=function() return 'sg_gates_preview_01_5' end} end}; self:cacheSprites(self.face) end; return self.face end,
 getSprite=function(self) assert(self.nSprite>=1 and self.nSprite<=4); self.north=self.nSprite==2 or self.nSprite==4; return 'sprite' end,
 cacheSprites=function() end}
''')
lua.execute((LUA/'shared/SG_GateConstruction.lua').read_text(encoding='utf-8'))
lua.execute(r'''
install()
local info={getScript=function() return {getName=function() return 'SlidingGateChainLink4' end} end}
local b=ISBuildIsoEntity:new(nil,info,nil)
local order={}
for i=1,8 do order[#order+1]=b.nSprite; b:rotateKey('rotate') end
assert(table.concat(order,',')=='2,1,6,5,4,3,8,7' and b.nSprite==2)
assert(ISBuildIsoEntity:new(nil,info,7).nSprite==7) -- serialized outer state survives reconstruction
-- Toggling side on the same native face recaches the footprint carriers.
local r=ISBuildIsoEntity:new(nil,info,1); r:getFace()
r.spriteCache['sg_gates_preview_01_5']=getSprite('sg_gates_preview_01_5')
r:rotateKey('rotate'); r:getFace(); assert(r.nSprite==6 and r.spriteCache['sg_gates_preview_01_5'].name=='sg_gates_preview_02_5')
for _=1,5 do r:rotateKey('rotate') end; assert(r.nSprite==7); r:getFace()
r:rotateKey('rotate'); r:getFace(); assert(r.nSprite==2 and r.spriteCache['sg_gates_preview_01_5'].name=='sg_gates_preview_01_5')
for _,n in ipairs({2,1,6,5,4,3,8,7}) do
 local g=ISBuildIsoEntity:new(nil,info,n)
 local face=g:getFace(); assert(face and g.nSprite==n)
 assert(g:getSprite()=='sprite' and g.nSprite==n)
 assert(g:isValid(square(100,200,0)) and g.north==(n%2==0))
 -- Footprint carriers are remapped for outer faces.
 assert(g.spriteCache['sg_gates_preview_01_5'].name==(n>4 and 'sg_gates_preview_02_5' or 'sg_gates_preview_01_5'))
 calls={}; g:render(100,200,0,square(100,200,0))
 local outerSide=n>4
 for _,c in ipairs(calls) do
  assert(c[1]:match('^sg_gates_preview_0'..(outerSide and 2 or 1)..'_%d+$'), c[1])
 end
 assert(#calls==2+8)
 g.character={getPerkLevel=function() return 8 end, isBuildCheat=function() return false end}
 g.sgPlaceholdersReached=nil; g:create(100,200,0,n%2==0)
 assert(built[1]==(n%2==0 and 'N' or 'W') and built[2]==((n-1)%4+1>=3 and 'reverse' or 'forward'))
 assert(built[3]==(outerSide and 'outer' or 'inner'))
end
''')
print('PASS outer cursor: 8 R states, native face/sprite mapping, outer preview carriers, authority side')
print(f'PASS {len(outer)} outer spriteModels reflect inner poses through the fence plane; {requested} leaf names registered')
