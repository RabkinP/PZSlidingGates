require "SG_GatePower"
if not isClient() then require "SG_GateCore" end

SGGateRemote = {}
SGGateRemote.itemType = "SlidingGates.GateRemote"
SGGateRemote.range = 20

local function walkItems(container, result)
    local items = container:getItems()
    for i = 0, items:size() - 1 do
        local item = items:get(i)
        if item:getFullType() == SGGateRemote.itemType then result[#result + 1] = item end
        if instanceof(item, "InventoryContainer") then walkItems(item:getInventory(), result) end
    end
    return result
end

function SGGateRemote.items(character)
    return character and walkItems(character:getInventory(), {}) or {}
end

function SGGateRemote.owned(character, itemId)
    if type(itemId) ~= "number" then return end
    for _, item in ipairs(SGGateRemote.items(character)) do
        if item:getID() == itemId and not item:isBroken() then return item end
    end
end

function SGGateRemote.distanceSquared(character, drive)
    local square = drive and drive:getSquare()
    local playerSquare = character and character:getCurrentSquare()
    if not square or not playerSquare or square:getZ() ~= playerSquare:getZ() then return end
    return (character:getX()-square:getX()-0.5)^2 + (character:getY()-square:getY()-0.5)^2
end

local function linked(item, drive)
    if not item or not drive or item:isBroken() then return false end
    local imd, dmd = item:getModData(), drive:getModData()
    local allowed = dmd.sgDriveData and dmd.sgDriveData.sgRemotes
    return imd.sgRemoteDrive ~= nil and imd.sgRemoteDrive == dmd.sgDriveIdentity
        and imd.sgRemoteKey ~= nil and allowed ~= nil and allowed[imd.sgRemoteKey] == item:getID()
end
SGGateRemote.linked = linked

function SGGateRemote.checkPair(character, id, instance, itemId, driveIdentity, checkDistance)
    local item = SGGateRemote.owned(character, itemId)
    if not item or not character or character:isDead() then return false, "unavailable" end
    local leaf, drive = SGGate.findRole(id, "leaf"), SGGate.findRole(id, "drive")
    if not leaf or not drive then return false, "missing" end
    if leaf:getModData().sgInstance ~= instance or drive:getModData().sgDriveIdentity ~= driveIdentity then
        return false, "instance"
    end
    if SGGate.isMoving(id) then return false, "busy" end
    local distance = SGGateRemote.distanceSquared(character, drive)
    if not distance or (checkDistance ~= false and distance > 4) then return false, "distance" end
    return true, nil, item, drive
end

function SGGateRemote.pair(character, id, instance, itemId, driveIdentity)
    if isClient() then return false end
    local valid, _, item, drive = SGGateRemote.checkPair(character, id, instance, itemId, driveIdentity)
    if not valid then return false end
    local data, imd, dmd = ModData.getOrCreate("SlidingGates"), item:getModData(), drive:getModData()
    if imd.sgRemoteKey then
        -- Revoke the old association when its drive is currently loaded.
        for gateId in pairs(SGGate.registry()) do
            local old = SGGate.findRole(gateId, "drive")
            local oldData = old and old:getModData()
            if oldData and oldData.sgDriveIdentity == imd.sgRemoteDrive and oldData.sgDriveData
                and oldData.sgDriveData.sgRemotes then
                oldData.sgDriveData.sgRemotes[imd.sgRemoteKey] = nil
                old:flagForHotSave()
                if isServer() then old:transmitModData() end
            end
        end
    else
        data.remoteSerial = (data.remoteSerial or 0) + 1
        imd.sgRemoteKey = "remote:" .. data.remoteSerial
    end
    dmd.sgDriveData = dmd.sgDriveData or { sgDriveIdentity = dmd.sgDriveIdentity }
    dmd.sgDriveData.sgRemotes = dmd.sgDriveData.sgRemotes or {}
    dmd.sgDriveData.sgRemotes[imd.sgRemoteKey] = item:getID()
    imd.sgRemoteDrive = dmd.sgDriveIdentity
    drive:flagForHotSave()
    if isServer() then drive:transmitModData(); item:syncItemFields() end
    return true
end

-- Choose the nearest loaded gate with a matching carried remote. Do not skip a
-- busy/unpowered gate and unexpectedly operate a farther one instead.
function SGGateRemote.nearest(character, selectedItem)
    if not character or character:isDead() then return end
    local items = selectedItem and { selectedItem } or SGGateRemote.items(character)
    local bestId, bestItem, bestDistance
    local playerSquare = character:getCurrentSquare()
    if not playerSquare then return end
    for id, entry in pairs(SGGate.registry()) do
        local x, y, z = SGGate.parseId(id)
        local bound = SGGateRemote.range + (type(entry) == "table" and entry.width or 2) + 0.5
        -- Avoid scanning world parts for every distant/unloaded gate in a large save.
        if x and z == playerSquare:getZ() and math.abs(character:getX()-x) <= bound
            and math.abs(character:getY()-y) <= bound then
            local drive = SGGate.findRole(id, "drive")
            local distance = SGGateRemote.distanceSquared(character, drive)
            if distance and distance <= SGGateRemote.range^2 and (not bestDistance or distance < bestDistance
                or (distance == bestDistance and id < bestId)) then
                for _, item in ipairs(items) do
                    if linked(item, drive) then bestId, bestItem, bestDistance = id, item, distance; break end
                end
            end
        end
    end
    return bestId, bestItem
end

function SGGateRemote.checkUse(character, id, instance, itemId, driveIdentity)
    local item = SGGateRemote.owned(character, itemId)
    local drive = SGGate.findRole(id, "drive")
    if not item or not drive or drive:getModData().sgDriveIdentity ~= driveIdentity or not linked(item, drive) then
        return false, "unavailable"
    end
    return SGGatePower.check(character, id, instance, true, SGGateRemote.range)
end

function SGGateRemote.handleRequest(character, args)
    if isClient() or type(args) ~= "table" or not SGGate.parseId(args.id)
        or type(args.open) ~= "boolean" then return false, "invalid" end
    local state = SGGate.snapshot(args.id)
    if not state then return false, "missing" end
    local valid, reason = SGGateRemote.checkUse(character, args.id, args.instance, args.remoteId, args.driveIdentity)
    if not valid then return false, reason end
    if args.open == state.open then return true, "unchanged" end
    if args.revision ~= state.revision then return false, "stale" end
    if not SGGatePower.complete(character, args.id, args.instance, args.open, SGGateRemote.range) then
        return false, "blocked"
    end
    return true, "accepted"
end

function SGGateRemote.message(character, reason)
    if not character then return end
    local key = "Tooltip_SG_RemoteUnavailable"
    if reason == "blocked" then key = "IGUI_PlayerText_DoorBlocked"
    elseif reason == "power" or reason == "busy" then key = "Tooltip_SG_Drive_" .. reason end
    character:setHaloNote(getText(key), 255, 255, 255, 256)
end

-- Inventory and hotkey entry points share this exact activation path.
function SGGateRemote.activate(character, selectedItem)
    local id, item = SGGateRemote.nearest(character, selectedItem)
    local leaf, drive = id and SGGate.findRole(id, "leaf"), id and SGGate.findRole(id, "drive")
    if not leaf or not drive or not item then SGGateRemote.message(character, "unavailable"); return false end
    local instance, driveIdentity = leaf:getModData().sgInstance, drive:getModData().sgDriveIdentity
    local valid, reason = SGGateRemote.checkUse(character, id, instance, item:getID(), driveIdentity)
    if not valid then SGGateRemote.message(character, reason); return false end
    if isClient() then return SGGate.requestRemote(id, character, item:getID(), driveIdentity) end
    local state = SGGate.snapshot(id)
    local accepted, failure = SGGateRemote.handleRequest(character, { id = id, instance = instance,
        revision = state.revision, open = not state.open, remoteId = item:getID(), driveIdentity = driveIdentity })
    if not accepted then SGGateRemote.message(character, failure) end
    return accepted
end
