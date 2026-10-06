require "SG_GateToggleAction"

local MAX_DISTANCE = 3.0

local function queue(playerObj, gateId)
    ISTimedActionQueue.addGetUpAndThen(playerObj, ISSlidingGateToggle:new(playerObj, gateId))
end

-- ISObjectClickHandler lives in lua/server (loaded after client files): wrap the click handlers once everything is loaded.
local function install()
    if ISSlidingGateToggle.hooked then return end
    ISSlidingGateToggle.hooked = true
    -- mouse click on a door-thumpable
    if ISObjectClickHandler and ISObjectClickHandler.doClickThumpable then
        local original = ISObjectClickHandler.doClickThumpable
        function ISObjectClickHandler.doClickThumpable(object, playerNum, playerObj)
            local gateId = object:getModData().sgGate
            if not gateId then return original(object, playerNum, playerObj) end
            if object:getSquare():getZ() ~= playerObj:getCurrentSquare():getZ() then return false end
            if (SGGate.distanceTo(playerObj, gateId) or 99) > MAX_DISTANCE then return false end
            CancelAction(playerNum, true)
            queue(playerObj, gateId)
            return true
        end
    end

    -- "Open door" / "Close door" in the world context menu
    if ISWorldObjectContextMenu and ISWorldObjectContextMenu.onOpenCloseDoor then
        local original = ISWorldObjectContextMenu.onOpenCloseDoor
        function ISWorldObjectContextMenu.onOpenCloseDoor(worldobjects, door, player)
            local gateId = door:getModData().sgGate
            if not gateId then return original(worldobjects, door, player) end
            local playerObj = getSpecificPlayer(player)
            CancelAction(player, true)
            if luautils.walkAdjWindowOrDoor(playerObj, door:getSquare(), door) then
                queue(playerObj, gateId)
            end
        end
    end
end

Events.OnGameBoot.Add(install)
Events.OnGameStart.Add(install)
