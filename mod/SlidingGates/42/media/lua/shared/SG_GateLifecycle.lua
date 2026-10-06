require "SG_GateCommon"
require "TimedActions/ISDestroyStuffAction"

local function install()
    if ISDestroyStuffAction.sgGateHooked then return end
    ISDestroyStuffAction.sgGateHooked = true
    local original = ISDestroyStuffAction.complete
    function ISDestroyStuffAction:complete()
        local md = self.item and self.item:getModData()
        local gateId = md and md.sgGate
        local result = original(self)
        if gateId and result and not isClient() then SGGate.destroyGate(gateId, self.character) end
        return result
    end
end
Events.OnGameBoot.Add(install)
Events.OnGameStart.Add(install)
Events.OnServerStarted.Add(install)
