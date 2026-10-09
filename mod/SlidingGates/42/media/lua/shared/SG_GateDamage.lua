-- Automatically loaded on SP/server. Clients receive the authoritative stage.
require "SG_GateCore"
if isClient() then return end

local nextCheck = 0
Events.OnTick.Add(function()
    local now = getTimestampMs()
    if now < nextCheck then return end
    nextCheck = now + 500
    for id in pairs(SGGate.registry()) do SGGate.updateDamage(id) end
end)
