-- World mutation runs in singleplayer or on the multiplayer authority only.
-- A gate is a set of parts sharing modData.sgGate = "<x>,<y>,<z>" (master leaf cell):
--   (x0 = visual origin cell: catcher post; opening cells x0-1 .. x0-width)
--   leaf    master door at x0-1 carrying the animated leaf model (model translate compensates the shift)
--   slave   hidden doors on the remaining opening cells, toggled with the leaf
--   block   closed hidden doors in x0-width-1 .. x0-2*width while the gate is open
--   post/rail  static decoration; drive  optional add-on, can be installed on an existing gate
-- N edges extend along -X; W edges along +Y. Registry/part metadata stores the orientation.

require "SG_GateCommon"
if isClient() then return end
if SGGate.coreLoaded then return end
SGGate.coreLoaded = true

SGGate = SGGate or {}
local TYPES = SGGateTypes
local requestPlayer
local authorizedGate
local recoveryReady = false
local deferredSquares = {}
local cleanupSquare
local removingParts = 0

function SGGate.ensureIdentity(id)
    local gates = SGGate.registry()
    local entry = gates[id]
    if not entry then return end
    if type(entry) ~= "table" then entry = { width = 2 }; gates[id] = entry end
    if not entry.instance then
        local data = ModData.getOrCreate("SlidingGates")
        data.serial = (data.serial or 0) + 1
        entry.instance = data.serial
    end
    entry.revision = entry.revision or 0
    entry.width = entry.width or 2
    entry.orientation = entry.orientation or SGGate.orientation(id)
    return entry
end

function SGGate.snapshot(id)
    local entry = SGGate.ensureIdentity(id)
    local leaf = SGGate.findRole(id, "leaf")
    if not entry or not leaf then return end
    local md = leaf:getModData()
    return { id = id, instance = entry.instance, revision = entry.revision,
        type = md.sgType, width = entry.width, orientation = entry.orientation, open = md.sgOpen or false,
        moving = entry.moving ~= nil, slavesOpen = md.sgSlavesOpen or false }
end

local function publish(id)
    local entry = SGGate.ensureIdentity(id)
    local leaf = SGGate.findRole(id, "leaf")
    if not entry or not leaf then return end
    entry.revision = entry.revision + 1
    local md = leaf:getModData()
    md.sgInstance, md.sgRevision, md.sgWidth = entry.instance, entry.revision, entry.width
    entry.open = md.sgOpen or false
    if isServer() then leaf:transmitModData() end
    if SGGate.onStateChanged then SGGate.onStateChanged(SGGate.snapshot(id)) end
end

local function transmitNew(obj)
    if isServer() then obj:transmitCompleteItemToClients() end
end

-- Door tiles without doorTrans (metal door, N edge: closed / open). A see-through (doorTrans) door in a fence cell lets the
-- engine's vision test see past the fence, and FBORenderCutaways then cuts the whole fence run away; an opaque
-- door keeps the vision block of the fence. Used for pocket blockers on cells that already have a fence.
local OPAQUE_DOOR_SPRITES = { "fixtures_doors_01_69", "fixtures_doors_01_71" }

-- Vehicles do not use our door logic: the physics (Bullet) shape of a square comes from its sprite properties
-- (IsoChunk.calcPhysics). A static hidden object whose sprite has PhysicsShape = WallN gives vehicles a wall on the
-- N edge of the square; it is present exactly where the gate blocks walking (and not on fence cells, which already
-- have a wall shape). Vanilla double doors do the same with their PhysicsShape tiles.
local PHYSICS_SPRITE_N = "fixtures_doors_fences_01_36"

-- Older saved registry entries are true and represent the original two-cell gate.
local gateWidth = SGGate.gateWidth

