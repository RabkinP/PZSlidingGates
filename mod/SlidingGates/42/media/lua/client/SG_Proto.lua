-- SlidingGates PROTOTYPE (stage 1b). Singleplayer debug only.
-- Findings so far: model-rendered objects (spriteModel) ignore IsoObject:setOffsetX/Y, so the
-- animation has to come from the glb (Open/Close animations), triggered by IsoThumpable:ToggleDoor.
-- This prototype spawns real vanilla gates (IsoThumpable doors) and toggles them, to observe:
--  * how the model animation looks and how the model is clipped/sorted outside its square
--  * door collision edge before/after toggling (see Dump)
--  * two adjacent gate tiles toggled together
-- Right-click a square -> "SG Proto" submenu.

SGProto = SGProto or {}

-- closed, open sprite per orientation
local TYPES = {
    large = { W = { "fixtures_doors_fences_01_128", "fixtures_doors_fences_01_130" },
              N = { "fixtures_doors_fences_01_129", "fixtures_doors_fences_01_131" } },
    small = { W = { "fixtures_doors_fences_01_16", "fixtures_doors_fences_01_18" },
              N = { "fixtures_doors_fences_01_17", "fixtures_doors_fences_01_19" } },
}

local function log(msg)
    print("[SGProto] " .. tostring(msg))
    local pl = getPlayer()
    if pl then pl:setHaloNote(tostring(msg), 255, 255, 255, 120) end
end

local function applyModel(obj)
    local base = obj:getModData().sgBase
    if base then obj:setSpriteModelName("Base." .. base .. (obj:IsOpen() and "_Open" or "_Closed")) end
end

local function spawnGate(sq, typeId, north)
    if not sq then return end
    local pair = TYPES[typeId][north and "N" or "W"]
    local obj = IsoThumpable.new(getWorld():getCell(), sq, pair[1], pair[2], north, {})
    obj:setMaxHealth(500)
    obj:setHealth(500)
    obj:setIsDoor(true)
    obj:setCanPassThrough(false)
    obj:setIsThumpable(true)
    sq:AddSpecialObject(obj)
    sq:RecalcAllWithNeighbours(true)
    log("spawned " .. typeId .. (north and " N " or " W ") .. sq:getX() .. "," .. sq:getY())
    return obj
end

-- vanilla gate door logic + our own glb model (modelName like "SG_ChainLink_N_Right")
local function spawnSG(sq, modelName, north)
    local obj = spawnGate(sq, "large", north)
    if not obj then return end
    obj:getModData().sgBase = modelName
    applyModel(obj)
    log("spawned SG model " .. modelName)
end

-- static decoration piece: plain IsoObject carrying one of our models (carrier sprite is never drawn)
local function spawnStatic(sq, modelName)
    if not sq then return end
    local obj = IsoObject.new(getWorld():getCell(), sq, "vegetation_groundcover_01_0")
    obj:setSpriteModelName("Base." .. modelName)
    sq:AddTileObject(obj)
    return obj
end

-- N-edge assembly. In game, model +X (Blender X) maps to world -x, so the whole layout runs along -x:
-- catcher post at x, guide post at x-2, rail x..x-3, drive at x-2, leaf from x towards x-2 (opens towards -x).
local function spawnAssembly(sq, leafModel, driveModel)
    local x, y, z = sq:getX(), sq:getY(), sq:getZ()
    local function at(k) return getCell():getGridSquare(x - k, y, z) end
    spawnSG(sq, leafModel, true)
    spawnStatic(at(0), "SG_CatcherPost_Static")
    spawnStatic(at(2), "SG_GuidePost_Static")
    for k = 0, 3 do spawnStatic(at(k), "SG_Rail_Static") end
    spawnStatic(at(2), driveModel or "SG_Drive_Static")
    log("assembly spawned")
end

-- spawn two neighbouring gate tiles along the gate line (N edge: +x, W edge: +y)
local function spawnPair(sq, typeId, north)
    spawnGate(sq, typeId, north)
    local x, y, z = sq:getX(), sq:getY(), sq:getZ()
    local sq2 = getCell():getGridSquare(north and x + 1 or x, north and y or y + 1, z)
    spawnGate(sq2, typeId, north)
end

local function dumpObj(obj)
    local sq = obj:getSquare()
    log("---- dump ----")
    log("class=" .. tostring(obj:getObjectName()) .. " sprite=" .. tostring(obj:getSpriteName()))
    local spr = obj:getSprite()
    local props = spr and spr:getProperties()
    if props then
        for _, k in ipairs({ "collideN", "collideW", "solid", "solidtrans", "doorN", "doorW", "attachedN", "attachedW", "attachedE", "attachedS", "doorTrans" }) do
            local ok, v = pcall(function() return props:has(k) end)
            local flag = IsoFlagType[k]
            local ok2, v2 = pcall(function() return flag and props:has(flag) end)
            log(k .. " str=" .. tostring(ok and v) .. " flag=" .. tostring(ok2 and v2))
        end
    end
    local sm = obj:getSpriteModel()
    log("spriteModel=" .. tostring(sm and sm:getModelScriptName()) .. " anim=" .. tostring(sm and sm.animationName))
    if instanceof(obj, "IsoThumpable") then
        log("isDoor=" .. tostring(obj:isDoor()) .. " open=" .. tostring(obj:IsOpen()) .. " north=" .. tostring(obj:getNorth())
            .. " edge=" .. tostring(obj:getSpriteEdge(false)))
    end
    if sq then
        log("sq " .. sq:getX() .. "," .. sq:getY() .. " hasClosedDoorN=" .. tostring(sq:hasClosedDoorOnEdge(IsoDirections.N))
            .. " W=" .. tostring(sq:hasClosedDoorOnEdge(IsoDirections.W))
            .. " openN=" .. tostring(sq:hasOpenDoorOnEdge(IsoDirections.N))
            .. " openW=" .. tostring(sq:hasOpenDoorOnEdge(IsoDirections.W)))
    end
