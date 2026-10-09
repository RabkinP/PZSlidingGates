require "SG_GateCommon"
require "SG_GateMotor"
if not isClient() then return end

local states, pending, snapshotAt = {}, {}, {}
local requestSerial = 0
local applying = false

local function stateOf(id)
    local leaf = SGGate.findRole(id, "leaf")
    if not leaf then return end
    local md = leaf:getModData()
    if states[id] and states[id].removed then return end
    return states[id] or { id = id, instance = md.sgInstance, revision = md.sgRevision,
        width = md.sgWidth or 2, orientation = md.sgOrientation or "N", direction = md.sgDirection or "forward", type = md.sgType, open = md.sgOpen or false,
        moving = md.sgMoving ~= nil, slavesOpen = md.sgSlavesOpen or false }
end

local function requestSnapshot(id, player)
    local now = getTimestampMs()
    if snapshotAt[id] and now - snapshotAt[id] < 1000 then return end
    player = player or getPlayer()
    if not player then return end
    snapshotAt[id] = now
    sendClientCommand(player, "SlidingGates", "snapshot", { id = id })
end

function SGGate.isMoving(id)
    local queued = pending[id]
    if queued and getTimestampMs() - queued.time > 5000 then
        pending[id] = nil
        requestSnapshot(id)
    end
    local state = stateOf(id)
    return pending[id] ~= nil or (state ~= nil and state.moving == true)
end

local function requestDesired(id, open, player)
    local state = stateOf(id)
    if not state or pending[id] or state.moving then return false end
    if not state.instance or not state.revision then requestSnapshot(id, player); return false end
    player = player or getPlayer()
    if not player or (SGGate.distanceTo(player, id) or 99) > 3 then return false end
    requestSerial = requestSerial + 1
    pending[id] = { time = getTimestampMs(), request = requestSerial }
    sendClientCommand(player, "SlidingGates", "toggle", {
        id = id, instance = state.instance, revision = state.revision,
        open = open, request = requestSerial,
    })
    return true
end

function SGGate.toggle(id, player)
    local state = stateOf(id)
    if not state or SGGate.isMoving(id) then return false end
    return requestDesired(id, not state.open, player)
end

function SGGate.requestRemote(id, player, remoteId, driveIdentity)
    local state = stateOf(id)
    if not state or pending[id] or state.moving then return false end
    if not state.instance or not state.revision then requestSnapshot(id, player); return false end
    requestSerial = requestSerial + 1
    pending[id] = { time = getTimestampMs(), request = requestSerial }
    sendClientCommand(player, "SlidingGates", "remote", { id = id, instance = state.instance,
        revision = state.revision, open = not state.open, request = requestSerial,
        remoteId = remoteId, driveIdentity = driveIdentity })
    return true
end

local function receiveState(state, snapshot)
    if type(state) ~= "table" or not SGGate.parseId(state.id) then return end
    local known = states[state.id]
    local leaf = SGGate.findRole(state.id, "leaf")
    local md = leaf and leaf:getModData()
    local instance = (known and known.instance) or (md and md.sgInstance)
    local revision = (known and known.revision) or (md and md.sgRevision) or -1
    if instance and (state.instance < instance or (state.instance == instance and state.revision < revision)) then return end
    if known and known.removed and state.instance == known.instance and state.revision <= known.revision then return end
    if (known and known.instance ~= state.instance) or not state.moving or not state.motor then
        SGGateMotor.stop(state.id)
    end
    states[state.id] = state
    SGGate.registry()[state.id] = { width = state.width, type = state.type, orientation = state.orientation or "N", direction = state.direction or "forward",
        instance = state.instance, revision = state.revision }
    if not leaf or (md.sgInstance and md.sgInstance ~= state.instance) then return end
    applying = true
    md.sgOpen, md.sgSlavesOpen = state.open, state.slavesOpen
    -- false is a meaningful closing marker, not absence of motion.
    if state.moving then md.sgMoving = state.open else md.sgMoving = nil end
    md.sgInstance, md.sgRevision, md.sgWidth = state.instance, state.revision, state.width
    md.sgOrientation = state.orientation or "N"
    md.sgDirection = state.direction or "forward"
    SGGateMotor.sync(state)
    local restingSnapshot = snapshot and not (known and known.instance == state.instance and known.moving)
    if restingSnapshot and leaf:IsOpen() ~= state.open then
        leaf:ToggleDoorSilent()
        leaf:getSquare():RecalcAllWithNeighbours(true)
    end
    -- Native IsoThumpable sync packets play Open/Close. Do not pre-toggle the
    -- leaf before such a packet: that would suppress its animation.
    if restingSnapshot or leaf:IsOpen() == state.open then SGGate.applyModel(leaf) end
    applying = false
