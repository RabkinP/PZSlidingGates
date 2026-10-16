require "SG_GateTypes"
SGGate = SGGate or {}
SGGate.MIN_BUILD_LEVEL = 4
-- Saved data layout of registry entries (entry.version) and parts (modData.sgVersion).
-- Data without a version is 1. Migrations live in SG_GateCore.lua.
SGGate.DATA_VERSION = 2

function SGGate.damageForRatio(ratio)
    if ratio <= 0.25 then return 3 end
    if ratio <= 0.50 then return 2 end
    if ratio <= 0.75 then return 1 end
    return 0
end

function SGGate.qualityForLevel(level, typeId)
    if SGGateTypes[typeId] and SGGateTypes[typeId].skill == "Woodwork" then
        if (tonumber(level) or 0) >= 7 then return "high" end
        if (tonumber(level) or 0) >= 5 then return "medium" end
        return "low"
    end
    if (tonumber(level) or 0) >= 8 then return "high" end
    if (tonumber(level) or 0) >= 6 then return "medium" end
    return "low"
end

function SGGate.buildLevel(character, typeId)
    if not character then return end
    local t = SGGateTypes[typeId]
    local ok, level = pcall(function()
        return character:getPerkLevel(t and t.skill == "Woodwork" and Perks.Woodwork or Perks.MetalWelding)
    end)
    if ok and type(level) == "number" then return level end
end

function SGGate.weldingLevel(character)
    if not character then return end
    local ok, level = pcall(function() return character:getPerkLevel(Perks.MetalWelding) end)
    if ok and type(level) == "number" then return level end
end

function SGGate.quality(id)
    local entry = SGGate.registry()[id]
    if type(entry) == "table" and entry.quality then return entry.quality end
    for _, obj in ipairs(SGGate.parts(id)) do
        if obj:getModData().sgQuality then return obj:getModData().sgQuality end
    end
    return "high" -- Legacy assemblies retain the existing model.
end