-- all door parts of a gate carry the gate's full health: the gate falls when any part is destroyed
local function gateHealth(id, typeId)
    local entry = (ModData.getOrCreate("SlidingGates").gates or {})[id]
    if type(entry) == "table" and entry.health then return entry.health end
    return TYPES[typeId] and TYPES[typeId].baseHealth or 300
end

local function log(msg)
    print("[SGGate] " .. tostring(msg))
    local pl = getPlayer()
    if pl then pl:setHaloNote(tostring(msg), 255, 255, 255, 120) end
end

local function sqAt(x, y, z) return getCell():getGridSquare(x, y, z) end
local function gateCell(id, x, y, z, k) return SGGate.cellAt(x, y, z, k, SGGate.orientation(id)) end
local function gateNeighbour(id, sq) return SGGate.edgeNeighbour(sq, SGGate.orientation(id)) end
local function opaquePair(id)
    return SGGate.orientation(id) == "W" and { "fixtures_doors_01_68", "fixtures_doors_01_70" } or OPAQUE_DOOR_SPRITES
end
local function staticModel(id, name)
    return name .. (SGGate.orientation(id) == "W" and "_W_Static" or "_Static")
end

local parseId = SGGate.parseId

local function tag(obj, id, role, extra)
    local d = obj:getModData()
    d.sgGate = id
    d.sgRole = role
    local entry = SGGate.ensureIdentity(id)
    if entry then d.sgInstance, d.sgWidth, d.sgOrientation = entry.instance, entry.width, entry.orientation end
    if extra then for k, v in pairs(extra) do d[k] = v end end
end

-- Door-thumpable on the assembly edge whose model is `modelBase`.
local function makeDoor(sq, typeId, id, role, modelBase, spritePair)
    local west = SGGate.orientation(id) == "W"
    local pair = spritePair or (west and TYPES[typeId].westDoorSprites or TYPES[typeId].doorSprites)
    local obj = IsoThumpable.new(getWorld():getCell(), sq, pair[1], pair[2], not west, {})
    local hp = gateHealth(id, typeId)
    obj:setMaxHealth(hp)
    obj:setHealth(hp)
    obj:setIsDoor(true)
    obj:setCanPassThrough(false)
    obj:setIsThumpable(true)
    tag(obj, id, role, { sgBase = modelBase, sgType = typeId, sgOpaque = spritePair ~= nil })
    sq:AddSpecialObject(obj)
    SGGate.applyModel(obj)
    sq:RecalcAllWithNeighbours(true)
    transmitNew(obj)
    return obj
end

local function makeStatic(sq, id, role, modelName)
    if not sq then return end
    local obj = IsoObject.new(getWorld():getCell(), sq, "vegetation_groundcover_01_0")
    obj:setSpriteModelName("Base." .. modelName)
    tag(obj, id, role, { sgStatic = modelName })
    sq:AddTileObject(obj)
    transmitNew(obj)
    return obj
end

local function removeObj(obj)
    local sq = obj:getSquare()
    if not sq then return end
    -- Removing our collision carrier may synchronously emit OnContainerUpdate.
    -- Do not reconcile the intermediate assembly and mistake that carrier for a fence.
    removingParts = removingParts + 1
    local ok, err = pcall(function()
        sq:transmitRemoveItemFromSquare(obj)
        sq:RecalcAllWithNeighbours(true)
    end)
    removingParts = removingParts - 1
    if not ok then error(err) end
end

local function toggleDoor(obj)
    local wasOpen = obj:IsOpen()
    obj:ToggleDoor(requestPlayer or getPlayer())
    SGGate.applyModel(obj)
    -- ToggleDoor returns no success value: obstruction/locks can refuse the request.
    return obj:IsOpen() ~= wasOpen
end

local findRole = SGGate.findRole

-- registry of gate ids (persisted in global ModData) so the sync handler knows which gates exist
local registry = SGGate.registry

