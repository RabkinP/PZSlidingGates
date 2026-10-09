require "TimedActions/ISBaseTimedAction"
require "SG_GateRemote"
ISSlidingGateRemotePair = ISBaseTimedAction:derive("ISSlidingGateRemotePair")
function ISSlidingGateRemotePair:isValid()
    return SGGateRemote.checkPair(self.character, self.gateId, self.instance, self.remoteId, self.driveIdentity)
end
function ISSlidingGateRemotePair:isValidStart() return self:isValid() end
function ISSlidingGateRemotePair:update() end
function ISSlidingGateRemotePair:start() end
function ISSlidingGateRemotePair:perform() ISBaseTimedAction.perform(self) end
function ISSlidingGateRemotePair:complete()
    return SGGateRemote.pair(self.character, self.gateId, self.instance, self.remoteId, self.driveIdentity)
end
function ISSlidingGateRemotePair:getDuration() return 30 end
function ISSlidingGateRemotePair:new(character, gateId, instance, remoteId, driveIdentity)
    local o = ISBaseTimedAction.new(self, character)
    o.gateId, o.instance, o.remoteId, o.driveIdentity = gateId, instance, remoteId, driveIdentity
    o.stopOnWalk, o.stopOnRun = true, true
    o.maxTime = o:getDuration()
    return o
end
