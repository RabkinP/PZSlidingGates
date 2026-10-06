# B42 multiplayer integration

Inspected 2026-10-06 in the installed game at
`E:/SteamLibrary/steamapps/common/ProjectZomboid`.
JAR SHA256 matches the model audit:
`E1A69EB743EDE60B213A0FE7F8B83D4FCAB773036D256CC4543A336F3B058A33`.
The following observations come from installed Lua files, which can change
independently of the JAR. They are preparation, not verified MP support.

## Installed Lua contracts inspected

- `media/lua/shared/TimedActions/ISOpenCloseDoor.lua`: vanilla door action lives
  in shared; `perform` completes the local queue, `complete` toggles the door with
  `self.character`. Our custom action now lives in shared. In MP its server
  completion is a no-op; the client's `perform` sends a versioned desired-state
  command, avoiding a second native/server toggle.
- `media/lua/client/BuildingObjects/TimedActions/ISBuildAction.lua`, `perform`:
  its client branch returns before `self.item:create`. Multiplayer construction
  must follow the actual entity action/transaction path; a client-only create hook
  cannot be assumed to run on the server.
- `media/lua/server/BuildingObjects/ISBuildIsoEntity.lua`, `setInfo`:
  placed objects are sent with `transmitCompleteItemToClients`. Assembly
  constructors now transmit their fully tagged doors/static objects/colliders
  from the authority; server leaf metadata uses `transmitModData`.
- `media/lua/shared/Moveables/ISMoveableSpriteProps.lua`: movable/scrap logic
  has separate client and server transmission branches. Our override must apply on
  the authority executing removal; loot and assembly cleanup must happen once.
- `media/lua/server/ClientCommands.lua`: returns immediately on a client and
  handles command dispatch on the authority.

## Implemented split (experimental)

The shared type definitions now provide stable IDs, entity mappings, width,
materials, health, model names and clip duration to both controllers.

World mutation is separated from the client controller:

- Authority owns registry, target state, motion progress, collision, construction,
  material recovery and eventual drive energy. It cannot end movement using
  `leaf:isAnimating()`: dedicated servers do not play model animations.
- Clients request actions and render accepted changes. They must not construct
  blockers/colliders independently or receive authority to award material drops.
- Server requests validate gate identity, loaded assembly, player floor/proximity,
  busy state, obstruction and eventual permissions/drive inputs.
- State updates need ordering and a stable assembly identity beyond coordinates
  so a delayed command cannot affect newly rebuilt gates at the same location.
- Late joins receive the resting pose and current authoritative collision; stale
  animation requests must not replay on a newly loaded assembly.
- Mouse/menu, Java E-key toggles, building, destruction and dismantling need
  separate integration tests. A sendClientCommand handler alone does not cover them.

Files:

- `shared/SG_GateCommon.lua`: read-only gate lookup, footprint, pose and proximity.
- `shared/SG_GateCore.lua`: early-return on network clients; authoritative assembly,
  collision transfer, unique persisted instance IDs, revisions, motion and recovery.
- `server/SG_GateServer.lua`: validated desired-state commands and state/snapshot/results.
- `client/SG_GateNetwork.lua`: command-only interaction, native animation packet ordering,
  loaded-square snapshots, stale-state rejection and pending-command refresh.
- `shared/SG_GateConstruction.lua`, `SG_GateSalvage.lua`, `SG_GateLifecycle.lua`:
  construction, scrapping and sledgehammer completion on the authority.
- `shared/SG_GateToggleAction.lua`: shared class for B42 timed-action reconstruction;
  captured instance prevents an old queued action from operating a replacement gate.

`zombie/core/BuildAction.class` and `zombie/network/packets/NetTimedActionPacket.class`
were extracted from the fingerprinted JAR and inspected with CFR. `BuildAction`
serializes the builder constructor's named parameters; `parse` reconstructs its
Lua class, and `perform` emits `OnProcessAction("build", player, argTable)`.
Installed `shared/ActionManager.lua`, `Actions.build`, sets `item.character` and
calls `item:create`. The construction wrapper is therefore shared and preserves
the original `ISBuildIsoEntity:new(character, objectInfo, nSprite, containers, logic)`
parameter names/order. Base `create` validates and consumes materials; assembly
creation follows the intercepted placeholder-placement stage, once.

Current `IsoObjectAnimations.addObject` returns immediately on GameServer.server;
the track speed on clients is 1.5 and update uses `GameTime.getTimeDelta`.
Server motion uses the same delta/rate and finishes by elapsed clip time, never
the native animating flag. `IsoThumpable.syncIsoObjectReceive` invokes private
`PlayAnimation` on an open-state change, then `OnContainerUpdate`. Clients do not
pre-toggle the leaf on a moving state notification, which would suppress that
native animation. Snapshot/resting-pose behavior and packet ordering still need
real gameplay verification.

Unvalidated native door packets are corrected on the authority, preserving its
target and per-cell collision progress. Java E input is converted into an explicit
desired-state command on the client. Temporary native client prediction and its
visual correction must be assessed in the live two-client test.

`tests/test_gate_multiplayer.py` exercises separate authority/client Lua runtimes,
including a two-client protocol simulation. These mocks verify controller logic,
not B42's UDP delivery, Java/Lua exposure or Bullet/GL behavior.

## Acceptance tests before declaring MP ready

Dedicated server and two clients: build once with materials consumed once;
toggle from each input path; simultaneous requests; near/far and floor checks;
cars and zombies; client disconnect during motion; late join; chunk unload/reload;
server save/restart mid-motion; dismantle/destroy without duplicate loot.
