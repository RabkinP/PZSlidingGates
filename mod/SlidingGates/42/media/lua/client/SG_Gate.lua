require "SG_GateCommon"
if isClient() then
    require "SG_GateNetwork"
else
    require "SG_GateCore"
end
