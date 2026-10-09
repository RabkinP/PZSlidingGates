require "keyBinding"
require "SG_Gate"
require "SG_GateRemote"

local binding = "SG_UseRemote"
local exists = false
for _, bind in ipairs(keyBinding) do if bind.value == binding then exists = true; break end end
if not exists then
    table.insert(keyBinding, { value = "[SlidingGates]" })
    table.insert(keyBinding, { value = binding, key = Keyboard.KEY_F9 })
end

Events.OnKeyPressed.Add(function(key)
    local core = getCore()
    if isGamePaused() or core:isDoingTextEntry() or not core:isKey(binding, key) or key == 0 then return end
    local character = getSpecificPlayer(0)
    if character and not character:isDead() then SGGateRemote.activate(character) end
end)
