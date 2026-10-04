-- SlidingGates: unified gate object (prototype, singleplayer).
-- A gate is a set of parts sharing modData.sgGate = "<x>,<y>,<z>" (master leaf cell):
--   (x0 = visual origin cell: catcher post; the opening is x0-1 and x0-2)
--   leaf    master door at x0-1 carrying the animated leaf model (model translate compensates the shift)
--   slave   door at x0-2 (second cell of the opening), hidden model, toggled with the leaf
--   block   closed hidden doors at x0-3, x0-4, present only while the gate is open (cells the leaf stands in)
--   post/rail  static decoration; drive  optional add-on, can be installed on an existing gate
-- N-edge gates extend towards -x (see research/vanilla-gates.md).

SGGate = SGGate or {}

local TYPES = {
    chainlink = {
        leafModel = "SG_ChainLink_N_Right_G", -- spriteModels *_G_*: leaf carrier is one cell to the left of the model origin
        doorSprites = { "fixtures_doors_fences_01_129", "fixtures_doors_fences_01_131" }, -- closed, open (N edge)
    },
}

local function log(msg)
    print("[SGGate] " .. tostring(msg))
    local pl = getPlayer()
    if pl then pl:setHaloNote(tostring(msg), 255, 255, 255, 120) end
end

local function sqAt(x, y, z) return getCell():getGridSquare(x, y, z) end

local function parseId(id)
    local x, y, z = id:match("^(-?%d+),(-?%d+),(-?%d+)$")
    return tonumber(x), tonumber(y), tonumber(z)
end

local function tag(obj, id, role, extra)
    local d = obj:getModData()
    d.sgGate = id
    d.sgRole = role
    if extra then for k, v in pairs(extra) do d[k] = v end end
end

-- resting pose of a door part: hidden parts use SG_Hidden, the leaf uses Closed/Open pose of its model
function SGGate.applyModel(obj)
    local base = obj:getModData().sgBase
    if not base then return end
    if base == "SG_Hidden" then
        obj:setSpriteModelName("Base.SG_Hidden")
    else
        obj:setSpriteModelName("Base." .. base .. (obj:IsOpen() and "_Open" or "_Closed"))
    end
end

-- door-thumpable on the N edge of sq whose model is `modelBase`
local function makeDoor(sq, typeId, id, role, modelBase)
    local pair = TYPES[typeId].doorSprites
    local obj = IsoThumpable.new(getWorld():getCell(), sq, pair[1], pair[2], true, {})
    obj:setMaxHealth(500)
    obj:setHealth(500)
    obj:setIsDoor(true)
    obj:setCanPassThrough(false)
    obj:setIsThumpable(true)
    tag(obj, id, role, { sgBase = modelBase, sgType = typeId })
    sq:AddSpecialObject(obj)
    SGGate.applyModel(obj)
    sq:RecalcAllWithNeighbours(true)
    return obj
end

local function makeStatic(sq, id, role, modelName)
    if not sq then return end
    local obj = IsoObject.new(getWorld():getCell(), sq, "vegetation_groundcover_01_0")
    obj:setSpriteModelName("Base." .. modelName)
    tag(obj, id, role)
    sq:AddTileObject(obj)
    return obj
end

local function removeObj(obj)
    local sq = obj:getSquare()
    if not sq then return end
    sq:transmitRemoveItemFromSquare(obj)
    sq:RecalcAllWithNeighbours(true)
end

local function toggleDoor(obj)
    obj:ToggleDoor(getPlayer())
    SGGate.applyModel(obj)
end