end

local function describe(o)
    local sq = o:getSquare()
    return string.format("%s@%d,%d,%d open=%s north=%s edge=%s", tostring(o:getSpriteName()), sq:getX(), sq:getY(), sq:getZ(),
        tostring(o:IsOpen()), tostring(o:getNorth()), tostring(o:getSpriteEdge(false)))
end

local function toggle(obj)
    local before = describe(obj)
    obj:ToggleDoor(getPlayer())
    applyModel(obj) -- the running animation keeps its own model; this sets the resting pose of the new state
    log("toggle: " .. before .. " -> open=" .. tostring(obj:IsOpen()) .. " obstructed=" .. tostring(obj:isObstructed()))
end

-- every door-thumpable within `r` tiles of the square (hit-testing of open gates is unreliable)
local function nearbyDoors(sq, r)
    local res = {}
    local cell = getCell()
    for dx = -r, r do
        for dy = -r, r do
            local s = cell:getGridSquare(sq:getX() + dx, sq:getY() + dy, sq:getZ())
            if s then
                local objs = s:getSpecialObjects()
                for i = 0, objs:size() - 1 do
                    local o = objs:get(i)
                    if instanceof(o, "IsoThumpable") and o:isDoor() then res[#res + 1] = o end
                end
            end
        end
    end
    return res
end

-- toggle this gate and its neighbour along the gate line
local function togglePair(obj)
    toggle(obj)
    local sq = obj:getSquare()
    local north = obj:getNorth()
    local x, y, z = sq:getX(), sq:getY(), sq:getZ()
    local sq2 = getCell():getGridSquare(north and x + 1 or x, north and y or y + 1, z)
    if not sq2 then return end
    local objs = sq2:getSpecialObjects()
    for i = 0, objs:size() - 1 do
        local o = objs:get(i)
        if instanceof(o, "IsoThumpable") and o:isDoor() then toggle(o) end
    end
end

local function removeObj(obj)
    local sq = obj:getSquare()
    sq:transmitRemoveItemFromSquare(obj)
    sq:RecalcAllWithNeighbours(true)
end

local function fillMenu(player, context, worldobjects, test)
    if test then return true end
    local sq
    for _, o in ipairs(worldobjects) do sq = o:getSquare(); if sq then break end end
    if not sq then return end

    local sub = ISContextMenu:getNew(context)
    context:addSubMenu(context:addOption("SG Proto"), sub)

    for _, typeId in ipairs({ "large", "small" }) do
        sub:addOption("Spawn " .. typeId .. " gate (N edge)", sq, spawnGate, typeId, true)
        sub:addOption("Spawn " .. typeId .. " gate (W edge)", sq, spawnGate, typeId, false)
        sub:addOption("Spawn " .. typeId .. " PAIR (N edge, +x)", sq, spawnPair, typeId, true)
        sub:addOption("Spawn " .. typeId .. " PAIR (W edge, +y)", sq, spawnPair, typeId, false)
    end

    for _, m in ipairs({ "SG_ChainLink_N_Right", "SG_ChainLink_N_Left", "SG_ChainLink_W_Right", "SG_ChainLink_W_Left" }) do
        sub:addOption("Spawn SG model " .. m, sq, spawnSG, m, m:find("_N_") ~= nil)
    end

    sub:addOption("Spawn SG ASSEMBLY (N, -x) drive A (z -0.28)", sq, spawnAssembly, "SG_ChainLink_N_Right", "SG_Drive_Static")
    sub:addOption("Spawn SG ASSEMBLY (N, -x) drive B (z -0.72)", sq, spawnAssembly, "SG_ChainLink_N_Right", "SG_Drive_StaticB")

    local doors = nearbyDoors(sq, 3)
    sub:addOption("Toggle ALL gates within 3 tiles (" .. #doors .. ")", doors, function(list) for _, o in ipairs(list) do toggle(o) end end)
    sub:addOption("Dump ALL gates within 3 tiles", doors, function(list) for _, o in ipairs(list) do log(describe(o)); dumpObj(o) end end)
    sub:addOption("Remove ALL gates within 3 tiles", doors, function(list) for _, o in ipairs(list) do removeObj(o) end end)
    for _, obj in ipairs(doors) do
        local name = describe(obj)
        sub:addOption("Toggle: " .. name, obj, toggle)
        sub:addOption("Dump: " .. name, obj, dumpObj)
        sub:addOption("Remove: " .. name, obj, removeObj)
    end
end

Events.OnFillWorldObjectContextMenu.Add(fillMenu)
