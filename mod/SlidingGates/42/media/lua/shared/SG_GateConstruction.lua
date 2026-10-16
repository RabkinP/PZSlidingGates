-- SlidingGates: hook into the B42 entity build system (ISBuildIsoEntity).
-- The entities SlidingGateChainLink2/4 (scripts/entity_sliding_gates.txt) provide the recipe, material check,
-- skill requirement and the placement cursor with placeholder tiles for the opening. The placeholder tiles are never
-- created: after the base class consumed the materials, the real gate is built with SGGate.build.
-- Geometry: the cursor row covers the opening cells x..x+W-1 (N edge); the catcher post sits on x+W and the leaf
-- slides towards -x into the pocket (x-1..x-W, checked in isValid).
-- W uses a column y..y+W-1, catcher y-1 and pocket y+W..y+2W-1.
-- Reversed N/W reflect travel along the edge, keeping the visible face unchanged.
-- Outer variants (nSprite 5..8 = outer 1..4) use the same cells/collision and mirror the assembly across the fence
-- line, facing the other way. nSprite is the only cursor state B42 serializes to the authority.

require "SG_GateCommon"

local GATE_TYPES = {}
local RECIPE_QUALITY = {}
for id, definition in pairs(SGGateTypes) do
    GATE_TYPES[definition.entity] = id
    RECIPE_QUALITY[definition.entity] = "high"
    for _, quality in ipairs({"Low", "Medium"}) do
        GATE_TYPES[definition.entity .. quality] = id
        RECIPE_QUALITY[definition.entity .. quality] = quality:lower()
    end
end

local function recipeQuality(builder)
    local ok, name = pcall(function() return builder.objectInfo:getScript():getName() end)
    return ok and RECIPE_QUALITY[name] or nil
end

-- Match the native wooden-wall recipe filter; Show All still lists every tier.
function SGGateLowRecipeTest(param)
    return param.shouldShowAll or SGGate.qualityForLevel(SGGate.weldingLevel(param.player)) == "low"
end
function SGGateMediumRecipeTest(param)
    return param.shouldShowAll or SGGate.qualityForLevel(SGGate.weldingLevel(param.player)) == "medium"
end
function SGGateHighRecipeTest(param)
    return param.shouldShowAll or SGGate.qualityForLevel(SGGate.weldingLevel(param.player)) == "high"
end

function SGGateWoodLowRecipeTest(param)
    return param.shouldShowAll or SGGate.qualityForLevel(SGGate.buildLevel(param.player, "wood"), "wood") == "low"
end
function SGGateWoodMediumRecipeTest(param)
    return param.shouldShowAll or SGGate.qualityForLevel(SGGate.buildLevel(param.player, "wood"), "wood") == "medium"
end
function SGGateWoodHighRecipeTest(param)
    return param.shouldShowAll or SGGate.qualityForLevel(SGGate.buildLevel(param.player, "wood"), "wood") == "high"
end

local function gateTypeOf(builder)
    local ok, name = pcall(function() return builder.objectInfo:getScript():getName() end)
    return ok and GATE_TYPES[name] or nil
end

-- the catcher cell for a placement origin x (opening starts at x)
-- Outer preview carriers: sg_gates_preview_02_<i> mirrors sg_gates_preview_01_<i> (tdef limit 512 per tileset).
local function previewSprite(index, outer) return (outer and "sg_gates_preview_02_" or "sg_gates_preview_01_") .. index end
local function baseFace(nSprite) return (nSprite - 1) % 4 + 1 end
local function isNorth(nSprite) return baseFace(nSprite) == 2 or baseFace(nSprite) == 4 end
local function direction(nSprite) return baseFace(nSprite) >= 3 and "reverse" or "forward" end
local function side(nSprite) return nSprite > 4 and "outer" or "inner" end
-- N, W, N outer, W outer, reverse N, reverse W, reverse N outer, reverse W outer
local nextFace = { [2] = 1, [1] = 6, [6] = 5, [5] = 4, [4] = 3, [3] = 8, [8] = 7, [7] = 2 }

local function catcherSquare(square, typeId, north, reversed)
    if reversed then
        if north then return getCell():getGridSquare(square:getX()-1, square:getY(), square:getZ()) end
        return getCell():getGridSquare(square:getX(), square:getY()+SGGate.width(typeId), square:getZ())
    end
    if not north then return getCell():getGridSquare(square:getX(), square:getY() - 1, square:getZ()) end
    return getCell():getGridSquare(square:getX() + SGGate.width(typeId), square:getY(), square:getZ())
end

