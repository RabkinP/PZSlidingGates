# B42 multiplayer integration groundwork

Inspected 2026-10-06 in the installed game at
`E:/SteamLibrary/steamapps/common/ProjectZomboid`.
JAR SHA256 matches the model audit:
`E1A69EB743EDE60B213A0FE7F8B83D4FCAB773036D256CC4543A336F3B058A33`.
The following observations come from installed Lua files, which can change
independently of the JAR. They are preparation, not verified MP support.

## Installed Lua contracts inspected

- `media/lua/shared/TimedActions/ISOpenCloseDoor.lua`: vanilla door action lives
  in shared; `perform` completes the local queue, `complete` toggles the door with
  `self.character`. Our custom action currently lives only in client.
- `media/lua/client/BuildingObjects/TimedActions/ISBuildAction.lua`, `perform`:
  its client branch returns before `self.item:create`. Multiplayer construction
  must follow the actual entity action/transaction path; a client-only create hook
  cannot be assumed to run on the server.
- `media/lua/server/BuildingObjects/ISBuildIsoEntity.lua`, `setInfo`:
  placed objects are sent with `transmitCompleteItemToClients`. Our assembly
  constructors currently add objects locally and need an explicit replication audit.
- `media/lua/shared/Moveables/ISMoveableSpriteProps.lua`: movable/scrap logic
  has separate client and server transmission branches. Our override must apply on
  the authority executing removal; loot and assembly cleanup must happen once.
- `media/lua/server/ClientCommands.lua`: returns immediately on a client and
  handles command dispatch on the authority.

## Required split

The shared type definitions now provide stable IDs, entity mappings, width,
materials, health, model names and clip duration to both future controllers.

The next change must separate world mutation from rendering:

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

## Acceptance tests before declaring MP ready

Dedicated server and two clients: build once with materials consumed once;
toggle from each input path; simultaneous requests; near/far and floor checks;
cars and zombies; client disconnect during motion; late join; chunk unload/reload;
server save/restart mid-motion; dismantle/destroy without duplicate loot.
