require "TimedActions/ISBaseTimedAction"
require "SG_GatePower"
if not isClient() then require "SG_GateCore" end

ISSlidingGatePower = ISBaseTimedAction:derive("ISSlidingGatePower")
function ISSlidingGatePower:isValid()
    return SGGatePower.check(self.character, self.gateId, self.instance)
end
function ISSlidingGatePower:isValidStart() return self:isValid() end
function ISSlidingGatePower:update() end
function ISSlidingGatePower:start() end
function ISSlidingGatePower:perform() ISBaseTimedAction.perform(self) end
function ISSlidingGatePower:complete()
    return SGGatePower.complete(self.character, self.gateId, self.instance, self.opening)
end
function ISSlidingGatePower:getDuration() return 1 end
function ISSlidingGatePower:new(character, gateId, instance, opening)
    local o = ISBaseTimedAction.new(self, character)
    o.gateId, o.instance, o.opening = gateId, instance, opening
    o.stopOnWalk, o.stopOnRun = true, true
    o.maxTime = o:getDuration()
    return o
end
