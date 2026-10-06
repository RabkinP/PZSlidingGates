-- SlidingGates: manual open/close through the vanilla timed-action queue.
-- Mouse click on a gate door and the door context menu queue ISSlidingGateToggle instead of ISOpenCloseDoor.
-- The action waits (waitToStart) until the leaf finished its animation, so any number of clicks run one
-- after another, each as a full animation. When the action finally starts it checks that the character is
-- still close to the gate; if they walked away, nothing happens.
-- (The E key toggles the door from Java and does not go through this queue.)

require "TimedActions/ISBaseTimedAction"
require "SG_GateCommon"

ISSlidingGateToggle = ISBaseTimedAction:derive("ISSlidingGateToggle")

local MAX_DISTANCE = 3.0 -- tiles from the character to the nearest gate door cell

function ISSlidingGateToggle:isValid()
    local leaf = SGGate.findRole(self.gateId, "leaf")
    if not leaf or leaf:getModData().sgInstance ~= self.instance then return false end
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
    if isClient() and self:isValid() then SGGate.toggle(self.gateId, self.character) end
    ISBaseTimedAction.perform(self)
end

function ISSlidingGateToggle:complete()
    -- MP uses the explicit versioned command sent by perform; native completion
    -- must not also toggle the gate on the server.
    if isClient() or isServer() then return true end
    print("[SGGate] queued action runs for gate " .. tostring(self.gateId))
    SGGate.toggle(self.gateId, self.character)
    return true
end

function ISSlidingGateToggle:getDuration()
    return 0
end

function ISSlidingGateToggle:new(character, gateId, instance)
    local o = ISBaseTimedAction.new(self, character)
    o.gateId = gateId
    local leaf = SGGate.findRole(gateId, "leaf")
    o.instance = instance or (leaf and leaf:getModData().sgInstance)
    o.stopOnWalk = false
    o.stopOnRun = false
    o.stopOnAim = false
    o.ignoreHandsWounds = true
    o.maxTime = o:getDuration()
    return o
end
