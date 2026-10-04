-- SlidingGates: unified gate object (prototype, singleplayer).
-- A gate is a set of parts sharing modData.sgGate = "<x>,<y>,<z>" (master leaf cell):
--   (x0 = visual origin cell: catcher post; opening cells x0-1 .. x0-width)
--   leaf    master door at x0-1 carrying the animated leaf model (model translate compensates the shift)
--   slave   hidden doors on the remaining opening cells, toggled with the leaf
--   block   closed hidden doors in x0-width-1 .. x0-2*width while the gate is open
--   post/rail  static decoration; drive  optional add-on, can be installed on an existing gate
-- N-edge gates extend towards -x (see research/vanilla-gates.md).

SGGate = SGGate or {}

local TYPES = {
    chainlink = {
        width = 2,
        leafModel = "SG_ChainLink_N_Right_G", -- spriteModels *_G_*: leaf carrier is one cell to the left of the model origin
        doorSprites = { "fixtures_doors_fences_01_129", "fixtures_doors_fences_01_131" }, -- closed, open (N edge)
    },
    chainlink4 = {
        width = 4,
        leafModel = "SG_ChainLink_4_N_Right_G",
        doorSprites = { "fixtures_doors_fences_01_129", "fixtures_doors_fences_01_131" },
    },
}

-- Older saved registry entries are true and represent the original two-cell gate.
local function gateWidth(id)
    local entry = (ModData.getOrCreate("SlidingGates").gates or {})[id]
    return type(entry) == "table" and entry.width or 2
end

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
    for dx = -(2 * gateWidth(id) + 1), 1 do
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
    local width = TYPES[typeId].width
    for k = width + 1, 2 * width do
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
    if not t then log("unknown gate type " .. tostring(typeId)); return end
    local width = t.width
    local x, y, z = sq:getX(), sq:getY(), sq:getZ()
    local id = x .. "," .. y .. "," .. z
    if registry()[id] then log("gate already exists " .. id); return end
    -- Check all required squares before creating any part.
    for k = 0, 2 * width do
        if not sqAt(x - k, y, z) or not sqAt(x - k, y - 1, z) then
            log("gate area is not loaded"); return
        end
        if k >= 1 and k <= width and sqAt(x - k, y, z):isBlockedTo(sqAt(x - k, y - 1, z)) then
            log("opening is blocked at cell " .. k); return
        end
    end
    registry()[id] = { width = width }
    makeDoor(sqAt(x - 1, y, z), typeId, id, "leaf", t.leafModel)
    for k = 2, width do makeDoor(sqAt(x - k, y, z), typeId, id, "slave", "SG_Hidden") end
    makeStatic(sq, id, "post", "SG_CatcherPost_Static")
    makeStatic(sqAt(x - width, y, z), id, "post", "SG_GuidePost_Static")
    for k = 0, 2 * width - 1 do makeStatic(sqAt(x - k, y, z), id, "rail", "SG_Rail_Static") end
    log("gate built " .. id .. " (no drive)")
    return id
end

function SGGate.installDrive(id)
    if findRole(id, "drive") then log("drive already installed"); return end
    local x, y, z = parseId(id)
    makeStatic(sqAt(x - gateWidth(id), y, z), id, "drive", "SG_Drive_Static")
    log("drive installed on " .. id)
end

function SGGate.removeDrive(id)
    local d = findRole(id, "drive")
    if d then removeObj(d); log("drive removed from " .. id) end
end

-- Bring all parts of one gate to the same state. Whatever door was toggled (mouse click, E key, menu, zombie)
-- is the one whose state differs from the last synced state; the other parts follow it.
local function syncGate(id)
    local leaf = findRole(id, "leaf")
    if not leaf then return end
    local x, y, z = parseId(id)
    local lo = leaf:IsOpen()
    local last = leaf:getModData().sgOpen
    if last == nil then last = false end
    local blockers, slaves, anyOpenBlocker, changedSlave = {}, {}, false, nil
    for _, o in ipairs(SGGate.parts(id)) do
        if o:getModData().sgRole == "slave" then
            slaves[#slaves + 1] = o
            if o:IsOpen() ~= last then changedSlave = o:IsOpen() end
        elseif o:getModData().sgRole == "block" then
            blockers[#blockers + 1] = o
            if o:IsOpen() then anyOpenBlocker = true end
        end
    end
    if lo == last and changedSlave == nil and not anyOpenBlocker then return end
    local target = last
    if lo ~= last then target = lo elseif changedSlave ~= nil then target = changedSlave end
    if lo ~= target then toggleDoor(leaf) end
    for _, slave in ipairs(slaves) do if slave:IsOpen() ~= target then toggleDoor(slave) end end
    for _, o in ipairs(blockers) do removeObj(o) end
    if target then addPocketBlockers(id, leaf:getModData().sgType, x, y, z) end
    SGGate.applyModel(leaf)
    leaf:getModData().sgOpen = target
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

function SGGate.isMoving(id)
    local leaf = findRole(id, "leaf")
    return leaf ~= nil and leaf:isAnimating()
end

-- distance from a character to the nearest door part of the gate (nil if the gate is gone)
function SGGate.distanceTo(chr, id)
    local best
    for _, o in ipairs(SGGate.parts(id)) do
        local role = o:getModData().sgRole
        if role == "leaf" or role == "slave" then
            local sq = o:getSquare()
            local d = sq and math.sqrt((chr:getX() - (sq:getX() + 0.5)) ^ 2 + (chr:getY() - (sq:getY() + 0.5)) ^ 2)
            if d and (not best or d < best) then best = d end
        end
    end
    return best
end

-- open/close from code (menu, remote): toggling the leaf triggers the sync above
function SGGate.toggle(id)
    local leaf = findRole(id, "leaf")
    if not leaf then log("gate parts missing for " .. id); return end
    if leaf:isAnimating() then log("gate " .. id .. " is moving"); return end
    toggleDoor(leaf)
end

function SGGate.remove(id)
    local parts = SGGate.parts(id) -- retain width before deleting its registry entry
    registry()[id] = nil
    for _, o in ipairs(parts) do removeObj(o) end
    log("gate removed " .. id)
end

-- how the cells around the gate block movement across the N edge / towards west (collision experiment)
function SGGate.dumpCollision(id)
    local x, y, z = parseId(id)
    for dx = 1, -(2 * gateWidth(id) + 1), -1 do
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
    sub:addOption("Build 4-cell GATE (no drive), N edge, extends -x", sq, SGGate.build, "chainlink4")
    for _, id in ipairs(SGGate.nearby(sq, 9)) do
        sub:addOption("[" .. id .. "] open/close", id, SGGate.toggle)
        sub:addOption("[" .. id .. "] install drive", id, SGGate.installDrive)
        sub:addOption("[" .. id .. "] remove drive", id, SGGate.removeDrive)
        sub:addOption("[" .. id .. "] dump collision", id, SGGate.dumpCollision)
        sub:addOption("[" .. id .. "] remove gate", id, SGGate.remove)
    end
end)
