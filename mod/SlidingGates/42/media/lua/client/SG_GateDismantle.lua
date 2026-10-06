-- SlidingGates: dismantling a gate with a blowtorch (more materials back than when it is destroyed).
-- Context menu entry on any gate part -> equip the torch, walk next to the gate, timed action -> SGGate.destroyGate
-- with a higher drop chance. Requires the same MetalWelding level as building the gate and some torch fuel.

require "TimedActions/ISBaseTimedAction"

ISSlidingGateDismantle = ISBaseTimedAction:derive("ISSlidingGateDismantle")

local MAX_DISTANCE = 3.0
local DROP_PERCENT = 80
local XP_AWARD = 20

local function findTorch(playerObj, minUses)
    local inv = playerObj:getInventory()
    return inv:getFirstTypeEvalRecurse("Base.BlowTorch", function(item)
        return item:getCurrentUses() >= minUses
    end)
end

function ISSlidingGateDismantle:isValid()
    local d = SGGate.distanceTo(self.character, self.gateId)
    return d ~= nil and d <= MAX_DISTANCE
end

function ISSlidingGateDismantle:update()
    self.character:setMetabolicTarget(Metabolics.UsingTools)
end

function ISSlidingGateDismantle:start()
    self:setActionAnim("BlowTorch")
    self:setOverrideHandModels(self.character:getPrimaryHandItem(), nil)
end

function ISSlidingGateDismantle:stop()
    ISBaseTimedAction.stop(self)
end

function ISSlidingGateDismantle:perform()
    ISBaseTimedAction.perform(self)
end

function ISSlidingGateDismantle:complete()
    local req = SGGate.dismantleRequirements(SGGate.typeOf(self.gateId))
    if not req then return false end
    local torch = findTorch(self.character, req.torchUses)
    if not torch then return false end
    for _ = 1, req.torchUses do torch:UseAndSync() end -- fuel of a drainable item, one unit per call
    SGGate.destroyGate(self.gateId, self.character, DROP_PERCENT)
    self.character:getXp():AddXP(Perks.MetalWelding, XP_AWARD)
    return true
end

function ISSlidingGateDismantle:getDuration()
    return 250
end

function ISSlidingGateDismantle:new(character, gateId)
    local o = ISBaseTimedAction.new(self, character)
    o.gateId = gateId
    o.stopOnWalk = true
    o.stopOnRun = true
    o.maxTime = o:getDuration()
    return o
end

local function onDismantle(playerObj, gateId, anchorObj)
    local req = SGGate.dismantleRequirements(SGGate.typeOf(gateId))
    local torch = req and findTorch(playerObj, req.torchUses)
    if not torch then return end
    ISInventoryPaneContextMenu.equipWeapon(torch, true, false, playerObj:getPlayerNum()) -- primary hand
    if luautils.walkAdj(playerObj, anchorObj:getSquare(), true) then
        ISTimedActionQueue.add(ISSlidingGateDismantle:new(playerObj, gateId))
    end
end

local function gateIdAt(worldobjects)
    for _, o in ipairs(worldobjects) do
        local d = o.getModData and o:getModData()
        if d and d.sgGate then return d.sgGate, o end
        local sq = o.getSquare and o:getSquare()
        if sq then
            local objs = sq:getObjects()
            for i = 0, objs:size() - 1 do
                local md = objs:get(i):getModData()
                if md and md.sgGate then return md.sgGate, objs:get(i) end
            end
        end
    end
end

Events.OnFillWorldObjectContextMenu.Add(function(player, context, worldobjects, test)
    if test then return end
    local gateId, anchorObj = gateIdAt(worldobjects)
    if not gateId then return end
    local playerObj = getSpecificPlayer(player)
    local req = SGGate.dismantleRequirements(SGGate.typeOf(gateId))
    if not req then return end
    local option = context:addOption(getText("ContextMenu_SG_Dismantle"), playerObj, onDismantle, gateId, anchorObj)
    local problems = {}
    if playerObj:getPerkLevel(Perks.MetalWelding) < req.welding then
        problems[#problems + 1] = getText("Tooltip_SG_NeedWelding", req.welding)
    end
    if not findTorch(playerObj, req.torchUses) then
        problems[#problems + 1] = getText("Tooltip_SG_NeedTorch", req.torchUses)
    end
    if #problems > 0 then
        option.notAvailable = true
        local tip = ISInventoryPaneContextMenu.addToolTip()
        tip.description = table.concat(problems, " <LINE> ")
        option.toolTip = tip
    end
end)

-- The vanilla "Disassemble" menu (ISDisassembleMenu) would offer to scrap a single gate part (the door carrier tiles
-- have CanScrap) and leave the rest of the gate behind. Gates are dismantled as a whole by the entry above only.
local function hideGatePartsFromVanillaScrap()
    if not ISMoveableSpriteProps or ISMoveableSpriteProps.sgScrapHooked then return end
    ISMoveableSpriteProps.sgScrapHooked = true
    local original = ISMoveableSpriteProps.canScrapObject
    function ISMoveableSpriteProps:canScrapObject(character)
        local obj = self.object
        if obj and obj.getModData then
            local md = obj:getModData()
            if md and md.sgGate then return { canScrap = false, craftValid = false }, 0, nil end
        end
        return original(self, character)
    end
end

Events.OnGameBoot.Add(hideGatePartsFromVanillaScrap)
Events.OnGameStart.Add(hideGatePartsFromVanillaScrap)
