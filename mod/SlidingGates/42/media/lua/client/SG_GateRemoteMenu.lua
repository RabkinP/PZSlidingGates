require "SG_Gate"
require "SG_GateRemoteAction"
require "TimedActions/ISTimedActionQueue"

local function queuePair(character, id, instance, remoteId, driveIdentity)
    local drive = SGGate.findRole(id, "drive")
    if drive and luautils.walkAdj(character, drive:getSquare()) then
        ISTimedActionQueue.add(ISSlidingGateRemotePair:new(character, id, instance, remoteId, driveIdentity))
    end
end

Events.OnFillWorldObjectContextMenu.Add(function(player, context, worldObjects, test)
    if test then return end
    local character, seen = getSpecificPlayer(player), {}
    if not character then return end
    local items = SGGateRemote.items(character)
    if #items == 0 then return end
    for _, object in ipairs(worldObjects) do
        local md = object and object.getModData and object:getModData()
        local id = md and md.sgGate
        if id and not seen[id] then
            seen[id] = true
            local drive, leaf = SGGate.findRole(id, "drive"), SGGate.findRole(id, "leaf")
            if drive and leaf and drive:getModData().sgDriveIdentity then
                local option = context:addOption(getText("ContextMenu_SG_LinkRemote"))
                local menu = context:getNew(context)
                context:addSubMenu(option, menu)
                for i, item in ipairs(items) do
                    local instance, token = leaf:getModData().sgInstance, drive:getModData().sgDriveIdentity
                    local child = menu:addOption(item:getName() .. " (" .. i .. ")", character,
                        queuePair, id, instance, item:getID(), token)
                    child.notAvailable = not SGGateRemote.checkPair(character, id, instance, item:getID(), token, false)
                end
            end
        end
    end
end)

Events.OnFillInventoryObjectContextMenu.Add(function(player, context, items)
    local character, seen = getSpecificPlayer(player), {}
    if not character then return end
    for _, entry in ipairs(items) do
        local item = entry.items and entry.items[1] or entry
        if item and item.getFullType and item:getFullType() == SGGateRemote.itemType and not seen[item:getID()] then
            seen[item:getID()] = true
            context:addOption(getText("ContextMenu_SG_UseRemote"), character, SGGateRemote.activate, item)
        end
    end
end)
