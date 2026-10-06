require "SG_GateCore"
if not isServer() then return end

SGGate.onStateChanged = function(state)
    if state then sendServerCommand("SlidingGates", "state", state) end
end
SGGate.onRemoved = function(id, instance, revision)
    sendServerCommand("SlidingGates", "removed", { id = id, instance = instance, revision = revision })
end

-- Coordinates alone identify a place, not an assembly. Instance rejects delayed
-- requests after rebuilding there; revision rejects concurrent/stale commands.
function SGGate.handleRequest(player, args)
    if type(args) ~= "table" or not SGGate.parseId(args.id) then return false, "invalid" end
    local state = SGGate.snapshot(args.id)
    if not state then return false, "missing" end
    if not player or player:isDead() or (SGGate.distanceTo(player, args.id) or 99) > 3 then
        return false, "distance"
    end
    if args.instance ~= state.instance then return false, "instance" end
    if type(args.open) ~= "boolean" then return false, "invalid" end
    -- Repeating a desired state never reverses a move or consumes another cycle.
    if args.open == state.open then return true, "unchanged" end
    if args.revision ~= state.revision then return false, "stale" end
    if SGGate.isMoving(args.id) then return false, "busy" end
    if not SGGate.toggle(args.id, player) then return false, "blocked" end
    return true, "accepted"
end

Events.OnClientCommand.Add(function(module, command, player, args)
    if module ~= "SlidingGates" or type(args) ~= "table" or not player then return end
    if command == "snapshot" then
        if not SGGate.parseId(args.id) then return end
        local state = SGGate.snapshot(args.id)
        -- Only loaded gates near the requester need snapshots, not the whole world registry.
        local x, y, z = SGGate.parseId(args.id)
        local sq = player and player:getCurrentSquare()
        if state and sq and sq:getZ() == z and math.abs(player:getX()-x) <= 32 and math.abs(player:getY()-y) <= 32 then
            sendServerCommand(player, "SlidingGates", "snapshot", state)
        end
    elseif command == "toggle" then
        local accepted, reason = SGGate.handleRequest(player, args)
        local state = SGGate.parseId(args.id) and SGGate.snapshot(args.id)
        sendServerCommand(player, "SlidingGates", "result", {
            id = args.id, request = args.request, accepted = accepted, reason = reason, state = state,
        })
    end
end)