-- side "outer" mirrors the whole assembly across the fence line (same edge, cells and collision).
function SGGate.leafModel(typeId, orientation, direction, quality, side)
    local t = SGGateTypes[typeId]
    if not t then return end
    local field = orientation == "W" and "westLeafModel" or "leafModel"
    if direction == "reverse" then field = orientation == "W" and "westReverseLeafModel" or "reverseLeafModel" end
    local base = t[field]
    if quality == "low" or quality == "medium" then
        local prefix = t.modelPrefix or (t.width == 4 and "SG_ChainLink_4" or "SG_ChainLink")
        base = prefix .. "_" .. (quality == "low" and "Low" or "Medium") .. base:sub(#prefix + 1)
    end
    return side == "outer" and base .. "_Out" or base
end

function SGGate.registry()
    local data = ModData.getOrCreate("SlidingGates")
    data.gates = data.gates or {}
    return data.gates
end

function SGGate.parseId(id)
    if type(id) ~= "string" or #id > 64 then return end
    local x, y, z = id:match("^(-?%d+),(-?%d+),(-?%d+)$")
    if not x then return end
    return tonumber(x), tonumber(y), tonumber(z)
end

-- Legacy gates have no orientation and keep the original N edge / -X travel.
local function nearbyMetadata(id)
    local x, y, z = SGGate.parseId(id)
    if not x then return end
    for _, offset in ipairs({ {-1, 0}, {0, 1}, {0, 0}, {1, 0}, {0, -1} }) do
        local sq = getCell():getGridSquare(x + offset[1], y + offset[2], z)
        if sq then
            local objects = sq:getObjects()
            for i = 0, objects:size() - 1 do
                local md = objects:get(i):getModData()
                if md.sgGate == id then return md end
            end
        end
    end
end

function SGGate.orientation(id)
    local entry = SGGate.registry()[id]
    if type(entry) == "table" and entry.orientation then return entry.orientation end
    local md = nearbyMetadata(id)
    return md and md.sgOrientation or "N"
end

function SGGate.direction(id)
    local entry = SGGate.registry()[id]
    if type(entry) == "table" and entry.direction then return entry.direction end
    local md = nearbyMetadata(id)
    return md and md.sgDirection or "forward"
end

function SGGate.side(id)
    local entry = SGGate.registry()[id]
    if type(entry) == "table" and entry.side then return entry.side end
    local md = nearbyMetadata(id)
    return md and md.sgSide or "inner"
end

function SGGate.cellAt(x, y, z, k, orientation, direction)
    if direction == "reverse" then k = -k end
    if orientation == "W" then return getCell():getGridSquare(x, y + k, z) end
    return getCell():getGridSquare(x - k, y, z)
end

function SGGate.edgeNeighbour(sq, orientation)
    if not sq then return end
    return getCell():getGridSquare(sq:getX() - (orientation == "W" and 1 or 0),
        sq:getY() - (orientation == "W" and 0 or 1), sq:getZ())
end

function SGGate.gateWidth(id)
    local entry = SGGate.registry()[id]
    if type(entry) == "table" and entry.width then return entry.width end
    -- Object metadata is available before a network snapshot/global registry.
    local md = nearbyMetadata(id)
    if md and md.sgWidth then return md.sgWidth end
    return 2
end

function SGGate.parts(id)
    local x, y, z = SGGate.parseId(id)
    local result = {}
    if not x then return result end
    for k = -1, 2 * SGGate.gateWidth(id) + 1 do
        local sq = SGGate.cellAt(x, y, z, k, SGGate.orientation(id), SGGate.direction(id))
        if sq then
            local objects = sq:getObjects()
            for i = 0, objects:size() - 1 do
                local obj = objects:get(i)
                if obj:getModData().sgGate == id then result[#result + 1] = obj end
            end
        end
    end
    return result
end

function SGGate.findRole(id, role)
    for _, obj in ipairs(SGGate.parts(id)) do
        if obj:getModData().sgRole == role then return obj end
    end
end

function SGGate.applyModel(obj)
    local md = obj:getModData()
    if md.sgStatic then obj:setSpriteModelName("Base." .. md.sgStatic); return end
    local base = md.sgBase
    if base then
        local visualChanged = false
        if md.sgRole == "leaf" then
            local entry = SGGate.registry()[md.sgGate]
            local damage = type(entry) == "table" and entry.damage or md.sgDamage or 0
            -- A running native track owns its model until it reaches its end pose.
            if md.sgMoving ~= nil or obj:isAnimating() then damage = md.sgVisualDamage or 0 end
            visualChanged = (md.sgVisualDamage or 0) ~= damage
            md.sgVisualDamage = damage
            if damage > 0 then base = base .. "_Damage" .. damage end
        end
        obj:setSpriteModelName("Base." .. base .. (base == "SG_Hidden" and "" or (obj:IsOpen() and "_Open" or "_Closed")))
        if visualChanged and obj:getSquare() then obj:invalidateRenderChunkLevel(256) end
    end
end

function SGGate.width(typeId) return SGGateTypes[typeId] and SGGateTypes[typeId].width end
function SGGate.typeOf(id)
    local leaf = SGGate.findRole(id, "leaf")
    if leaf and leaf:getModData().sgType then return leaf:getModData().sgType end
    local entry = SGGate.registry()[id]
    return type(entry) == "table" and entry.type or (SGGate.gateWidth(id) == 4 and "chainlink4" or "chainlink")
end

function SGGate.canBuild(sq, typeId, orientation, direction, side)
    local definition = SGGateTypes[typeId]
    if not sq or not definition then return false, "unknown gate type" end
    orientation = orientation or "N"
    direction = direction or "forward"
    if orientation ~= "N" and orientation ~= "W" then return false, "unsupported orientation" end
    if direction ~= "forward" and direction ~= "reverse" then return false, "unsupported direction" end
    if side ~= nil and side ~= "inner" and side ~= "outer" then return false, "unsupported side" end
    local x, y, z = sq:getX(), sq:getY(), sq:getZ()
    if SGGate.registry()[x .. "," .. y .. "," .. z] then return false, "gate already exists" end
    for k = 0, 2 * definition.width do
        local cell = SGGate.cellAt(x, y, z, k, orientation, direction)
        local north = SGGate.edgeNeighbour(cell, orientation)
        if not cell or not north then return false, "gate area is not loaded" end
        if k >= 1 and k <= definition.width and cell:isBlockedTo(north) then
            return false, "opening is blocked at cell " .. k
        end
    end
    return true
end

function SGGate.distanceTo(chr, id)
    local best
    if not chr or not chr:getCurrentSquare() then return end
    for _, obj in ipairs(SGGate.parts(id)) do
        local role, sq = obj:getModData().sgRole, obj:getSquare()
        if (role == "leaf" or role == "slave" or role == "block") and sq and sq:getZ() == chr:getCurrentSquare():getZ() then
            local distance = math.sqrt((chr:getX() - sq:getX() - 0.5)^2 + (chr:getY() - sq:getY() - 0.5)^2)
            if not best or distance < best then best = distance end
        end
    end
    return best
end
