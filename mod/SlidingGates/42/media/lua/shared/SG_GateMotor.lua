require "SG_GateCommon"

SGGateMotor = {}
SGGateMotor.sound = "SG_GateMotorRunning"
SGGateMotor.noiseRadius = 20
SGGateMotor.noiseVolume = 15
local active = {}

local function silence(entry)
    if entry.emitter then entry.emitter:stopSound(entry.handle) end
    -- World-owned emitters return to the pool after their sound stops.
    entry.emitter, entry.handle = nil, nil
end

function SGGateMotor.stop(id)
    local entry = active[id]
    if entry then silence(entry); active[id] = nil end
end

local function noise(drive)
    if isClient() or not addSound then return end
    local sq = drive:getSquare()
    addSound(drive, sq:getX(), sq:getY(), sq:getZ(), SGGateMotor.noiseRadius, SGGateMotor.noiseVolume)
end

-- Only accepted authority state starts sound; repeated snapshots never stack loops.
function SGGateMotor.sync(state)
    if not state then return end
    if not state.moving or not state.motor or (state.motionRemaining or 0) <= 0 then
        SGGateMotor.stop(state.id)
        return
    end
    local entry = active[state.id]
    if entry and entry.instance ~= state.instance then SGGateMotor.stop(state.id); entry = nil end
    if not entry then
        entry = { instance = state.instance, noiseAfter = 1 }
        active[state.id] = entry
        local drive = SGGate.findRole(state.id, "drive")
        if drive then noise(drive) end
    end
    -- A same-revision refresh may shorten the deadline, but an old duplicate
    -- cannot extend it. A new move has a higher authority revision.
    if entry.revision == state.revision and entry.remaining then
        entry.remaining = math.min(entry.remaining, state.motionRemaining)
    else
        entry.remaining = state.motionRemaining
    end
    entry.revision = state.revision
end

function SGGateMotor.update()
    local paused = isGamePaused and isGamePaused()
    if not paused and not isServer() and UIManager and UIManager.getSpeedControls then
        local controls = UIManager.getSpeedControls()
        paused = controls and controls:getCurrentGameSpeed() == 0
    end
    local step = paused and 0 or getGameTime():getTimeDelta() * 1.5
    for id, entry in pairs(active) do
        local leaf, drive = SGGate.findRole(id, "leaf"), SGGate.findRole(id, "drive")
        if not leaf or not drive or leaf:getModData().sgInstance ~= entry.instance then
            SGGateMotor.stop(id)
        elseif paused then
            silence(entry)
        else
            entry.remaining = entry.remaining - step
            if entry.remaining <= 0 then
                SGGateMotor.stop(id)
            else
                if not isServer() and not entry.emitter and getWorld then
                    local sq = drive:getSquare()
                    entry.emitter = getWorld():getFreeEmitter(sq:getX()+0.5, sq:getY()+0.5, sq:getZ())
                    -- Local playback: authority state already reaches all clients.
                    entry.handle = entry.emitter:playSoundImpl(SGGateMotor.sound, drive)
                end
                entry.noiseAfter = entry.noiseAfter - step
                if entry.noiseAfter <= 0 then noise(drive); entry.noiseAfter = 1 end
            end
        end
    end
end

function SGGateMotor.reset()
    for id in pairs(active) do SGGateMotor.stop(id) end
end
Events.OnGameStart.Add(SGGateMotor.reset)