-- Pocket cells get a blocker only when the N edge is not already blocked (e.g. by a fence): a door-thumpable
-- placed on a fence cell makes the neighbouring fence sections fade (cutaway), and the fence blocks anyway.
local function addPocketBlockers(id, typeId, x, y, z)
    local width = TYPES[typeId].width
    for k = width + 1, 2 * width do
        local sq = gateCell(id, x, y, z, k)
        local north = gateNeighbour(id, sq)
        if sq and north then
            -- fenced cell: opaque blocker (collision/damage proxy, vision stays blocked); free cell: see-through one
            local pair = sq:isBlockedTo(north) and opaquePair(id) or nil
            makeDoor(sq, typeId, id, "block", "SG_Hidden", pair)
        end
    end
end

-- Build a gate without drive. sq is the catcher cell; the master is one travel cell away.
function SGGate.build(sq, typeId, healthBonus, orientation)
    typeId = typeId or "chainlink"
    orientation = orientation or "N"
    local ok, reason = SGGate.canBuild(sq, typeId, orientation)
    if not ok then log(reason); return end
    local t = TYPES[typeId]
    local width = t.width
    local x, y, z = sq:getX(), sq:getY(), sq:getZ()
    local id = x .. "," .. y .. "," .. z
    registry()[id] = { width = width, type = typeId, orientation = orientation, health = t.baseHealth + (healthBonus or 0) }
    makeDoor(gateCell(id, x, y, z, 1), typeId, id, "leaf", orientation == "W" and t.westLeafModel or t.leafModel)
    for k = 1, width do makeDoor(gateCell(id, x, y, z, k), typeId, id, "slave", "SG_Hidden") end -- collision of the opening
    makeStatic(sq, id, "post", staticModel(id, "SG_CatcherPost"))
    makeStatic(gateCell(id, x, y, z, width), id, "post", staticModel(id, "SG_GuidePost"))
    for k = 0, 2 * width - 1 do makeStatic(gateCell(id, x, y, z, k), id, "rail", staticModel(id, "SG_Rail")) end
    SGGate.finalize(id) -- initial closed state: physics colliders on the opening cells
    log("gate built " .. id .. " (no drive)")
    return id
end

function SGGate.installDrive(id)
    if findRole(id, "drive") then log("drive already installed"); return end
    local x, y, z = parseId(id)
    makeStatic(gateCell(id, x, y, z, gateWidth(id)), id, "drive", staticModel(id, "SG_Drive"))
    log("drive installed on " .. id)
end

function SGGate.removeDrive(id)
    local d = findRole(id, "drive")
    if d then removeObj(d); log("drive removed from " .. id) end
end

-- Collision of the opening is carried by hidden "slave" doors (one per opening cell, also on the leaf cell),
-- the leaf door only carries the animation. While the leaf moves, collision follows it cell by cell
-- (pessimistically, a cell is released only after the leaf cleared it and blocked before it arrives):
--   opening: opening cell k is released when the leaf moved k cells; pocket cell j is blocked when the leaf
--            is about to enter it
--   closing: the mirror image
-- Progress uses the engine's rate. Singleplayer finishes with the render flag;
-- dedicated servers finish by elapsed clip time. A persistent "moving" mark
-- so a gate left in an intermediate state by a save/crash is completed (opened or closed) at game start.
local ANIM_SPEED = 1.5     -- IsoObjectAnimations track speed
local EPS = 1e-6
local moving = {}          -- id -> { opening, t, width, typeId, x, y, z }
local unresolved = {}      -- ids whose parts were not loaded when the game started
local tickCount = 0

-- Kahlua has no global next(): emptiness check via pairs
local function hasEntries(t)
    for _ in pairs(t) do return true end
    return false
end

local function isPaused()
    if isServer() then return false end
    local sc = UIManager.getSpeedControls()
    return sc and sc:getCurrentGameSpeed() == 0
end

local function entryOf(id)
    local e = registry()[id]
    if type(e) ~= "table" then e = { width = 2 }; registry()[id] = e end
    return e
