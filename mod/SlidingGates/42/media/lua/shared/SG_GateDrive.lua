require "SG_GateCommon"
require "SG_GatePower"
if not isClient() then require "SG_GateCore" end

SGGateDrive = {}
SGGateDrive.itemType = "SlidingGates.GateDrive"

local function inventoryItems(container, result)
    result = result or {}
    local items = container:getItems()
    for i = 0, items:size() - 1 do
        local item = items:get(i)
        result[#result + 1] = item
        if instanceof(item, "InventoryContainer") then inventoryItems(item:getInventory(), result) end
    end
    return result
end

function SGGateDrive.square(id)
    local x, y, z = SGGate.parseId(id)
    if x then return SGGate.cellAt(x, y, z, SGGate.gateWidth(id), SGGate.orientation(id), SGGate.direction(id)) end
end

-- One inventory snapshot feeds both the menu requirements and authoritative check.
function SGGateDrive.requirements(character, installing)
    local inv = character:getInventory()
    local notBroken = function(item) return not item:isBroken() end
    local result = {
        electrical = character:getPerkLevel(Perks.Electricity),
        mechanics = character:getPerkLevel(Perks.Mechanics),
        screwdriver = inv:getFirstTagEvalRecurse(ItemTag.SCREWDRIVER, notBroken) ~= nil,
        wrench = inv:getFirstTagEvalRecurse(ItemTag.WRENCH, notBroken) ~= nil,
        drives = 0, fasteners = 0, selected = {},
    }
    if installing then
        for _, item in ipairs(inventoryItems(inv)) do
            local fullType = item:getFullType()
            if fullType == SGGateDrive.itemType then
                result.drives = result.drives + 1
                result.driveItem = result.driveItem or item
            elseif fullType == "Base.Screws" or fullType == "Base.NutsBolts" then
                result.fasteners = result.fasteners + 1
                if #result.selected < 4 then result.selected[#result.selected + 1] = item end
            end
        end
        if result.driveItem then result.selected[#result.selected + 1] = result.driveItem end
    end
    return result
end

-- Return the exact inventory objects to consume, including mixed fasteners and
-- items in bags. Recompute on the authority at completion, never trust a client list.
function SGGateDrive.check(character, id, instance, installing, checkDistance)
    if not character or character:isDead() or type(installing) ~= "boolean" then return false, "missing" end
    local leaf = SGGate.findRole(id, "leaf")
    local sq = SGGateDrive.square(id)
    if not leaf or not sq then return false, "missing" end
    if leaf:getModData().sgInstance ~= instance then return false, "instance" end
    if SGGate.isMoving(id) then return false, "busy" end
    local drive = SGGate.findRole(id, "drive")
    if (installing and drive) or (not installing and not drive) then return false, "changed" end
    if not installing and drive:getContainer() and drive:getContainer():getItems():size() > 0 then
        return false, "contents"
    end
    local playerSquare = character:getCurrentSquare()
    if not playerSquare or playerSquare:getZ() ~= sq:getZ() then return false, "distance" end
    if checkDistance ~= false and (character:getX()-sq:getX()-0.5)^2 +
        (character:getY()-sq:getY()-0.5)^2 > 4 then return false, "distance" end
    local requirements = SGGateDrive.requirements(character, installing)
    if requirements.electrical < 1 or requirements.mechanics < 1 then
        return false, "skills"
    end
    if not requirements.screwdriver or not requirements.wrench then return false, "tools" end
    if installing and (not requirements.driveItem or requirements.fasteners < 4) then return false, "materials" end
    return true, nil, requirements.selected, requirements.driveItem
end

function SGGateDrive.complete(character, id, instance, installing)
    if isClient() then return false end
    local valid, _, selected, driveItem = SGGateDrive.check(character, id, instance, installing)
    if not valid then return false end
    if installing then
        if not SGGate.installDrive(id, driveItem:getModData()) then return false end
        for _, item in ipairs(selected) do
            local container = item:getContainer()
            character:removeFromHands(item)
            container:Remove(item)
            sendRemoveItemFromContainer(container, item)
        end
    else
        local obj = SGGate.findRole(id, "drive")
        local item = instanceItem(SGGateDrive.itemType)
        if not item then return false end
        local data = obj:getModData().sgDriveData
        if data then
            for key, value in pairs(copyTable(data)) do item:getModData()[key] = value end
        end
        if not SGGate.removeDrive(id) then return false end
        local inv = character:getInventory()
        inv:AddItem(item)
        sendAddItemToContainer(inv, item)
    end
    return true
end
