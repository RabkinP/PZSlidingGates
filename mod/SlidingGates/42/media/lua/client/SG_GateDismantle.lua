-- SlidingGates: dismantling uses the vanilla "Disassemble" menu (tools, skill, XP, sounds and the scrap yield of the
-- clicked part all come from vanilla ISMoveableSpriteProps:scrapObject). We only make the result consistent with the
-- gate being one object: after the vanilla scrapping of any gate part the rest of the gate goes away too, returning
-- part of the recipe materials (SGGate.destroyGate with a drop chance per unit).

local EXTRA_DROP_PERCENT = 70 -- on top of the vanilla scrap yield of the scrapped part

local function install()
    if not ISMoveableSpriteProps or ISMoveableSpriteProps.sgScrapHooked then return end
    ISMoveableSpriteProps.sgScrapHooked = true
    local original = ISMoveableSpriteProps.scrapObject
    function ISMoveableSpriteProps:scrapObject(character)
        local gateId
        local obj = self.object
        if obj and obj.getModData then
            local md = obj:getModData()
            gateId = md and md.sgGate
        end
        local result = original(self, character)
        if gateId and SGGate.typeOf(gateId) then
            SGGate.destroyGate(gateId, character, EXTRA_DROP_PERCENT)
        end
        return result
    end
end

Events.OnGameBoot.Add(install)
Events.OnGameStart.Add(install)