end

-- parts of the gate indexed by cell number k (cell x0-k): slaves[k], blockers[k]
local function indexParts(id)
    local x, y = parseId(id)
    local slaves, blockers, colliders = {}, {}, {}
    for _, o in ipairs(SGGate.parts(id)) do
        local role, sq = o:getModData().sgRole, o:getSquare()
        if sq then
            local k = SGGate.orientation(id) == "W" and sq:getY() - y or x - sq:getX()
            if role == "slave" then slaves[k] = o
            elseif role == "block" then blockers[k] = o
            elseif role == "collider" then colliders[k] = o end
        end
    end
    return slaves, blockers, colliders
end

local function setCollider(colliders, id, x, y, z, k, present)
    local o = colliders[k]
    if present and not o then
        local sq = gateCell(id, x, y, z, k)
        if sq then
            local obj = IsoObject.new(getWorld():getCell(), sq, SGGate.orientation(id) == "W" and "fixtures_doors_fences_01_38" or PHYSICS_SPRITE_N)
            obj:setSpriteModelName("Base.SG_Hidden")
            tag(obj, id, "collider", { sgStatic = "SG_Hidden" })
            sq:AddTileObject(obj)
            sq:RecalcAllWithNeighbours(true)
            colliders[k] = obj
            transmitNew(obj)
        end
    elseif not present and o then
        removeObj(o)
        colliders[k] = nil
    end
end

local function setSlave(slaves, k, open)
    local o = slaves[k]
    if o and o:IsOpen() ~= open then
        if isServer() then
            -- Collision proxies are controlled by the assembly, not vehicle door checks.
            o:ToggleDoorSilent()
            o:getSquare():RecalcAllWithNeighbours(true)
            o:sync()
        else toggleDoor(o) end
    end
end

local function setBlocker(blockers, id, typeId, x, y, z, k, present)
    local o = blockers[k]
    if present and not o then
        local sq = gateCell(id, x, y, z, k)
        local north = gateNeighbour(id, sq)
        if sq and north then
            local pair = sq:isBlockedTo(north) and opaquePair(id) or nil
            blockers[k] = makeDoor(sq, typeId, id, "block", "SG_Hidden", pair)
        end
    elseif not present and o then
        removeObj(o)
        blockers[k] = nil
    end
end

-- Apply the final collision state of an idle gate (idempotent).
local function finalize(id)
    local leaf = findRole(id, "leaf")
    if not leaf then return false end
    local x, y, z = parseId(id)
    local md = leaf:getModData()
    local open = md.sgOpen or false
    local width = gateWidth(id)
    -- A leaf can load before the rest of its assembly across a chunk boundary.
    -- Keep the recovery marker until every required square and opening door exists.
    for k = 0, 2 * width do
        if not gateCell(id, x, y, z, k) or not gateNeighbour(id, gateCell(id, x, y, z, k)) then return false end
    end
    local slaves, blockers, colliders = indexParts(id)
    for k = 1, width do if not slaves[k] then return false end end
    -- the leaf door and its model pose must match the target too (silent fix: no animation, no sound)
    if leaf:IsOpen() ~= open then
        leaf:ToggleDoorSilent()
        leaf:getSquare():RecalcAllWithNeighbours(true)
        if isServer() then leaf:sync() end
        log("gate " .. id .. ": leaf state corrected")
    end
    SGGate.applyModel(leaf)
    for k = 1, width do
        setSlave(slaves, k, open)
        setCollider(colliders, id, x, y, z, k, not open)
    end
    for k = width + 1, 2 * width do
        setBlocker(blockers, id, md.sgType, x, y, z, k, open)
        local b = blockers[k]
        setCollider(colliders, id, x, y, z, k, b ~= nil and not b:getModData().sgOpaque)
    end
    md.sgSlavesOpen = open
    md.sgMoving = nil
    entryOf(id).moving = nil
    moving[id] = nil
    if isServer() then leaf:setAnimating(false) end
    publish(id)
    return true
