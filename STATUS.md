# SlidingGates: implementation status

Updated 2026-10-07. The user confirmed the singleplayer car-obstruction fix in
game. The subsequent multiplayer implementation has only mock-based verification;
dedicated-server/two-client gameplay and singleplayer regression still need a run.

## Implemented

- Manual chain-link gates in two- and four-cell widths; integrated assembly is
  N-right along world -X and W along +Y, selected with R during construction.
  W uses the same calibrated geometry rotated in spriteModel. The user confirmed
  R rotation works in game; comprehensive vehicle/MP acceptance remains pending.
- Animated leaves, static posts/rails and optional decorative drive model.
- Opening collision transfers cell by cell; hidden physics carriers block vehicles.
- Construction recipes, welding skill/health bonus and native model build cursor.
- Queued mouse/menu toggles, vehicle obstruction checks and interrupted-motion recovery.
- E at an open retracted leaf now requests closing through the pocket proxy; moving
  gates ignore repeated proxy input. Mock checks cover N/W, blocked closing, and MP
  proximity to pocket cells. This E fix still needs gameplay confirmation.
- Whole-assembly destruction/dismantling with bounded material recovery.
- RU/EN recipe and tooltip translations.
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

All seven test scripts pass with Python and lupa (including Lua 5.1 execution):

```powershell
$env:PYTHONPATH = 'C:/Users/pavel/AppData/Local/Temp/pz-skill-validation-deps'
python tests/test_gate_widths.py
python tests/test_gate_orientation.py
python tests/test_gate_salvage.py
python tests/test_gate_preview.py
python tests/test_gate_tiles.py
python tests/test_model_variants.py
python tests/test_gate_multiplayer.py
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

The installed-game tile probe passes for all 24 carriers; all eight exported leaves pass clip/travel,
weight and deployment checks. Existing geometry evidence lives in
`art/clearance_checks.json` and `art/handle_checks.json`; geometry was not rebuilt
by the stabilization changes.

## Remaining work, in order

1. Validate the experimental multiplayer controller in a dedicated server with two
   clients and coop; test all inputs, construction, destruction, restart and network
   ordering. Recheck singleplayer after the shared-module split.
2. Functional add-on drive: installation/removal recipes, electricity, car battery,
   charging, cycle consumption, linked RF remotes, sound and sandbox options.
3. Validate W assembly appearance/collision in game; add the opposite opening
   direction when requested (left-opening assemblies remain unimplemented).
4. Complete obstacle policy, keys/locks and release polish. Wood/steel styles follow v1.

Dedicated server plus two clients, coop and restart testing remain required.
Motor control remains unimplemented. Multiplayer code is experimental until the
real server/client acceptance checklist passes.
