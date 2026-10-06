-- SlidingGates: hook into the B42 entity build system (ISBuildIsoEntity).
-- The entities SlidingGateChainLink2/4 (scripts/entity_sliding_gates.txt) provide the recipe, material check,
-- skill requirement and the placement cursor with placeholder tiles for the opening. The placeholder tiles are never
-- created: after the base class consumed the materials, the real gate is built with SGGate.build.
-- Geometry: the cursor row covers the opening cells x..x+W-1 (N edge); the catcher post sits on x+W and the leaf
-- slides towards -x into the pocket (x-1..x-W, checked in isValid).
-- W uses a column y..y+W-1, catcher y-1 and pocket y+W..y+2W-1.

require "SG_GateCommon"

local GATE_TYPES = {}
for id, definition in pairs(SGGateTypes) do GATE_TYPES[definition.entity] = id end

local function gateTypeOf(builder)
    local ok, name = pcall(function() return builder.objectInfo:getScript():getName() end)
    return ok and GATE_TYPES[name] or nil
end

-- the catcher cell for a placement origin x (opening starts at x)
local function catcherSquare(square, typeId, north)
    if not north then return getCell():getGridSquare(square:getX(), square:getY() - 1, square:getZ()) end
    return getCell():getGridSquare(square:getX() + SGGate.width(typeId), square:getY(), square:getZ())
end

-- ISBuildIsoEntity lives in lua/server and is not loaded yet when client files run: wrap it once the game started.
local function install()
    if not ISBuildIsoEntity or ISBuildIsoEntity.sgHooked then return end
    ISBuildIsoEntity.sgHooked = true

    -- Preserve the serialized B42 nSprite on the server; new cursors default to N.
    local originalNew = ISBuildIsoEntity.new
    function ISBuildIsoEntity:new(character, objectInfo, nSprite, containers, logic)
        local o = originalNew(self, character, objectInfo, nSprite, containers, logic)
        if o and gateTypeOf(o) then
            o.nSprite = nSprite == 1 and 1 or 2   -- 1=W 2=N
            o.nSpriteCache = -1
            o.north = o.nSprite == 2
        end
        return o
    end

    local originalRotateKey = ISBuildIsoEntity.rotateKey
    function ISBuildIsoEntity:rotateKey(key)
        if not gateTypeOf(self) then return originalRotateKey(self, key) end
        if getCore():isKey(KeybindId.ROTATE_BUILDING, key) then
            self.nSprite = self.nSprite == 2 and 1 or 2
            self.nSpriteCache = -1
            self.north = self.nSprite == 2
        end
    end

    local originalIsValid = ISBuildIsoEntity.isValid
    function ISBuildIsoEntity:isValid(square)
        local typeId = gateTypeOf(self)
        if not typeId then return originalIsValid(self, square) end
        if self.getFace then self:getFace() end
        self.north = self.nSprite == 2
        if not originalIsValid(self, square) then return false end
        local catcher = catcherSquare(square, typeId, self.north)
        if not catcher then return false end
        return (SGGate.canBuild(catcher, typeId, self.north and "N" or "W"))
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

    -- B42's cacheSprites makes texture-only copies via LoadSingleTexture, losing spriteModel.
    -- Our cursor uses the registered sprites; the ghost renderer does not mutate their properties.
    local originalCacheSprites = ISBuildIsoEntity.cacheSprites
    function ISBuildIsoEntity:cacheSprites(face)
        if not gateTypeOf(self) then return originalCacheSprites(self, face) end
        if not face then return end
        for z = 0, face:getzLayers() - 1 do
            for x = 0, face:getWidth() - 1 do
                for y = 0, face:getHeight() - 1 do
                    local info = face:getTileInfo(x, y, z)
                    local name = info and info:getSpriteName()
                    if name then self.spriteCache[name] = getSprite(name) end
                end
            end
        end
    end

    -- The base cursor draws the leaf from our entity carrier on the catcher-adjacent opening cell.
    -- Static parts use the same native ghost renderer; no objects are inserted into the world.
    local originalRender = ISBuildIsoEntity.render
    function ISBuildIsoEntity:render(x, y, z, square)
        originalRender(self, x, y, z, square)
        local typeId = gateTypeOf(self)
        if not typeId then return end
        if not square then return end
        local valid = self:isValid(square)
        local r, g, b = 1, 1, 1
        if not valid then r, g, b = 0.65, 0.2, 0.2 end
        local width = SGGate.width(typeId)
        local west = self.nSprite == 1
        local catcherX, catcherY = west and x or x + width, west and y - 1 or y
        local function draw(index, k)
            local sprite = getSprite("sg_gates_preview_01_" .. index)
            if sprite then sprite:RenderGhostTileColor(catcherX - (west and 0 or k),
                catcherY + (west and k or 0), z, r, g, b, 0.6) end
        end
        draw(west and 16 or 8, 0)
        draw(west and 17 or 9, width)
        for k = 0, 2 * width - 1 do draw(west and 18 or 10, k) end
    end

    local originalCreate = ISBuildIsoEntity.create
    function ISBuildIsoEntity:create(x, y, z, north, sprite)
        local typeId = gateTypeOf(self)
        if not typeId then return originalCreate(self, x, y, z, north, sprite) end
        if isClient() then return end -- native B42 build transaction invokes create on the authority
        local placement = getCell():getGridSquare(x, y, z)
        if north ~= (self.nSprite == 2) or not placement or not self:isValid(placement) then return false end
        print(string.format("[SGBuild] create %s at %d,%d,%d north=%s", typeId, x, y, z, tostring(north)))
        self.sgPlaceholdersReached = false
        originalCreate(self, x, y, z, north, sprite)
        if not self.sgPlaceholdersReached then print("[SGBuild] base create did not reach tile placement"); return end
        local square = getCell():getGridSquare(x, y, z)
        local catcher = square and catcherSquare(square, typeId, self.north)
        if not catcher then print("[SGBuild] no catcher square"); return end
        local bonus = 0
        local ok, level = pcall(function() return self.character:getPerkLevel(Perks.MetalWelding) end)
        if ok and type(level) == "number" then bonus = level * 50 end -- health: base + 50 per welding level
        local id = SGGate.build(catcher, typeId, bonus, north and "N" or "W")
        print("[SGBuild] SGGate.build -> " .. tostring(id))
    end
    print("[SGBuild] ISBuildIsoEntity hooks installed")
end

Events.OnGameBoot.Add(install)
Events.OnGameStart.Add(install)
Events.OnServerStarted.Add(install)
