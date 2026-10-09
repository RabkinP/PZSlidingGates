# SlidingGates: implementation status

Updated 2026-10-09 after the drive, remote, reverse-direction and poster work was
committed. The user reports that singleplayer works in game, including the new
features; multiplayer has not been run yet and has only mock-based verification.

## Implemented

- Gate quality (2026-10-10): welding 4–5 Low, 6–7 Medium, 8+ High for both
  widths and all four directions. Native filtered recipes show translated quality
  in parentheses and matching model previews. Quality persists in saves/MP
  snapshots; legacy gates remain High. Art, assets, mock regressions and installed
  parser probes pass; this new feature has not yet been visually checked in game.

- Manual chain-link gates in two- and four-cell widths; integrated assembly is
  N-right along world -X and W along +Y, plus reversed N (+X) and reversed W (-Y).
  R cycles N -> W -> reverse N -> reverse W during construction. W uses the
  calibrated geometry rotated in spriteModel; reversed assemblies use separate
  X-mirrored models (`*_Reverse.glb`) with positive scales, the same outward face
  and a catcher on the opposite side. Comprehensive vehicle/MP acceptance remains pending.
- Animated leaves, static posts/rails and optional decorative drive model.
- Electric motor item: an independent 30% roll after vanilla dismantling removes a
  washer, dryer or combination washer/dryer. The normal scrap output is preserved;
  only the authority rolls, once per appliance. Other appliances are excluded.
- A portable gate drive and B42 craftRecipe: Electrical 3, Welding 2,
  vanilla light and work-surface requirements, screws/nuts-and-bolts alternatives.
- Normal context-menu installation/removal on existing N/W gates in both widths.
  Shared B42 timed-action completion validates the gate instance, motion, proximity,
  skills, tools and actual inventory; installation consumes a drive and 4 fasteners.
  Removal returns the drive with its item modData; fasteners are not returned.
  Whole-assembly dismantling also returns a mounted player-installed drive once;
  destructive damage loses it.
  Drives have a normal world container accepting exactly one vanilla car battery.
  Local powered open/close actions check power and use existing motion/obstruction
  logic on the authority. Grid power takes priority and charges a healthy battery
  at 10% per game hour while loaded; battery operation costs 1% per movement after
  successful start. Blocked movements cost nothing; manual inputs stay independent.
  Removing a drive requires an empty compartment. Dismantling returns its actual
  battery with charge/condition, destruction loses it. Sandbox configuration
  remains unimplemented.
- Powered motion plays the approved synthetic gate-drive sound as a dedicated
  four-second seamless loop (steady running, no beeps or silent lead/tail).
  SP/clients play local spatial audio; only SP/server emits zombie-attracting
  noise (initial radius 20, volume 15, refreshed once per animation second).
  Manual moves, charging and failed requests remain silent. Finish, removal,
  destruction, unload, pause and the remaining-motion deadline stop audio.
  Native sound-script parsing and lifecycle/network mocks pass; listening,
  balance and actual two-client playback still require gameplay acceptance.
- A craftable RF remote (Electrical 2, screwdriver only, light/work surface) pairs
  with one installed drive; multiple remotes can share a drive. Pairing is an
  authoritative shared timed action with gate and drive identities. Inventory
  use and remappable F9 share the same activation path, selecting the nearest
  loaded gate with a carried linked remote, including bags and key rings. The
  remote uses vanilla base:fitskeyring acceptance. Range is initially
  20 cells on the same floor, independent of walls. A busy/unpowered/blocked
  nearest gate never causes a farther one to operate. Server requests validate
  possession, actual item ID, pairing, distance, state revision and power; moving
  gates reject repeats. Drive removal/reinstallation and remote transfer preserve
  pairing, a new drive at the same location does not inherit it.
  A single selected remote can be renamed through the vanilla More submenu and
  text dialog; native custom-name/item-field synchronization preserves pairing.
  `tests/test_gate_remote_rename.py` exercises the installed vanilla menu and
  callback, including grouped items, cancellation and the name-length limit.
- Custom inventory icons for the motor, drive and remote (32x32) and construction
  icons for both widths (48x48) are prepared and connected to the scripts.
  Originals, prompts and a reproducible preparation tool are retained in the repo.
  PNG/reference checks and small-size visual review pass; actual menu appearance
  still requires gameplay acceptance.
- Workshop poster: a separate Blender scene (`art/build_poster_scene.py` and
  helpers, `art/poster/`) renders `mod/SlidingGates/42/poster.png`, referenced
  from `mod.info`. Game models and clips are not modified by the poster scene.
- Opening collision transfers cell by cell; hidden physics carriers block vehicles.
- Construction recipes, welding skill/health bonus and native model build cursor.
- Queued mouse/menu toggles, vehicle obstruction checks and interrupted-motion recovery.
- E at an open retracted leaf now requests closing through the pocket proxy; moving
  gates ignore repeated proxy input. Mock checks cover N/W, blocked closing, and MP
  proximity to pocket cells. This E fix still needs gameplay confirmation.
- Whole-assembly destruction/dismantling with bounded material recovery.
- All 29 installed vanilla locales have gate/recipe/item names, drive menu labels
  and tooltips, including regional Spanish, traditional/simplified Chinese and
  Strewberrie. Each locale has the same 32 keys across six JSON files, including
  powered actions, the battery compartment and the configurable remote binding.
- Debug spawn/remove tools are available only with the game's debug mode enabled.
- Stable gate type IDs, models, material budgets and clip lengths live in
  `mod/SlidingGates/42/media/lua/shared/SG_GateTypes.lua`.