-- all parts of the gate id (scans the cells it can occupy)
function SGGate.parts(id)
    local x, y, z = parseId(id)
    local res = {}
    for dx = -5, 1 do
        local sq = sqAt(x + dx, y, z)
        if sq then
            local objs = sq:getObjects()
            for i = 0, objs:size() - 1 do
                local o = objs:get(i)
                if o:getModData().sgGate == id then res[#res + 1] = o end
            end
        end
    end
    return res
end

local function findRole(id, role)
    for _, o in ipairs(SGGate.parts(id)) do
        if o:getModData().sgRole == role then return o end
    end
end

-- registry of gate ids (persisted in global ModData) so the sync handler knows which gates exist
local function registry()
    local md = ModData.getOrCreate("SlidingGates")
    md.gates = md.gates or {}
    return md.gates
end

-- Pocket cells get a blocker only when the N edge is not already blocked (e.g. by a fence): a door-thumpable
-- placed on a fence cell makes the neighbouring fence sections fade (cutaway), and the fence blocks anyway.
local function addPocketBlockers(id, typeId, x, y, z)
    for k = 3, 4 do
        local sq, north = sqAt(x - k, y, z), sqAt(x - k, y - 1, z)
        if sq and north and not sq:isBlockedTo(north) then
            makeDoor(sq, typeId, id, "block", "SG_Hidden")
        end
    end
end

-- Build a gate WITHOUT drive. sq = master (leaf) cell; returns the gate id.
function SGGate.build(sq, typeId)
    typeId = typeId or "chainlink"
    local t = TYPES[typeId]
    local x, y, z = sq:getX(), sq:getY(), sq:getZ()
    local id = x .. "," .. y .. "," .. z
    registry()[id] = true
    makeDoor(sqAt(x - 1, y, z), typeId, id, "leaf", t.leafModel)
    makeDoor(sqAt(x - 2, y, z), typeId, id, "slave", "SG_Hidden")
    makeStatic(sq, id, "post", "SG_CatcherPost_Static")
    makeStatic(sqAt(x - 2, y, z), id, "post", "SG_GuidePost_Static")
    for k = 0, 3 do makeStatic(sqAt(x - k, y, z), id, "rail", "SG_Rail_Static") end
    log("gate built " .. id .. " (no drive)")
    return id
end

function SGGate.installDrive(id)
    if findRole(id, "drive") then log("drive already installed"); return end
    local x, y, z = parseId(id)
    makeStatic(sqAt(x - 2, y, z), id, "drive", "SG_Drive_Static")
    log("drive installed on " .. id)
end

function SGGate.removeDrive(id)
    local d = findRole(id, "drive")
    if d then removeObj(d); log("drive removed from " .. id) end
end

-- While the leaf animates, a second toggle would restart the clip from its first frame and the leaf would
-- jump to the end pose. So for the duration of the animation the door parts stop being doors (setIsDoor(false)):
-- mouse click, E key and the context menu ignore them. The window is tracked with the engine's own progress rate.
local ANIM_SECONDS = 2.0   -- clip length (frames 1..49 at 24 fps)
local ANIM_SPEED = 1.5     -- IsoObjectAnimations track speed
local busy = {}            -- id -> elapsed clip seconds

local function setDoorParts(id, isDoor)
    for _, o in ipairs(SGGate.parts(id)) do
        local role = o:getModData().sgRole
        if role == "leaf" or role == "slave" or role == "block" then
            o:setIsDoor(isDoor)
            local sq = o:getSquare()
            if sq then sq:RecalcAllWithNeighbours(true) end
        end
    end
end

local function startBusy(id)
    busy[id] = 0
    setDoorParts(id, false)
end

local function endBusy(id)
    busy[id] = nil
    setDoorParts(id, true)
end

local function isPaused()
    local sc = UIManager.getSpeedControls()
    return sc and sc:getCurrentGameSpeed() == 0
end

local tickCount = 0
Events.OnTick.Add(function()
    tickCount = tickCount + 1
    if next(busy) and not isPaused() then
        local step = getGameTime():getTimeDelta() * ANIM_SPEED
        for id, t in pairs(busy) do
            t = t + step
            if t >= ANIM_SECONDS then endBusy(id) else busy[id] = t end
        end
    end
    -- safety net (e.g. the game was saved mid-animation): idle gates must have working doors
    if tickCount % 120 == 0 then
        for id, _ in pairs(registry()) do
            if busy[id] == nil then
                local leaf = findRole(id, "leaf")
                if leaf and not leaf:isDoor() then setDoorParts(id, true) end
            end
        end
    end
end)

-- Bring all parts of one gate to the same state. Whatever door was toggled (mouse click, E key, menu, zombie)
-- is the one whose state differs from the last synced state; the other parts follow it.
local function syncGate(id)
    local leaf, slave = findRole(id, "leaf"), findRole(id, "slave")
    if not leaf or not slave then return end
    if busy[id] then return end
    local x, y, z = parseId(id)
    local lo, so = leaf:IsOpen(), slave:IsOpen()
    local last = leaf:getModData().sgOpen
    if last == nil then last = false end
    local blockers, anyOpenBlocker = {}, false
    for _, o in ipairs(SGGate.parts(id)) do
        if o:getModData().sgRole == "block" then
            blockers[#blockers + 1] = o
            if o:IsOpen() then anyOpenBlocker = true end
        end
    end
    if lo == last and so == last and not anyOpenBlocker then return end
    local target = last
    if lo ~= last then target = lo elseif so ~= last then target = so end
    if lo ~= target then toggleDoor(leaf) end
    if so ~= target then toggleDoor(slave) end
    for _, o in ipairs(blockers) do removeObj(o) end
    if target then addPocketBlockers(id, leaf:getModData().sgType, x, y, z) end
    SGGate.applyModel(leaf)
    leaf:getModData().sgOpen = target
    startBusy(id)
    log("gate " .. id .. (target and " opened" or " closed"))
end

local reconciling = false
function SGGate.reconcile()
    if reconciling then return end
    reconciling = true
    local ok, err = pcall(function() for id, _ in pairs(registry()) do syncGate(id) end end)
    reconciling = false
    if not ok then print("[SGGate] reconcile error: " .. tostring(err)) end
end
Events.OnContainerUpdate.Add(SGGate.reconcile)

-- open/close from code (menu, remote): toggling the leaf triggers the sync above
function SGGate.toggle(id)
    local leaf = findRole(id, "leaf")
    if not leaf then log("gate parts missing for " .. id); return end
    if busy[id] then log("gate " .. id .. " is moving"); return end
    toggleDoor(leaf)
end

function SGGate.remove(id)
    registry()[id] = nil
    busy[id] = nil
    for _, o in ipairs(SGGate.parts(id)) do removeObj(o) end
    log("gate removed " .. id)
end

-- how the cells around the gate block movement across the N edge / towards west (collision experiment)
function SGGate.dumpCollision(id)
    local x, y, z = parseId(id)
    for dx = 1, -5, -1 do
        local sq, north = sqAt(x + dx, y, z), sqAt(x + dx, y - 1, z)
        local west = sqAt(x + dx - 1, y, z)
        if sq and north then
            log(string.format("x%+d: N-blocked=%s closedN=%s openN=%s openW=%s west-blocked=%s", dx,
                tostring(sq:isBlockedTo(north)), tostring(sq:hasClosedDoorOnEdge(IsoDirections.N)),
                tostring(sq:hasOpenDoorOnEdge(IsoDirections.N)), tostring(sq:hasOpenDoorOnEdge(IsoDirections.W)),
                tostring(west and sq:isBlockedTo(west))))
        end
    end
end

-- gate ids with a part within r tiles of sq
function SGGate.nearby(sq, r)
    local res, seen = {}, {}
    for dx = -r, r do
        for dy = -r, r do
            local s = sqAt(sq:getX() + dx, sq:getY() + dy, sq:getZ())
            if s then
                local objs = s:getObjects()
                for i = 0, objs:size() - 1 do
                    local d = objs:get(i):getModData()
                    if d.sgGate and not seen[d.sgGate] then seen[d.sgGate] = true; res[#res + 1] = d.sgGate end
                end
            end
        end
    end
    return res
end

Events.OnFillWorldObjectContextMenu.Add(function(player, context, worldobjects, test)
    if test then return end
    local sq
    for _, o in ipairs(worldobjects) do sq = o:getSquare(); if sq then break end end
    if not sq then return end
    local sub = ISContextMenu:getNew(context)
    context:addSubMenu(context:addOption("SG Gate"), sub)
    sub:addOption("Build GATE (no drive), N edge, extends -x", sq, SGGate.build, "chainlink")
    for _, id in ipairs(SGGate.nearby(sq, 5)) do
        sub:addOption("[" .. id .. "] open/close", id, SGGate.toggle)
        sub:addOption("[" .. id .. "] install drive", id, SGGate.installDrive)
        sub:addOption("[" .. id .. "] remove drive", id, SGGate.removeDrive)
        sub:addOption("[" .. id .. "] dump collision", id, SGGate.dumpCollision)
        sub:addOption("[" .. id .. "] remove gate", id, SGGate.remove)
    end
end)
