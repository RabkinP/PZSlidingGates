-- SlidingGates: manual open/close through the vanilla timed-action queue.
-- Mouse click on a gate door and the door context menu queue ISSlidingGateToggle instead of ISOpenCloseDoor.
-- The action waits (waitToStart) until the leaf finished its animation, so any number of clicks run one
-- after another, each as a full animation. When the action finally starts it checks that the character is
-- still close to the gate; if they walked away, nothing happens.
-- (The E key toggles the door from Java and does not go through this queue.)

require "TimedActions/ISBaseTimedAction"

ISSlidingGateToggle = ISBaseTimedAction:derive("ISSlidingGateToggle")

local MAX_DISTANCE = 3.0 -- tiles from the character to the nearest gate door cell

function ISSlidingGateToggle:isValid()
    local d = SGGate.distanceTo(self.character, self.gateId)
    return d ~= nil and d <= MAX_DISTANCE
end

function ISSlidingGateToggle:isValidStart()
    return self:isValid()
end

-- hold the action in the queue while the previous open/close is still animating
function ISSlidingGateToggle:waitToStart()
    return SGGate.isMoving(self.gateId)
end

function ISSlidingGateToggle:update() end

function ISSlidingGateToggle:start() end

function ISSlidingGateToggle:stop()
    ISBaseTimedAction.stop(self)
end

function ISSlidingGateToggle:perform()
    ISBaseTimedAction.perform(self)
end

function ISSlidingGateToggle:complete()
    SGGate.toggle(self.gateId)
    return true
end

function ISSlidingGateToggle:getDuration()
    return 0
end

function ISSlidingGateToggle:new(character, gateId)
    local o = ISBaseTimedAction.new(self, character)
    o.gateId = gateId
    o.stopOnWalk = false
    o.stopOnRun = false
    o.stopOnAim = false
    o.ignoreHandsWounds = true
    o.maxTime = o:getDuration()
    return o
end

local function queue(playerObj, gateId)
    ISTimedActionQueue.addGetUpAndThen(playerObj, ISSlidingGateToggle:new(playerObj, gateId))
end

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
