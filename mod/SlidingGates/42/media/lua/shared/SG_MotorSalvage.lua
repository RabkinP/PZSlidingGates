-- Add one independent motor roll to vanilla scrapping; never replace its loot.
if not ISMoveableSpriteProps then require "Moveables/ISMoveableSpriteProps" end

local SOURCES = {}
for _, first in ipairs({ 0, 4, 12 }) do
    for index = first, first + 3 do SOURCES["appliances_laundry_01_" .. index] = true end
end
local active = setmetatable({}, { __mode = "k" })

local function install()
    if not ISMoveableSpriteProps or ISMoveableSpriteProps.sgMotorHooked then return end
    ISMoveableSpriteProps.sgMotorHooked = true
    local original = ISMoveableSpriteProps.scrapObject
    function ISMoveableSpriteProps:scrapObject(character)
        local obj = self.object
        local sprite = obj and obj:getSprite()
        if not sprite or not SOURCES[sprite:getName()] then return original(self, character) end
        if isClient() or active[obj] or obj:getObjectIndex() == -1 then return false end
        local square = obj:getSquare()
        local md = obj:getModData()
        active[obj] = true
        local ok, result = pcall(original, self, character)
        active[obj] = nil
        if not ok then error(result) end
        -- Vanilla returns nil on success and deletes the appliance even when its
        -- material rolls fail. Use removal, not the return value or loot count.
        if square and obj:getObjectIndex() == -1 and not md.sgMotorRolled then
            md.sgMotorRolled = true
            if ZombRand(100) < 30 then
                local motor = instanceItem("SlidingGates.ElectricMotor")
                if motor then square:AddWorldInventoryItem(motor, 0.5, 0.5, 0.0) end
            end
        end
        return result
    end
end

Events.OnGameBoot.Add(install)
Events.OnGameStart.Add(install)
Events.OnServerStarted.Add(install)
