require "SG_GateCommon"

SGGatePower = {}
SGGatePower.containerType = "sg_drive_battery"
-- Initial balance: one percent per movement, ten percent per game hour.
SGGatePower.cycleCost = 0.01
SGGatePower.chargePerHour = 0.10
local batteryTypes = { ["Base.CarBattery1"] = true, ["Base.CarBattery2"] = true,
    ["Base.CarBattery3"] = true }

function SGGatePower.isBattery(item)
    return item ~= nil and batteryTypes[item:getFullType()] == true
        and instanceof(item, "DrainableComboItem")
end

function SGGatePower.acceptBattery(container, item)
    if not SGGatePower.isBattery(item) then return false end
    local parent = container:getParent()
    if not parent or parent:getModData().sgRole ~= "drive" then return false end
    local items = container:getItems()
    -- Also permit the already contained item when vanilla checks its destination.
    return items:size() == 0 or (items:size() == 1 and items:get(0) == item)
end

function SGGatePower.ensureContainer(drive)
    local container = drive:getContainer()
    local created = container == nil
    if created then
        container = ItemContainer.new(SGGatePower.containerType, drive:getSquare(), drive)
        drive:setContainer(container)
    end
    container:setType(SGGatePower.containerType)
    container:setCapacity(5)
    container:setExplored(true)
    container:setAcceptItemFunction("SGGatePower.acceptBattery")
    local md = drive:getModData()
    if not isClient() and not md.sgDriveIdentity then
        local data = ModData.getOrCreate("SlidingGates")
        data.driveSerial = (data.driveSerial or 0) + 1
        md.sgDriveIdentity = (md.sgDriveData and md.sgDriveData.sgDriveIdentity) or data.driveSerial
        if md.sgDriveData then md.sgDriveData.sgDriveIdentity = md.sgDriveIdentity end
        drive:flagForHotSave()
        created = true
    end
    return container, created
end

function SGGatePower.battery(drive)
    local container = drive and drive:getContainer()
    if not container then return end
    local items = container:getItems()
    if items:size() == 1 and SGGatePower.isBattery(items:get(0)) then return items:get(0) end
end

function SGGatePower.source(drive)
    if not drive or not drive:getSquare() then return "none" end
    if drive:getSquare():haveElectricity() then return "grid" end
    local battery = SGGatePower.battery(drive)
    if battery and battery:getCondition() > 0 and battery:getCurrentUsesFloat() + 0.000001 >= SGGatePower.cycleCost then
        return "battery"
    end
    return "none"
end

local function setCharge(drive, battery, charge)
    battery:setUsedDelta(math.max(0, math.min(1, charge)))
    drive:flagForHotSave()
    if isServer() then sendItemStats(battery) end
end

function SGGatePower.check(character, id, instance, checkDistance, maxDistance)
    if not character or character:isDead() then return false, "missing" end
    local drive, leaf = SGGate.findRole(id, "drive"), SGGate.findRole(id, "leaf")
    if not drive or not leaf then return false, "missing" end
    if leaf:getModData().sgInstance ~= instance then return false, "instance" end
    if SGGate.isMoving(id) then return false, "busy" end
    local sq, playerSq = drive:getSquare(), character:getCurrentSquare()
    if not sq or not playerSq or sq:getZ() ~= playerSq:getZ() then return false, "distance" end
    if checkDistance ~= false and (character:getX()-sq:getX()-0.5)^2 +
        (character:getY()-sq:getY()-0.5)^2 > (maxDistance or 2)^2 then return false, "distance" end
    if SGGatePower.source(drive) == "none" then return false, "power" end
    return true
end

-- Capture a desired state and identity; duplicate completions cannot reverse it.
function SGGatePower.complete(character, id, instance, opening, maxDistance)
    if isClient() or type(opening) ~= "boolean" then return false end
    local valid = SGGatePower.check(character, id, instance, true, maxDistance)
    if not valid then return false end
    local leaf = SGGate.findRole(id, "leaf")
    if leaf:IsOpen() == opening then return true end
    local drive = SGGate.findRole(id, "drive")
    local source, battery = SGGatePower.source(drive), SGGatePower.battery(drive)
    -- No yield between checking power, starting motion and reserving its energy.
    if not SGGate.toggle(id, character, true) then return false end
    if source == "battery" then
        setCharge(drive, battery, battery:getCurrentUsesFloat() - SGGatePower.cycleCost)
    end
    return true
end

-- Charge only for time observed with this loaded drive connected to electricity.
-- Reset the clock on loading: an unloaded/offline interval never grants free charge.
local clocks = setmetatable({}, { __mode = "k" })
function SGGatePower.charge(drive, now)
    if isClient() then return end
    local previous = clocks[drive]
    clocks[drive] = now
    if not previous or now <= previous then return end
    local battery = SGGatePower.battery(drive)
    if not battery or battery:getCondition() <= 0 or not drive:getSquare():haveElectricity() then return end
    local charge = battery:getCurrentUsesFloat()
    if charge < 1 then setCharge(drive, battery, charge + math.min(now - previous, 1/60) * SGGatePower.chargePerHour) end
end

Events.EveryOneMinute.Add(function()
    if isClient() then return end
    local now = getGameTime():getWorldAgeHours()
    for id in pairs(SGGate.registry()) do
        local drive = SGGate.findRole(id, "drive")
        if drive then SGGatePower.charge(drive, now) end
    end
end)

Events.LoadGridsquare.Add(function(square)
    local objects = square:getObjects()
    for i = 0, objects:size() - 1 do
        local drive = objects:get(i)
        if drive:getModData().sgRole == "drive" then
            local _, created = SGGatePower.ensureContainer(drive)
            clocks[drive] = nil
            if created and isServer() then drive:transmitCompleteItemToClients() end
        end
    end
end)
