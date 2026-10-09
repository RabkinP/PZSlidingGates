require "SG_GateRemote"
require "ISUI/ISInventoryPaneContextMenu"

-- Extend the vanilla eligibility check, leaving its option/dialog/name sync intact.
-- Do not tag a remote as a key ring: it remains an ordinary electronic item.
local original = ISInventoryPaneContextMenu.doMoreContextMenu
ISInventoryPaneContextMenu.doMoreContextMenu = function(context, tests, moveItems, playerObj, items, count)
    if not tests.canBeRenamed and count == 1 then
        for _, entry in ipairs(items) do
            local item = entry
            if type(entry) == "table" and entry.items then item = entry.items[1] end
            if item and item.getFullType and item:getFullType() == SGGateRemote.itemType then
                tests.canBeRenamed = item
                break
            end
        end
    end
    return original(context, tests, moveItems, playerObj, items, count)
end
