-- SlidingGates: dismantling uses the vanilla "Disassemble" menu (tools, skill, XP and sounds come from
-- ISMoveableSpriteProps:scrapObject). Gate material yield is handled once for the
-- entire assembly; vanilla carrier-tile scrap must not be added on top of it.

local DROP_PERCENT = 70

if not isServer() then require "ISUI/ISDisassembleMenu" end
if not ISMoveableSpriteProps then require "Moveables/ISMoveableSpriteProps" end

local function install()
    if not ISMoveableSpriteProps or ISMoveableSpriteProps.sgScrapHooked then return end
    ISMoveableSpriteProps.sgScrapHooked = true
    -- A gate has several selectable carriers, but only its leaf is an action target.
    if ISDisassembleMenu then
        local originalMenu = ISDisassembleMenu.createMenu
        function ISDisassembleMenu.createMenu(worldObjects, context, playerObj)
            local objects, seen = {}, {}
            for _, obj in ipairs(worldObjects) do
                local md = obj and obj.getModData and obj:getModData()
                local id = md and md.sgGate
                if not id then
                    objects[#objects + 1] = obj
                elseif not seen[id] then
                    seen[id] = true
                    for _, part in ipairs(SGGate.parts(id)) do
                        if part:getModData().sgRole == "leaf" then
                            objects[#objects + 1] = part
                            break
                        end
                    end
                end
            end
            return originalMenu(objects, context, playerObj)
        end
    end
    -- Configure each gate before menu eligibility and timed-action creation.
    -- Shared vanilla tiles and the carpentry thumpable fallback must stay untouched.
    local originalFromObject = ISMoveableSpriteProps.fromObject
    function ISMoveableSpriteProps.fromObject(obj)
        local md = obj and obj.getModData and obj:getModData()
        if not (md and md.sgGate) then return originalFromObject(obj) end
        local props = ISMoveableSpriteProps.new(obj:getSprite())
        props.object = obj
        props.isFromObject = true
        props.material = "MetalPipe"
        props.material2 = nil
        props.material3 = nil
        props.canScrap = true
        props.scrapUseTool = true
        props.scrapUseSkill = true
        props.scrapSize = "Medium"
        props.scrapToolUses = 5
        props.isMultiSprite = false
        props.name = obj:getName() or "Sliding gate"
        return props
    end

    local originalItems = ISMoveableSpriteProps.getScrapItemsList
    function ISMoveableSpriteProps:getScrapItemsList(character)
        if self.sgGateScrap then return { usable = {}, unusable = {} } end
        return originalItems(self, character)
    end

    local original = ISMoveableSpriteProps.scrapObject
    function ISMoveableSpriteProps:scrapObject(character)
        local gateId
        local obj = self.object
        if obj and obj.getModData then
            local md = obj:getModData()
            gateId = md and md.sgGate
        end
        if not gateId then return original(self, character) end
        if isClient() then return false end -- the vanilla action completes scrapping on the server
        local previous = self.sgGateScrap
        self.sgGateScrap = true
        local ok, result = pcall(original, self, character)
        self.sgGateScrap = previous
        if not ok then error(result) end
        -- Vanilla returns nil even on success. Check actual removal, not its return value or skill roll.
        if obj:getObjectIndex() == -1 then
            SGGate.destroyGate(gateId, character, DROP_PERCENT)
        end
        return result
    end
end

Events.OnGameBoot.Add(install)
Events.OnGameStart.Add(install)
Events.OnServerStarted.Add(install)
