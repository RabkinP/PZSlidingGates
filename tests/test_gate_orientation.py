"""W assembly gameplay regressions. Mocks do not establish native visual placement."""
import ast
from pathlib import Path
from lupa import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
LUA = ROOT/'mod/SlidingGates/42/media/lua'
tree = ast.parse((ROOT/'tests/test_gate_widths.py').read_text())
MOCK = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == 'MOCK' for target in node.targets))

for width in (2, 4):
    for server in (False, True):
        lua = LuaRuntime()
        lua.globals().package.path = str(LUA/'shared/?.lua').replace('\\', '/') + ';' + lua.globals().package.path
        lua.execute(MOCK)
        lua.globals().width, lua.globals().serverMode = width, server
        lua.execute('require "SG_GateCore"')
        lua.execute(r'''
        local kind=width==2 and 'chainlink' or 'chainlink4'
        -- W opening crosses the west edge and extends along +Y from the catcher.
        square(30,21,0).fence=true
        assert(not SGGate.canBuild(square(30,20,0),kind,'W'))
        square(30,21,0).fence=false
        assert(not SGGate.canBuild(square(30,20,0),kind,'S'))
        local id=SGGate.build(square(30,20,0),kind,100,'W')
        assert(id=='30,20,0' and SGGate.orientation(id)=='W')
        local leaf=SGGate.findRole(id,'leaf')
        assert(leaf.sq.x==30 and leaf.sq.y==21 and leaf.north==false)
        assert(leaf.sprite=='fixtures_doors_fences_01_128')
        assert(leaf.model=='Base.'..SGGateTypes[kind].westLeafModel..'_Closed')
        assert(SGGate.snapshot(id).orientation=='W')
        for _,o in ipairs(SGGate.parts(id)) do
            assert(o.md.sgOrientation=='W')
            if o.md.sgRole=='slave' then assert(o.north==false) end
            if o.md.sgRole=='collider' then assert(o.sprite=='fixtures_doors_fences_01_38') end
        end
        assert(#partsWithRole(id,'slave')==width)
        assert(#partsWithRole(id,'rail')==2*width)
        SGGate.installDrive(id)
        local drive=SGGate.findRole(id,'drive')
        assert(drive.sq.x==30 and drive.sq.y==20+width and drive.model=='Base.SG_Drive_W_Static')
        local function blocked(k) return square(30,20+k,0):isBlockedTo(square(29,20+k,0)) end
        local function finish()
            delta=1
            for _=1,width do tick() end
            leaf.animating=false
            if tick then tick() end
            assert(not SGGate.isMoving(id))
        end
        -- Vehicle checks and partial-load checks use the rotated destination rows.
        square(30,21+width,0).vehicle=true
        assert(SGGate.toggle(id)==false and not leaf:IsOpen())
        square(30,21+width,0).vehicle=false
        missing='29,'..(21+width)..',0'
        assert(SGGate.toggle(id)==false and not leaf:IsOpen())
        missing=nil
        assert(SGGate.toggle(id))
        delta=1
        for p=1,width do
            tick()
            for k=1,width do assert(blocked(k)==(k>p)) end
            for j=1,width do assert(blocked(width+j)==(j<=math.min(width,p+1))) end
        end
        leaf.animating=false; if tick then tick() end
        assert(leaf.model=='Base.'..SGGateTypes[kind].westLeafModel..'_Open')
        square(30,21,0).vehicle=true
        assert(SGGate.toggle(id)==false and leaf:IsOpen())
        square(30,21,0).vehicle=false
        assert(SGGate.toggle(id)); finish()
        for k=1,width do assert(blocked(k)) end
        for k=width+1,2*width do assert(not blocked(k)) end
        -- E at the retracted W leaf closes the whole SP assembly, not just its proxy.
        if not serverMode then
            assert(SGGate.toggle(id)); finish()
            local pocket=partsWithRole(id,'block')[width]
            pocket:ToggleDoor()
            assert(not pocket:IsOpen() and not leaf:IsOpen() and SGGate.isMoving(id))
            pocket:ToggleDoor()
            assert(SGGate.registry()[id].moving==false)
            finish()
        end
        -- W fence keeps an opaque W damage proxy and needs no duplicate vehicle wall.
        square(30,21+width,0).fence=true
        assert(SGGate.toggle(id)); finish()
        local opaque
        for _,o in ipairs(partsWithRole(id,'block')) do
            if o.md.sgOpaque then opaque=o end
        end
        assert(opaque and opaque.sprite=='fixtures_doors_01_68' and opaque.north==false)
        assert(#partsWithRole(id,'collider')==width-1)
        -- Interrupted closing waits for the W neighbour to load, then restores all cells.
        assert(SGGate.toggle(id))
        missing='29,'..(20+2*width)..',0'
        gameStart()
        assert(SGGate.isMoving(id) and SGGate.registry()[id].moving==false)
        missing=nil
        for _=1,120 do if tick then tick() end end
        leaf.animating=false
        assert(not SGGate.isMoving(id) and not leaf:IsOpen() and SGGate.registry()[id].moving==nil)
        for k=1,width do assert(blocked(k)) end
        -- Object metadata bootstraps direction/width before the MP registry arrives.
        local entry=SGGate.registry()[id]
        SGGate.registry()[id]=nil
        assert(SGGate.orientation(id)=='W' and SGGate.gateWidth(id)==width)
        assert(SGGate.findRole(id,'leaf')==leaf)
        SGGate.registry()[id]=entry
        SGGate.remove(id)
        for k=0,2*width do assert(#square(30,20+k,0).objects==0) end
        assert(SGGate.orientation('99,99,0')=='N') -- legacy default
        ''')
        print(f'PASS W {width} server={server}: parts, models, door/vehicle carriers, motion, fences, reload, metadata, cleanup')
