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

    -- the cursor must start in the N orientation (the only one supported); other rotations stay invalid
    local originalNew = ISBuildIsoEntity.new
    function ISBuildIsoEntity:new(character, objectInfo, nSprite, containers, logic)
        local o = originalNew(self, character, objectInfo, nSprite, containers, logic)
        if o and gateTypeOf(o) then
            o.nSprite = 2   -- 1=W 2=N 3=E 4=S
            o.nSpriteCache = -1
            o.north = true
        end
        return o
    end

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

    -- preview of the real gate models under the cursor (the entity tiles are only flat markers)
    local function clearPreview(builder)
        if builder.sgPreview then SGGate.clearPreview(builder.sgPreview) end
        builder.sgPreview, builder.sgPreviewKey = nil, nil
    end

    local originalRender = ISBuildIsoEntity.render
    function ISBuildIsoEntity:render(x, y, z, square)
        originalRender(self, x, y, z, square)
        local typeId = gateTypeOf(self)
        if not typeId then return end
        local key = square and (x .. "," .. y .. "," .. z) or "none"
        if key == self.sgPreviewKey then return end
        clearPreview(self)
        self.sgPreviewKey = key
        local catcher = square and catcherSquare(square, typeId)
        if catcher then
            local valid = self:isValid(square)
            self.sgPreview = SGGate.createPreview(catcher, typeId, valid and 0.65 or 0.3)
        end
    end

    local originalDeactivate = ISBuildIsoEntity.deactivate
    function ISBuildIsoEntity:deactivate()
        if gateTypeOf(self) then clearPreview(self) end
        return originalDeactivate(self)
    end

    local originalCreate = ISBuildIsoEntity.create
    function ISBuildIsoEntity:create(x, y, z, north, sprite)
        local typeId = gateTypeOf(self)
        if not typeId then return originalCreate(self, x, y, z, north, sprite) end
        clearPreview(self) -- the real gate replaces the preview
        print(string.format("[SGBuild] create %s at %d,%d,%d north=%s", typeId, x, y, z, tostring(north)))
        self.sgPlaceholdersReached = false
        originalCreate(self, x, y, z, north, sprite)
        if not self.sgPlaceholdersReached then print("[SGBuild] base create did not reach tile placement"); return end
        local square = getCell():getGridSquare(x, y, z)
        local catcher = square and catcherSquare(square, typeId)
        if not catcher then print("[SGBuild] no catcher square"); return end
        local bonus = 0
        local ok, level = pcall(function() return self.character:getPerkLevel(Perks.MetalWelding) end)
        if ok and type(level) == "number" then bonus = level * 50 end -- health: base + 50 per welding level
        local id = SGGate.build(catcher, typeId, bonus)
        print("[SGBuild] SGGate.build -> " .. tostring(id))
    end
    print("[SGBuild] ISBuildIsoEntity hooks installed")
end

Events.OnGameBoot.Add(install)
Events.OnGameStart.Add(install)