end

Events.OnServerCommand.Add(function(module, command, args)
    if module ~= "SlidingGates" or type(args) ~= "table" then return end
    if command == "state" or command == "snapshot" then
        receiveState(args, command == "snapshot")
    elseif command == "result" then
        local queued = pending[args.id]
        if queued and queued.request == args.request then pending[args.id] = nil end
        if args.state then receiveState(args.state, false) end
        if args.remote and not args.accepted and SGGateRemote then
            SGGateRemote.message(getPlayer(), args.reason)
        elseif args.reason == "blocked" then
            local player = getPlayer()
            if player then player:setHaloNote(getText("IGUI_PlayerText_DoorBlocked"), 255, 255, 255, 256) end
        end
    elseif command == "removed" then
        local state = states[args.id]
        if state and state.instance == args.instance and args.revision >= state.revision then
            states[args.id] = { instance = args.instance, revision = args.revision, removed = true }
            pending[args.id] = nil
            SGGate.registry()[args.id] = nil
            SGGateMotor.stop(args.id)
        end
    end
end)

-- Java E-key input uses a native door packet. The server restores that prediction
-- and accepts only the explicit, validated desired-state request below.
Events.OnContainerUpdate.Add(function()
    if applying then return end
    for id in pairs(SGGate.registry()) do
        local state = stateOf(id)
        if state then
            local leaf = SGGate.findRole(id, "leaf")
            if leaf and not state.moving and leaf:IsOpen() ~= state.open then
                requestDesired(id, leaf:IsOpen())
            elseif not state.moving then
                for _, part in ipairs(SGGate.parts(id)) do
                    local role = part:getModData().sgRole
                    if role == "slave" and part:IsOpen() ~= state.slavesOpen then
                        requestDesired(id, part:IsOpen()); break
                    elseif role == "block" and state.open and part:IsOpen() then
                        requestDesired(id, false); break
                    end
                end
            end
            if leaf and leaf:IsOpen() == state.open then SGGate.applyModel(leaf) end
        end
    end
end)

Events.LoadGridsquare.Add(function(square)
    local objects, seen = square:getObjects(), {}
    for i = 0, objects:size() - 1 do
        local obj = objects:get(i)
        local md = obj:getModData()
        if md.sgGate then
            local entry = SGGate.registry()[md.sgGate]
            if type(entry) ~= "table" then
                SGGate.registry()[md.sgGate] = { width = md.sgWidth or 2, orientation = md.sgOrientation or "N", direction = md.sgDirection or "forward", instance = md.sgInstance }
            else
                entry.orientation = entry.orientation or md.sgOrientation or "N"
                entry.direction = entry.direction or md.sgDirection or "forward"
            end
            -- Restore model names even before the requested resting snapshot arrives.
            if md.sgBase or md.sgStatic then SGGate.applyModel(obj) end
            if not seen[md.sgGate] then
                seen[md.sgGate] = true
                local state = stateOf(md.sgGate)
                if state then SGGate.registry()[md.sgGate] = { width = state.width, orientation = state.orientation or "N", direction = state.direction or "forward", instance = state.instance } end
                requestSnapshot(md.sgGate)
            end
        end
    end
end)

Events.OnGameStart.Add(function()
    states, pending, snapshotAt = {}, {}, {}
    for id in pairs(SGGate.registry()) do requestSnapshot(id) end
end)

local pollTicks = 0
Events.OnTick.Add(function()
    SGGateMotor.update()
    pollTicks = pollTicks + 1
    if pollTicks % 120 ~= 0 then return end
    -- Refresh only locally loaded moving/pending gates, including after a lost result.
    for id in pairs(SGGate.registry()) do
        local state = stateOf(id)
        if pending[id] or (state and state.moving) then
            SGGate.isMoving(id)
            requestSnapshot(id)
        end
    end
end)