end
SGGate.finalize = finalize

-- collision of every cell for leaf progress p (0..1)
local function applyProgress(id, tr, p)
    tr.progress = p
    local slaves, blockers, colliders = indexParts(id)
    local W = tr.width
    for k = 1, W do
        local open
        if tr.opening then open = p >= k / W - EPS else open = p < (W - k) / W - EPS end
        setSlave(slaves, k, open)
        setCollider(colliders, id, tr.x, tr.y, tr.z, k, not open)
    end
    for j = 1, W do
        local present
        if tr.opening then present = p >= (j - 1) / W - EPS else present = p < 1 - (j - 1) / W - EPS end
        setBlocker(blockers, id, tr.typeId, tr.x, tr.y, tr.z, W + j, present)
        local b = blockers[W + j]
        setCollider(colliders, id, tr.x, tr.y, tr.z, W + j, b ~= nil and not b:getModData().sgOpaque)
    end
end

-- The tick handler exists only while some gate is moving (or waits for its parts to load): it subscribes
-- when work appears and unsubscribes itself when the work is done, so idle gates cost nothing per frame.
local tickActive = false
local onTick

local function ensureTick()
    if not tickActive then
        tickActive = true
        Events.OnTick.Add(onTick)
    end
end

onTick = function()
    if hasEntries(moving) then
        local ok, delta = pcall(function() return getGameTime():getTimeDelta() end)
        if not ok or type(delta) ~= "number" then delta = 1 / 48 end -- engine value at normal speed
        local step = isPaused() and 0 or delta * ANIM_SPEED
        for id, tr in pairs(moving) do
            local leaf = findRole(id, "leaf")
            if not leaf then
                moving[id] = nil
                unresolved[id] = true
            elseif (isServer() and tr.t >= tr.seconds - EPS) or (not isServer() and not leaf:isAnimating() and tr.t > 0) then
                if finalize(id) then
                    log("gate " .. id .. " settled")
                else
                    moving[id] = nil
                    unresolved[id] = true
                end
            else
                tr.t = tr.t + step
                applyProgress(id, tr, math.min(tr.t / tr.seconds, 1))
            end
        end
    end
    tickCount = tickCount + 1
    if hasEntries(unresolved) and tickCount % 60 == 0 then
        for id, _ in pairs(unresolved) do
            if finalize(id) then unresolved[id] = nil; log("gate " .. id .. " completed after load") end
        end
    end
    if not hasEntries(moving) and not hasEntries(unresolved) then
        tickActive = false
        Events.OnTick.Remove(onTick)
    end
end

local function startMotion(id, leaf, target)
    local x, y, z = parseId(id)
    local md = leaf:getModData()
    md.sgMoving = target
    entryOf(id).moving = target
    local tr = { opening = target, t = 0, seconds = TYPES[md.sgType].clipSeconds, width = gateWidth(id), typeId = md.sgType, x = x, y = y, z = z }
    moving[id] = tr
    applyProgress(id, tr, 0)
    publish(id)
    ensureTick()
end

-- Vanilla refuses to move a door while a vehicle stands in its way and shows "The door is blocked" over the
-- character. A gate needs the cells its leaf will move through to be free of vehicles: the opening cells when
-- closing, the pocket cells when opening (characters do not obstruct doors in vanilla either).
function SGGate.isBlocked(id, opening)
    local x, y, z = parseId(id)
    local W = gateWidth(id)
    local from, to = 1, W
    if opening then from, to = W + 1, 2 * W end
    for k = from, to do
        local sq = gateCell(id, x, y, z, k)
        if not sq or not gateNeighbour(id, gateCell(id, x, y, z, k)) or sq:isVehicleIntersecting() then return true end
    end
    -- The native leaf door checks its own obstruction in BOTH directions. A car
    -- pressed against a closed leaf may obstruct it even with an empty pocket.
    local leaf = findRole(id, "leaf")
    if leaf and leaf:isObstructed() then return true end
    return false