-- Vanilla build cheat (debug Force Build) skips skill requirements; the chosen recipe then sets quality.
local function buildCheat(build)
    local ok, cheat = pcall(function() return build.character:isBuildCheat() end)
    return ok and cheat == true
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
            o.nSprite = nextFace[nSprite] and nSprite or 2 -- 1=W, 2=N, 3=reverse W, 4=reverse N, +4 outer
            o.sgFace = o.nSprite
            o.nSpriteCache = -1
            o.north = isNorth(o.nSprite)
        end
        return o
    end

    local originalRotateKey = ISBuildIsoEntity.rotateKey
    function ISBuildIsoEntity:rotateKey(key)
        if not gateTypeOf(self) then return originalRotateKey(self, key) end
        if getCore():isKey(KeybindId.ROTATE_BUILDING, key) then
            self.nSprite = nextFace[self.sgFace or self.nSprite] or 2
            self.sgFace = self.nSprite
            self.nSpriteCache = -1
            self.north = isNorth(self.nSprite)
        end
    end

    -- Vanilla getFace only knows nSprite 1..4 and would wrap an outer value back to an inner face.
    local originalGetFace = ISBuildIsoEntity.getFace
    function ISBuildIsoEntity:getFace()
        if not originalGetFace then return end
        if not gateTypeOf(self) or not self.nSprite or self.nSprite <= 4 then
            if self.sgOuterCache and self.face then self.sgOuterCache = false; self:cacheSprites(self.face) end
            return originalGetFace(self)
        end
        self.nSprite = self.nSprite - 4
        local face = originalGetFace(self)
        self.nSprite = self.nSprite + 4
        if not self.sgOuterCache and face then self.sgOuterCache = true; self:cacheSprites(face) end
        return face
    end

    -- ISBuildingObject.getSprite derives north/west from nSprite 1..4 (server create calls it).
    local originalGetSprite = ISBuildIsoEntity.getSprite
    function ISBuildIsoEntity:getSprite()
        if not originalGetSprite then return end
        if not gateTypeOf(self) or not self.nSprite or self.nSprite <= 4 then return originalGetSprite(self) end
        self.nSprite = self.nSprite - 4
        local ok, sprite = pcall(originalGetSprite, self)
        self.nSprite = self.nSprite + 4
        if not ok then error(sprite) end
        return sprite
    end

    local originalIsValid = ISBuildIsoEntity.isValid
    function ISBuildIsoEntity:isValid(square)
        local typeId = gateTypeOf(self)
        if not typeId then return originalIsValid(self, square) end
        -- Vanilla auto-rotate (ISBuildingObject drag loop) probes nSprite 1..4 when a spot is invalid and keeps the
        -- first valid one, collapsing outer/reverse faces. Only rotateKey chooses our face: undo and reject probes.
        if self.sgFace and self.nSprite ~= self.sgFace then
            self.nSprite = self.sgFace
            self.nSpriteCache = -1
            self.north = isNorth(self.nSprite)
            return false
        end
        local level = not buildCheat(self) and SGGate.buildLevel(self.character, typeId)
        -- like vanilla, the minimum level is the recipe's SkillRequired; only the exact quality tier is ours
        if level and SGGate.qualityForLevel(level, typeId) ~= recipeQuality(self) then return false end
        if self.getFace then self:getFace() end
        self.north = isNorth(self.nSprite)
        if not originalIsValid(self, square) then return false end
        local reversed = direction(self.nSprite) == "reverse"
        local catcher = catcherSquare(square, typeId, self.north, reversed)
        if not catcher then return false end
        return (SGGate.canBuild(catcher, typeId, self.north and "N" or "W", direction(self.nSprite), side(self.nSprite)))
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
                    if name then
                        local index = self.sgOuterCache and tonumber(name:match("^sg_gates_preview_01_(%d+)$"))
                        self.spriteCache[name] = getSprite(index and previewSprite(index, true) or name)
                    end
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
        local west = not isNorth(self.nSprite)
        local reversed = direction(self.nSprite) == "reverse"
        local catcherX = west and x or (reversed and x-1 or x+width)
        local catcherY = west and (reversed and y+width or y-1) or y
        local sign = reversed and -1 or 1
        local function draw(index, k)
            local sprite = getSprite(previewSprite(index, side(self.nSprite) == "outer"))
            if sprite then sprite:RenderGhostTileColor(catcherX - (west and 0 or sign*k),
                catcherY + (west and sign*k or 0), z, r, g, b, 0.6) end
        end
        local staticStart = reversed and (west and 40 or 36) or (west and 16 or 8)
        if SGGateTypes[typeId].previewStaticStart then
            staticStart = SGGateTypes[typeId].previewStaticStart + (reversed and 8 or 0) + (west and 4 or 0)
        end
        draw(staticStart, 0)
        draw(staticStart+1, width)
        for k = 0, 2 * width - 1 do draw(staticStart+2, k) end
    end

    local originalCreate = ISBuildIsoEntity.create
    function ISBuildIsoEntity:create(x, y, z, north, sprite)
        local typeId = gateTypeOf(self)
        if not typeId then return originalCreate(self, x, y, z, north, sprite) end
        if isClient() then return end -- native B42 build transaction invokes create on the authority
        local placement = getCell():getGridSquare(x, y, z)
        if north ~= isNorth(self.nSprite) or not placement or not self:isValid(placement) then return false end
        print(string.format("[SGBuild] create %s at %d,%d,%d north=%s", typeId, x, y, z, tostring(north)))
        self.sgPlaceholdersReached = false
        originalCreate(self, x, y, z, north, sprite)
        if not self.sgPlaceholdersReached then print("[SGBuild] base create did not reach tile placement"); return end
        local square = getCell():getGridSquare(x, y, z)
        local catcher = square and catcherSquare(square, typeId, self.north, direction(self.nSprite) == "reverse")
        if not catcher then print("[SGBuild] no catcher square"); return end
        local level = SGGate.buildLevel(self.character, typeId)
        local quality = (not buildCheat(self) and level) and SGGate.qualityForLevel(level, typeId) or recipeQuality(self)
        local id = SGGate.build(catcher, typeId, level, north and "N" or "W", direction(self.nSprite), quality, side(self.nSprite))
        print("[SGBuild] SGGate.build -> " .. tostring(id))
    end
    print("[SGBuild] ISBuildIsoEntity hooks installed")
end

Events.OnGameBoot.Add(install)
Events.OnGameStart.Add(install)
Events.OnServerStarted.Add(install)
