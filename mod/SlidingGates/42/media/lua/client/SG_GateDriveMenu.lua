require "SG_GateDriveAction"
require "SG_GatePowerAction"
require "TimedActions/ISTimedActionQueue"
require "ISUI/ISToolTip"

local function requirementsTooltip(character, installing, valid, reason)
    local requirements = SGGateDrive.requirements(character, installing)
    local lines = { getText("Tooltip_craft_Needs") .. ":" }
    local function requirement(label, current, needed)
        -- Same theme-aware good/bad highlight tags as vanilla vehicle mechanics.
        local color = current >= needed and "<GHC>" or "<BHC>"
        lines[#lines + 1] = color .. " " .. label .. " " .. current .. "/" .. needed
    end
    requirement(getText("IGUI_perks_Electricity"), requirements.electrical, 1)
    requirement(getText("IGUI_perks_Mechanics"), requirements.mechanics, 1)
    requirement(getItemDisplayName("Base.Screwdriver"), requirements.screwdriver and 1 or 0, 1)
    requirement(getItemDisplayName("Base.Wrench"), requirements.wrench and 1 or 0, 1)
    if installing then
        requirement(getItemDisplayName(SGGateDrive.itemType), requirements.drives, 1)
        requirement(getItemDisplayName("Base.Screws") .. " / " .. getItemDisplayName("Base.NutsBolts"),
            requirements.fasteners, 4)
    end
    -- Resource failures are already shown per row; retain world/state diagnostics.
    if not valid and reason ~= "skills" and reason ~= "tools" and reason ~= "materials" then
        lines[#lines + 1] = "<BHC> " .. getText("Tooltip_SG_Drive_" .. reason)
    end
    return table.concat(lines, " <LINE> ")
end

local function queue(character, id, instance, installing)
    local sq = SGGateDrive.square(id)
    if sq and luautils.walkAdj(character, sq) then
        ISTimedActionQueue.add(ISSlidingGateDrive:new(character, id, instance, installing))
    end
end

local function queuePower(character, id, instance, opening)
    local sq = SGGateDrive.square(id)
    if sq and luautils.walkAdj(character, sq) then
        ISTimedActionQueue.add(ISSlidingGatePower:new(character, id, instance, opening))
    end
end

-- Vanilla walk-to-container + inventory transfer: works from bags and in multiplayer.
local function queueBattery(character, item, container)
    if luautils.walkToContainer(container, character:getPlayerNum()) then
        ISTimedActionQueue.add(ISInventoryTransferAction:new(character, item, item:getContainer(), container))
    end
end

local function carriedBattery(character)
    local best
    for _, item in ipairs(SGGateDrive.inventoryItems(character:getInventory())) do
        if SGGatePower.isBattery(item) and (not best or item:getCurrentUsesFloat() > best:getCurrentUsesFloat()) then
            best = item
        end
    end
    return best
end

local function addBatteryOptions(context, character, id)
    local drive = SGGate.findRole(id, "drive")
    local container = drive and drive:getContainer()
    if not container then return end
    local inside = SGGatePower.battery(drive)
    if inside then
        context:addOption(getText("ContextMenu_SG_TakeBattery"), character, queueBattery, inside,
            character:getInventory())
    elseif container:getItems():size() == 0 then
        local carried = carriedBattery(character)
        if carried then
            context:addOption(getText("ContextMenu_SG_PutBattery"), character, queueBattery, carried, container)
        end
    end
end

Events.OnFillWorldObjectContextMenu.Add(function(player, context, worldObjects, test)
    if test then return end
    local character = getSpecificPlayer(player)
    if not character then return end
    local seen = {}
    for _, obj in ipairs(worldObjects) do
        local md = obj and obj.getModData and obj:getModData()
        local id = md and md.sgGate
        if id and not seen[id] then
            seen[id] = true
            local leaf = SGGate.findRole(id, "leaf")
            if leaf then
                local instance = leaf:getModData().sgInstance
                local installing = SGGate.findRole(id, "drive") == nil
                local label = getText(installing and "ContextMenu_SG_InstallDrive" or "ContextMenu_SG_RemoveDrive")
                local option = context:addOption(label, character, queue, id, instance, installing)
                local valid, reason = SGGateDrive.check(character, id, instance, installing, false)
                option.notAvailable = not valid
                local tooltip = ISToolTip:new()
                tooltip:initialise()
                tooltip.description = requirementsTooltip(character, installing, valid, reason)
                option.toolTip = tooltip
                if not installing then
                    local opening = not leaf:IsOpen()
                    local powerOption = context:addOption(getText(opening and "ContextMenu_SG_PowerOpen" or
                        "ContextMenu_SG_PowerClose"), character, queuePower, id, instance, opening)
                    local powered, powerReason = SGGatePower.check(character, id, instance, false)
                    powerOption.notAvailable = not powered
                    local powerTip = ISToolTip:new()
                    powerTip:initialise()
                    powerTip.description = getText("Tooltip_SG_BatteryCompartment")
                    if not powered then
                        powerTip.description = powerTip.description .. " <LINE> " .. getText("Tooltip_SG_Drive_" .. powerReason)
                    end
                    powerOption.toolTip = powerTip
                    addBatteryOptions(context, character, id)
                end
            end
        end
    end
end)