- Experimental multiplayer controller: authoritative movement/collision clock,
  replicated world parts, versioned desired-state commands, instance identity,
  proximity/floor/busy checks, resting snapshots, reload recovery and orphan cleanup.
- Construction/salvage/sledgehammer hooks now load on the authority too. Client
  interaction uses shared timed actions and explicit server commands without a
  second toggle on the timed action's server completion.

The four-cell base health is 450, plus 50 per welding level. Existing saved
assemblies retain their recorded health; the entity description now agrees with Lua.

## Verification

All fourteen test scripts pass with Python and lupa (including Lua 5.1 execution):

```powershell
$env:PYTHONPATH = 'C:/Users/pavel/AppData/Local/Temp/pz-skill-validation-deps'
python tests/test_gate_widths.py
python tests/test_gate_orientation.py
python tests/test_gate_salvage.py
python tests/test_gate_preview.py
python tests/test_gate_tiles.py
python tests/test_model_variants.py
python tests/test_gate_multiplayer.py
python tests/test_gate_drive.py
python tests/test_gate_power.py
python tests/test_gate_remote.py
python tests/test_gate_motor.py
python tests/test_gate_direction.py
python tests/test_gate_remote_rename.py
python tests/test_localization.py
```

The width suite also covers a car obstructing the closed master leaf with an empty
pocket and a native toggle refusal after preflight: neither can persist an open
target or trigger instantaneous recovery. The user confirmed this fix in game
before the multiplayer split.

The width suite checks both widths, motion collision boundaries, paused motion,
repeated requests, vehicle rejection including a pre-toggled slave, opaque fence
proxies, unloaded destinations, partial-chunk recovery and loss of the leaf during
motion. Recovery retains its persisted marker until all required squares and
opening doors are loaded. These are Lua mocks, not Bullet or network tests.

Multiplayer mocks cover server authority, explicit object transmissions, concurrent
and stale requests, identity after rebuild, proximity/floor/death checks, native
door packet correction, dedicated-server completion without render flags, restart
with a closing marker, delayed orphan cleanup, client-only requests, native animation
packet ordering, late-join resting snapshots, timeout and removed-state ordering.
Salvage is exercised in both singleplayer and server modes; construction verifies
one base create and no client-side create. Native UDP delivery is not simulated.

W tests cover both widths on SP/server, rotated carriers, vehicle/fence rejection,
cell-by-cell motion, partial-load recovery and metadata before a registry snapshot.
Preview tests check R and serialized W construction; MP checks slave-first W loading.
The recipe includes one rubber hose or any tights for roller tyres.

The installed-game tile probe passes for all 24 carriers; all ten exported leaves pass clip/travel,
weight and deployment checks. `tests/test_model_variants.py` also checks that all six
reverse models are exact X reflections (normals within 1e-3 after export
re-quantization) without winding regressions or negative scales; evidence is in
`art/reverse_checks.json`. `tests/test_gate_direction.py` covers reversed mechanics,
metadata and MP regressions on mocks. Existing geometry evidence lives in
`art/clearance_checks.json` and `art/handle_checks.json`; geometry was not rebuilt
by the stabilization changes.

The drive suite uses Lua 5.1 to check motor-source whitelisting, the 30% boundary,
failed/cancelled removal and duplicate/reentrant calls; it also checks installation
and removal on SP/server across both widths/orientations, mixed fasteners, nested
inventory, moving/distant/dead/under-skilled players, broken tools, stale identities,
item-data preservation, whole-gate salvage and client actions without world mutation.
Menu deduplication, walking/queued parameters and all Lua/translation syntax pass.
`research/probe-drive-recipe.py` parses both item definitions and the recipe using
the installed game classes; it confirms surface/light tags, three required skills,
12 inputs and one output. It does not run crafting, a game world or network delivery.
Evidence and remaining acceptance checks: `research/drive-integration.md`.

The power suite covers one-battery filtering, both widths/orientations on SP/server,
grid priority, exact successful-movement consumption, blocked/duplicate/stale/dead/
distant rejection, depleted/broken batteries, time-based charging and its clamp,
client non-mutation, empty-compartment removal and once-only battery recovery.
These checks use mocks; container UI, serialization and native network transfers
still require actual gameplay acceptance.

The RF suite covers multiple/remapped bindings, nested inventory, nearest matching
selection and explicit inventory selection, range boundary, busy/power/obstruction,
dead/wrong-floor/stale/foreign-ID rejection, transfer and drive lifecycle. Client
checks cover authority-only pairing completion, versioned request/pending/results,
grouped inventory context, primary/alternate keys, text entry and pause. Server
command routing is checked at 10-cell distance. The native recipe probe parses the
remote item and confirms five inputs, one skill, surface/light and one output.
Native input events, item synchronization, saves and two-client RF gameplay still
require acceptance.

## Remaining work, in order

1. Validate the experimental multiplayer controller in a dedicated server with two
   clients and coop; test all inputs, construction, destruction, restart and network
   ordering. Recheck singleplayer after the shared-module split.
2. Gameplay acceptance for motor salvage, drive crafting, light/surface requirements,
   installation/removal, battery container UI/save/load/transfers, grid/generator
   power, charging, powered movement, motor sound/noise and item replication. Then implement
   sandbox options. Include RF pairing, inventory
   use and F9 in the dedicated-server/two-client acceptance run.
3. Validate W and reversed assemblies' appearance/collision with vehicles in game,
   and in multiplayer.
4. Complete obstacle policy, keys/locks and release polish. Wood/steel styles follow v1.

Dedicated server plus two clients, coop and restart testing remain required.
Sandbox configuration remains unimplemented. Multiplayer code is experimental until the
real server/client acceptance checklist passes.
