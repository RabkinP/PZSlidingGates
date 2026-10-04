-- SlidingGates: hook into the B42 entity build system (ISBuildIsoEntity).
-- The entities SlidingGateChainLink2/4 (scripts/entity_sliding_gates.txt) provide the recipe, material check,
-- skill requirement and the placement cursor with placeholder tiles for the opening. The placeholder tiles are never
-- created: after the base class consumed the materials, the real gate is built with SGGate.build.
-- Geometry: the cursor row covers the opening cells x..x+W-1 (N edge); the catcher post sits on x+W and the leaf
-- slides towards -x into the pocket (x-1..x-W, checked in isValid).

local GATE_TYPES = {
    SlidingGateChainLink2 = "chainlink",
    SlidingGateChainLink4 = "chainlink4",
}

local function gateTypeOf(builder)
    local ok, name = pcall(function() return builder.objectInfo:getScript():getName() end)
    return ok and GATE_TYPES[name] or nil
end

-- the catcher cell for a placement origin x (opening starts at x)
local function catcherSquare(square, typeId)
    return getCell():getGridSquare(square:getX() + SGGate.width(typeId), square:getY(), square:getZ())
end

-- ISBuildIsoEntity lives in lua/server and is not loaded yet when client files run: wrap it once the game started.
local function install()
    if not ISBuildIsoEntity or ISBuildIsoEntity.sgHooked then return end
    ISBuildIsoEntity.sgHooked = true

    local originalIsValid = ISBuildIsoEntity.isValid
    function ISBuildIsoEntity:isValid(square)
        local typeId = gateTypeOf(self)
        if not typeId then return originalIsValid(self, square) end
        if not self.north then return false end -- only the N edge (gates extending towards -x) is supported so far
        if not originalIsValid(self, square) then return false end
        local catcher = catcherSquare(square, typeId)
        if not catcher then return false end
        return (SGGate.canBuild(catcher, typeId))
    end

    -- never place the placeholder tiles of our entities; remember that the base class got as far as placing them
    local originalSetInfo = ISBuildIsoEntity.setInfo
    function ISBuildIsoEntity:setInfo(square, north, sprite, openSprite)
        if gateTypeOf(self) then
            self.sgPlaceholdersReached = true
            return
        end
        return originalSetInfo(self, square, north, sprite, openSprite)
    end

    local originalCreate = ISBuildIsoEntity.create
    function ISBuildIsoEntity:create(x, y, z, north, sprite)
        local typeId = gateTypeOf(self)
        if not typeId then return originalCreate(self, x, y, z, north, sprite) end
        print(string.format("[SGBuild] create %s at %d,%d,%d north=%s", typeId, x, y, z, tostring(north)))
        self.sgPlaceholdersReached = false
        originalCreate(self, x, y, z, north, sprite)
        if not self.sgPlaceholdersReached then print("[SGBuild] base create did not reach tile placement"); return end
        local square = getCell():getGridSquare(x, y, z)
        local catcher = square and catcherSquare(square, typeId)
        if not catcher then print("[SGBuild] no catcher square"); return end
        local id = SGGate.build(catcher, typeId)
        print("[SGBuild] SGGate.build -> " .. tostring(id))
    end
    print("[SGBuild] ISBuildIsoEntity hooks installed")
end

Events.OnGameBoot.Add(install)
Events.OnGameStart.Add(install)