end

local function notifyBlocked(chr)
    chr = chr or getPlayer()
    if chr then chr:setHaloNote(getText("IGUI_PlayerText_DoorBlocked"), 255, 255, 255, 256) end
end

-- Bring all parts of one gate to the same state. Whatever door was toggled (mouse click, E key, menu, zombie)
-- is the request: the leaf follows slave toggles, slaves/blockers follow the motion rules above.
local function syncGate(id)
    local leaf = findRole(id, "leaf")
    if not leaf then return end
    local md = leaf:getModData()
    local lo = leaf:IsOpen()
    local last = md.sgOpen or false
    local slavesOpen = md.sgSlavesOpen or false
    local changed, openBlockers = nil, {}
    if lo ~= last then changed = lo end
    local slaves, blockers = indexParts(id)
    if isServer() and authorizedGate ~= id then
        -- Native door packets (including E-key input) are not authoritative commands.
        -- Restore the accepted target/progress; the client's explicit request is validated separately.
        local corrected = false
        if leaf:IsOpen() ~= last then
            leaf:ToggleDoorSilent()
            leaf:getSquare():RecalcAllWithNeighbours(true)
            leaf:sync()
            corrected = true
        end
        if moving[id] then
            applyProgress(id, moving[id], moving[id].progress or 0)
        else
            for _, o in pairs(slaves) do
                if o:IsOpen() ~= slavesOpen then
                    o:ToggleDoorSilent(); o:getSquare():RecalcAllWithNeighbours(true); o:sync()
                    corrected = true
                end
            end
        end
        for _, o in pairs(blockers) do
            if o:IsOpen() then
                o:ToggleDoorSilent(); o:getSquare():RecalcAllWithNeighbours(true); o:sync()
                corrected = true
            end
        end
        SGGate.applyModel(leaf)
        if corrected and SGGate.onStateChanged then SGGate.onStateChanged(SGGate.snapshot(id)) end
        return
    end
    -- a slave that differs from what we expect is a player toggle only when the gate is idle (not moving)
    if changed == nil and not moving[id] then
        for _, o in pairs(slaves) do
            if o:IsOpen() ~= slavesOpen then changed = o:IsOpen(); break end
        end
    end
    for _, o in pairs(blockers) do if o:IsOpen() then openBlockers[#openBlockers + 1] = o end end
    -- E at the retracted leaf toggles a pocket proxy. It requests closing the
    -- assembly, while the proxy itself remains closed until the leaf clears it.
    if changed == nil and last and #openBlockers > 0 and not SGGate.isMoving(id) then changed = false end
    for _, o in ipairs(openBlockers) do
        o:ToggleDoorSilent()
        o:getSquare():RecalcAllWithNeighbours(true)
        SGGate.applyModel(o)
    end
    if changed == nil then return end
    if changed == last and lo == last then return end
    local target = changed
    print(string.format("[SGGate] toggle request for %s: target open=%s, leaf toggled by engine=%s, vehicle=%s",
        id, tostring(target), tostring(lo ~= last), tostring(getPlayer() and getPlayer():getVehicle() ~= nil)))
    local function rejectRequest()
        -- refused: undo the toggle the engine already did on the leaf door (no animation) and tell the player
        if leaf:IsOpen() ~= last then
            leaf:ToggleDoorSilent()
            leaf:getSquare():RecalcAllWithNeighbours(true)
            if isServer() then leaf:sync() end
        end
        -- a refused request may also come from a slave toggled by the engine (E key on the nearest door): put every
        -- slave back to its expected state, silently (a normal toggle would be refused by the vehicle again)
        for _, o in pairs(slaves) do
            if o:IsOpen() ~= slavesOpen then
                o:ToggleDoorSilent()
                o:getSquare():RecalcAllWithNeighbours(true)
                if isServer() then o:sync() end
            end
        end
        SGGate.applyModel(leaf)
        notifyBlocked()
    end
    if SGGate.isBlocked(id, target) then
        rejectRequest()
        return
    end
    if lo ~= target and not toggleDoor(leaf) then
        -- A slave may have opened while the engine refused the master door.
        -- Never persist a target or start recovery for a move that did not happen.
        rejectRequest()
        return
    end
    SGGate.applyModel(leaf)
    md.sgOpen = target
    startMotion(id, leaf, target)
    log("gate " .. id .. (target and " opening" or " closing"))
end

-- a save/crash mid-motion leaves slaves/blockers in an intermediate state: complete such gates at start
-- (gates whose parts are not loaded yet are retried until they are)
local function recover()
    recoveryReady = true
    for square in pairs(deferredSquares) do cleanupSquare(square) end
    deferredSquares = {}
    for id, e in pairs(registry()) do
        SGGate.ensureIdentity(id)
        for _, part in ipairs(SGGate.parts(id)) do
            local md, entry = part:getModData(), SGGate.ensureIdentity(id)
            if not md.sgInstance then md.sgInstance, md.sgWidth, md.sgOrientation = entry.instance, entry.width, entry.orientation end
        end
        if type(e) == "table" and e.moving ~= nil then
            local ok, done = pcall(finalize, id)
            if not (ok and done) then unresolved[id] = true; ensureTick() end
        end
    end
end
Events.OnGameStart.Add(recover)
Events.OnServerStarted.Add(recover)

-- Destruction: when any door part of a gate is destroyed (zombies, weapons, vehicles) the whole gate falls apart and
-- drops part of its materials (50% per unit, like vanilla thumpables). Every part has the full gate health.
function SGGate.destroyGate(id, destroyer, dropPercent)
    -- Multiple parts/events can report the same destruction. Claim the registry entry only once.
    if registry()[id] == nil then return false end
    local leaf = findRole(id, "leaf")
    local x, y, z = parseId(id)
    local dropSq = (leaf and leaf:getSquare()) or gateCell(id, x, y, z, 1)
    local entry = registry()[id]
    local identity = SGGate.ensureIdentity(id)
    local instance, revision = identity.instance, identity.revision
    local typeId = (leaf and leaf:getModData().sgType) or (type(entry) == "table" and entry.type) or nil
    if not typeId then
        -- gates built before the type was recorded: derive it from any remaining door part, else from the width
        for _, o in ipairs(SGGate.parts(id)) do
            if o:getModData().sgType then typeId = o:getModData().sgType; break end
        end
        typeId = typeId or (gateWidth(id) == 4 and "chainlink4" or "chainlink")
    end
    local parts = SGGate.parts(id)
    moving[id] = nil
    unresolved[id] = nil
    registry()[id] = nil
    for _, o in ipairs(parts) do removeObj(o) end
    if dropSq and typeId and TYPES[typeId] then
        for itemType, count in pairs(TYPES[typeId].materials) do
            local recovered = 0
            for _ = 1, count do
                if ZombRand(100) < (dropPercent or 50) then recovered = recovered + 1 end
            end
            if itemType == "Base.Wire" then
                -- Recipe quantities are uses, not coils. Set charge BEFORE placing the item in the world.
                if recovered > 0 then
                    local wire = instanceItem(itemType)
                    if wire then
                        wire:setUsedDelta(math.min(1, recovered * wire:getUseDelta()))
                        dropSq:AddWorldInventoryItem(wire, 0.0, 0.0, 0.0)
                    end
                end
            else
                for _ = 1, recovered do dropSq:AddWorldInventoryItem(itemType, 0.0, 0.0, 0.0) end
            end
        end
    end
    log("gate " .. id .. (dropPercent and " dismantled" or " destroyed"))
    if SGGate.onRemoved then SGGate.onRemoved(id, instance, revision + 1) end
    return true
end

Events.OnDestroyIsoThumpable.Add(function(thump, player)
    local d = thump:getModData()
    if d and d.sgGate and registry()[d.sgGate] ~= nil then SGGate.destroyGate(d.sgGate, player) end
end)

local reconciling = false
function SGGate.reconcile()
    if reconciling or removingParts > 0 then return end
    reconciling = true
    local ok, err = pcall(function() for id, _ in pairs(registry()) do syncGate(id) end end)
    reconciling = false
    if not ok then print("[SGGate] reconcile error: " .. tostring(err)) end
end
Events.OnContainerUpdate.Add(SGGate.reconcile)

function SGGate.isMoving(id)
    local leaf = findRole(id, "leaf")
    return moving[id] ~= nil or unresolved[id] ~= nil or (not isServer() and leaf ~= nil and leaf:isAnimating())
end

-- open/close from code (menu, remote): toggling the leaf triggers the sync above
function SGGate.toggle(id, player)
    local leaf = findRole(id, "leaf")
    if not leaf then log("gate parts missing for " .. id); return end
    if SGGate.isMoving(id) then log("gate " .. id .. " is moving"); return end
    if SGGate.isBlocked(id, not leaf:IsOpen()) then notifyBlocked(); return false end
    requestPlayer, authorizedGate = player, id
    local ok, result = pcall(toggleDoor, leaf)
    requestPlayer, authorizedGate = nil, nil
    if not ok then error(result) end
    return result
end

function SGGate.remove(id)
    local identity = SGGate.ensureIdentity(id)
    moving[id] = nil
    unresolved[id] = nil
    local parts = SGGate.parts(id) -- retain width before deleting its registry entry
    registry()[id] = nil
    for _, o in ipairs(parts) do removeObj(o) end
    log("gate removed " .. id)
    if identity and SGGate.onRemoved then SGGate.onRemoved(id, identity.instance, identity.revision + 1) end
end

cleanupSquare = function(square)
    local stale = {}
    local objects = square:getObjects()
    for i = 0, objects:size() - 1 do
        local obj = objects:get(i)
        local md = obj:getModData()
        if md.sgGate then
            if not recoveryReady then deferredSquares[square] = true; return end
            local entry = SGGate.ensureIdentity(md.sgGate)
            if not entry or (md.sgInstance and md.sgInstance ~= entry.instance) then
                stale[#stale + 1] = obj
            else
                -- Upgrade legacy saves and restore each model after native deserialization.
                md.sgInstance, md.sgWidth, md.sgOrientation = entry.instance, entry.width, entry.orientation
                if md.sgRole == "leaf" then md.sgRevision = entry.revision end
                SGGate.applyModel(obj)
            end
        end
    end
    -- Destroyed/unloaded parts must not reappear later, and never produce extra loot.
    for _, obj in ipairs(stale) do removeObj(obj) end
end
Events.LoadGridsquare.Add(cleanupSquare)

-- Debug collision along the assembly edge, including the pocket.
function SGGate.dumpCollision(id)
    local x, y, z = parseId(id)
    local orientation = SGGate.orientation(id)
    local edge = orientation == "W" and IsoDirections.W or IsoDirections.N
    for k = -1, 2 * gateWidth(id) + 1 do
        local sq = gateCell(id, x, y, z, k)
        local neighbour = gateNeighbour(id, sq)
        if sq and neighbour then
            log(string.format("cell %d (%s): blocked=%s closedDoor=%s openDoor=%s", k, orientation,
                tostring(sq:isBlockedTo(neighbour)), tostring(sq:hasClosedDoorOnEdge(edge)),
                tostring(sq:hasOpenDoorOnEdge(edge))))
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
    if test or not isDebugEnabled() then return end
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
