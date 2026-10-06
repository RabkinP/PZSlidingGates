# SlidingGates: implementation status

Updated 2026-10-06. The user's current singleplayer playtest reports that gates
appear to work. This is not a dedicated-server or two-client verification.

## Implemented

- Manual chain-link gates in two- and four-cell widths; integrated assembly is
  N-right, extending along world -X.
- Animated leaves, static posts/rails and optional decorative drive model.
- Opening collision transfers cell by cell; hidden physics carriers block vehicles.
- Construction recipes, welding skill/health bonus and native model build cursor.
- Queued mouse/menu toggles, vehicle obstruction checks and interrupted-motion recovery.
- Whole-assembly destruction/dismantling with bounded material recovery.
- RU/EN recipe and tooltip translations.
- Debug spawn/remove tools are available only with the game's debug mode enabled.
- Stable gate type IDs, models, material budgets and clip lengths live in
  `mod/SlidingGates/42/media/lua/shared/SG_GateTypes.lua`.

The four-cell base health is 450, plus 50 per welding level. Existing saved
assemblies retain their recorded health; the entity description now agrees with Lua.

## Verification

All five test scripts pass with Python and lupa:

```powershell
$env:PYTHONPATH = 'C:/Users/pavel/AppData/Local/Temp/pz-skill-validation-deps'
python tests/test_gate_widths.py
python tests/test_gate_salvage.py
python tests/test_gate_preview.py
python tests/test_gate_tiles.py
python tests/test_model_variants.py
```

The width suite also covers a car obstructing the closed master leaf with an empty
pocket and a native toggle refusal after preflight: neither can persist an open
target or trigger instantaneous recovery. This fix awaits an in-game retest of the
reported car-collision scenario.

The width suite checks both widths, motion collision boundaries, paused motion,
repeated requests, vehicle rejection including a pre-toggled slave, opaque fence
proxies, unloaded destinations, partial-chunk recovery and loss of the leaf during
motion. Recovery retains its persisted marker until all required squares and
opening doors are loaded. These are Lua mocks, not Bullet or network tests.

The installed-game tile probe passes; all eight exported leaves pass clip/travel,
weight and deployment checks. Existing geometry evidence lives in
`art/clearance_checks.json` and `art/handle_checks.json`; geometry was not rebuilt
by the stabilization changes.

## Remaining work, in order

1. Server authority and synchronization: commands, movement clock independent of
   rendering, object replication, late join, chunk loading and server restart.
2. Functional add-on drive: installation/removal recipes, electricity, car battery,
   charging, cycle consumption, linked RF remotes, sound and sandbox options.
3. W and left-opening assemblies: static placement, collision, building and tests.
4. Complete obstacle policy, keys/locks and release polish. Wood/steel styles follow v1.

Dedicated server plus two clients, coop and restart testing remain required.
Motor control and multiplayer are not enabled by the shared-definition extraction.
