require "TimedActions/ISBaseTimedAction"
require "SG_GateDrive"

ISSlidingGateDrive = ISBaseTimedAction:derive("ISSlidingGateDrive")

function ISSlidingGateDrive:isValid()
    return SGGateDrive.check(self.character, self.gateId, self.instance, self.installing)
end

function ISSlidingGateDrive:isValidStart() return self:isValid() end

function ISSlidingGateDrive:waitToStart()
    local sq = SGGateDrive.square(self.gateId)
    if sq then self.character:faceLocation(sq:getX(), sq:getY()) end
    return self.character:shouldBeTurning()
end

function ISSlidingGateDrive:start()
    self:setActionAnim("Loot")
    self.character:SetVariable("LootPosition", "Low")
    self.character:reportEvent("EventLootItem")
end

function ISSlidingGateDrive:update()
    local sq = SGGateDrive.square(self.gateId)
    if sq then self.character:faceLocation(sq:getX(), sq:getY()) end
end

function ISSlidingGateDrive:stop() ISBaseTimedAction.stop(self) end
function ISSlidingGateDrive:perform() ISBaseTimedAction.perform(self) end

function ISSlidingGateDrive:complete()
    -- The native B42 timed-action transaction invokes complete on the authority.
    -- There is no separate client command to race or duplicate this completion.
    return SGGateDrive.complete(self.character, self.gateId, self.instance, self.installing)
end

function ISSlidingGateDrive:getDuration()
    if self.character:isTimedActionInstant() then return 1 end
    return self.installing and 180 or 120
end

-- Named primitive parameters are reconstructed by B42 NetTimedActionPacket.
function ISSlidingGateDrive:new(character, gateId, instance, installing)
    local o = ISBaseTimedAction.new(self, character)
    o.gateId, o.instance, o.installing = gateId, instance, installing
    o.stopOnWalk, o.stopOnRun = true, true
    o.maxTime = o:getDuration()
    return o
end
