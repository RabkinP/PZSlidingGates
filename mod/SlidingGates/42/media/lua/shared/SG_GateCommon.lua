require "SG_GateTypes"
SGGate = SGGate or {}

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

function SGGate.gateWidth(id)
    local entry = SGGate.registry()[id]
    if type(entry) == "table" and entry.width then return entry.width end
    -- Object metadata is available before a network snapshot/global registry.
    local x, y, z = SGGate.parseId(id)
    local sq = x and getCell():getGridSquare(x - 1, y, z)
    if sq then
        local objects = sq:getObjects()
        for i = 0, objects:size() - 1 do
            local md = objects:get(i):getModData()
            if md.sgGate == id and md.sgWidth then return md.sgWidth end
        end
    end
    return 2
end

function SGGate.parts(id)
    local x, y, z = SGGate.parseId(id)
    local result = {}
    if not x then return result end
    for dx = -(2 * SGGate.gateWidth(id) + 1), 1 do
        local sq = getCell():getGridSquare(x + dx, y, z)
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
        obj:setSpriteModelName("Base." .. base .. (base == "SG_Hidden" and "" or (obj:IsOpen() and "_Open" or "_Closed")))
    end
end

function SGGate.width(typeId) return SGGateTypes[typeId] and SGGateTypes[typeId].width end
function SGGate.typeOf(id)
    local leaf = SGGate.findRole(id, "leaf")
    if leaf and leaf:getModData().sgType then return leaf:getModData().sgType end
    local entry = SGGate.registry()[id]
    return type(entry) == "table" and entry.type or (SGGate.gateWidth(id) == 4 and "chainlink4" or "chainlink")
end

function SGGate.canBuild(sq, typeId)
    local definition = SGGateTypes[typeId]
    if not sq or not definition then return false, "unknown gate type" end
    local x, y, z = sq:getX(), sq:getY(), sq:getZ()
    if SGGate.registry()[x .. "," .. y .. "," .. z] then return false, "gate already exists" end
    for k = 0, 2 * definition.width do
        local cell = getCell():getGridSquare(x - k, y, z)
        local north = getCell():getGridSquare(x - k, y - 1, z)
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
        if (role == "leaf" or role == "slave") and sq and sq:getZ() == chr:getCurrentSquare():getZ() then
            local distance = math.sqrt((chr:getX() - sq:getX() - 0.5)^2 + (chr:getY() - sq:getY() - 0.5)^2)
            if not best or distance < best then best = distance end
        end
    end
    return best
end
