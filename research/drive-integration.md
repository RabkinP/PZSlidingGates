# Drive crafting and installation: installed B42 contracts

## Vanilla remote renaming (2026-10-09)

The installed `ISInventoryPaneContextMenu.createMenu` marks keys, key rings and
inventory containers as `tests.canBeRenamed`. There is no generic rename-item tag
in that Lua eligibility check. `SG_GateRemoteRename.lua` extends only the input
to `doMoreContextMenu` for a single selected `SlidingGates.GateRemote`, including
grouped inventory entries. The original method creates More → Rename and calls
vanilla `onRenameBag`; `onRenameBagClick` validates a nonempty name of at most
28 bytes, calls `setName`, `setCustomName(true)` and `syncItemFields`, and refreshes
inventory panels. No replacement dialog, item category/tag or pairing data changes.

## Battery compartment and local powered operation

`SG_GatePower.lua` attaches an `ItemContainer` to the existing drive object before
its initial replication, using `ItemContainer.new(type, square, parent)` followed
by `setContainer`. The installed B42 class has constructors with zero arguments,
an integer ID, `(String, IsoGridSquare, IsoObject)` and
`(int, String, IsoGridSquare, IsoObject)`; the five-argument call still present in
vanilla `server/Camping/SCampfireGlobalObject.lua:addContainer` is unsupported.
Verified 2026-10-09 by CFR extraction from the installed JAR (SHA256
`E1A69EB743EDE60B213A0FE7F8B83D4FCAB773036D256CC4543A336F3B058A33`),
`ItemContainer` constructors, and a gameplay exception in `console.txt` at
`SG_GatePower.ensureContainer`. The Lua mock rejects surplus constructor arguments.
Capacity 5 fits
one of the three weight-5 vanilla car batteries. The additional accept function
requires a vanilla full type and DrainableComboItem and rejects a second item.
The installed `ItemContainer.isItemAllowed` invokes the named Lua function with
container and item and requires Boolean.TRUE (CFR, current JAR, lines 362–382).
Restore this function on LoadGridsquare because its setter is runtime state;
legacy drives receive an empty compartment. Every locale includes the native
`IGUI_ContainerTitle_sg_drive_battery` title used by ISInventoryPage.

Native `getCurrentUsesFloat`/`setUsedDelta` hold the charge in the item; server
changes use the vanilla `sendItemStats` entry point. Grid power is checked at the
drive square. Charge updates run EveryOneMinute only on the authority, with an
elapsed-time cap of one minute and a fresh clock after square loading. No offline
or unloaded charging is claimed. Local powered movement uses a separate shared
B42 timed action, captures gate identity and desired state, never mutates from a
client completion, and reuses SGGate.toggle obstruction checks. Each successful
battery movement reserves 1%; supply loss does not interrupt an accepted move.
Grid charging is initially 10% per game hour. Sound and sandbox values remain
separate stages; RF control is described below.

`tests/test_gate_power.py` checks both widths and N/W on SP/server; battery filter,
power priority, successful/blocked/duplicate movements, charge limits, elapsed
time, authority, nonempty removal and once-only original-item salvage. All ten
test scripts pass. Actual container transfers between two clients, save/load,
legacy migration, generator coverage and UI still require gameplay verification.

## RF remote and native key binding

The remote is a distinct normal item, without vanilla `RemoteController = true`
to avoid adding explosives-controller actions. Its icon and WorldStaticModel reuse
the installed RemoteCrafted item's `RemoteCrafted`/`RemoteController` assets;
`generated/models_items.txt` registers `WorldItems/RemoteController`, scale 0.02.
This is the native world-item path; no gate geometry/model scripts were altered
and its dropped-item appearance still needs gameplay acceptance.

The recipe follows the vanilla remote's TV-remote/cordless-phone/pager alternatives,
adds a radio transmitter, two electronics scrap and one electric wire, and uses
only an unbroken retained screwdriver. Native parsing confirms surface/light,
Electrical 2, time 100, five inputs and one output. It is not a learned recipe.

Pairing uses a shared B42 timed action with primitive gate ID, gate instance,
remote item ID and drive identity fields. Each installed drive gets an identity
preserved in its portable item data. The drive records remote keys mapped to actual
item IDs, so copying another remote's modData does not authorize a different item.
Server use checks the actual item in the sender's recursive inventory, association,
gate instance/revision, range/floor, busy/power and existing obstruction logic.
Inventory use and F9 select the same activation path; F9 chooses the nearest
loaded matching gate, not the nearest powered gate. Range is 20 cells on the same
floor without RF line-of-sight checks. Failed nearest gates never fall through to
farther gates. The ordinary state/result channel retains pending-command handling.

Current `InventoryItem.syncItemFields` routes a server update to the player whose
inventory contains the item, including nested containers. The installed
`SyncItemFieldsPacket` writes modData and `processModData` restores it on receipt;
pairing therefore uses this entry point, rather than assuming ItemStats includes
custom keys. CFR sources were extracted from the fingerprinted installed JAR.

The remote also carries `base:fitskeyring`. The installed
`server/Items/AcceptItemFunction.lua:KeyRing` accepts keys or items with
`ItemTag.FITS_KEY_RING`; vanilla key-ring variants all use this filter. Key rings
are InventoryContainer items, so the existing recursive remote lookup handles
pairing and use while the remote is inside the ring, without replacing the filter.

The binding is appended to vanilla `keyBinding` before MainOptions.loadKeys;
MainOptions registers it through Core.addKeyBinding and translates its section and
name via UI_optionscreen_binding_*. The handler uses Core.isKey, which honors
primary/alternate keys and modifier rules, and ignores text entry and pause.
The current vanilla keyBinding.lua does not assign F9. No ModOptions dependency.

`tests/test_gate_remote.py` covers SP/server across 2/4 and N/W, pairing/rebinding,
nested inventory, copied metadata, nearest/explicit selection, range boundary,
busy/power/obstruction, item transfer, drive removal/reinstallation/rebuild, native
action fields, client command/pending/result, inventory context, key remapping,
text/pause and server routing at 10-cell distance. Save/restart with paired remotes,
actual nested-item synchronization, UI keys and dedicated-server/two-client gameplay
remain acceptance checks.

Game root: `E:/SteamLibrary/steamapps/common/ProjectZomboid`.
JAR SHA256: `E1A69EB743EDE60B213A0FE7F8B83D4FCAB773036D256CC4543A336F3B058A33`.
Relevant classes were extracted from this JAR and inspected with CFR from
`E:/git/PZMining/tools/cfr.jar`; older PZMining class copies are not the authority.

## Appliance dismantling

Parsed the installed binary `newtiledefinitions.tiles` and the noise property patch.
`appliances_laundry_01_0..3`, `_4..7` and `_12..15` are the combination appliance,
washer and dryer. They have `CanScrap`, primary `Material=Fridge`, and their own
`IsoCombinationWasherDryer` / `IsoClothingWasher` / `IsoClothingDryer` types.
The vanilla `ISMoveableDefinitions` Fridge scrap definition uses the blowtorch,
welding mask and MetalWelding. Pickup skill level is a separate contract.

Current `ISMoveableSpriteProps.scrapObjectInternal` removes the world object before
generating its material rolls. Its public scrap method may return nil on success.
Therefore the motor hook caches the square and checks removal, not a boolean return
or a positive material yield. It uses a fixed sprite whitelist, claims both successful
and unsuccessful motor rolls once, and leaves vanilla materials untouched. It does
not mutate these sprites or the shared Fridge/Electric material definitions.
The hook runs on SP/server, never a network client, and tolerates repeated boot hooks
and recursive invocation. It can coexist with the gate-specific scrap wrapper.

## Crafting conditions

Current `CraftRecipe.isAnySurfaceCraft()` and `canBeDoneInDark()` read recipe tags.
`HandcraftLogic.createCachedRecipeInfo` requires an assigned generic crafting surface
within vanilla workbench range for AnySurfaceCraft. `CraftRecipeData.consumeInputsInternal`
rejects recipes without CanBeDoneInDark when the player is too dark to read. No custom
electric-light requirement is used.

`research/probe-drive-recipe.py` uses the installed ScriptManager/ScriptBucketCollection
loader and native CraftRecipe parser with initialized perks/random state, without a
game world. Both new items register. Parsed flags: AnySurfaceCraft=true,
CanBeDoneInDark=false; 3 required skills; 3 XP awards; time=500; 12 inputs; 1 output.
Saved parser output: `research/render-audit/drive-recipe-native.txt`.
This probe does not consume real inventory, initialize an actual workbench, load Lua
translations/textures or demonstrate the full in-game crafting transaction.

## Installation transaction

`zombie.core.NetTimedAction.set` reads constructor parameter names from the Lua
`new` prototype and serializes matching fields on the action. The shared
`ISSlidingGateDrive:new(character, gateId, instance, installing)` preserves those
names and values, including the false removal flag. Current vanilla shared actions,
including ISPlaceCarBatteryChargerAction, consume/award inventory and mutate world
objects in `complete`, while `perform` advances the client queue.

The drive action follows this native completion path; it does not also send a custom
installation command. Authority completion rechecks identity, player floor/proximity
to the calibrated guide-post cell, skills, unbroken tools, motion and actual inventory.
Screws and nuts/bolts can be mixed; nested inventory items are removed from their own
containers and replicated with vanilla inventory helpers. The drive model uses the
existing width/orientation placement. Its item modData is tagged before broadcasting
the new object. Installation/removal publishes a new gate revision; ordinary object
transmission supplies the model to clients, including late joins.

Removal requires an empty battery compartment, returns the drive and preserves
item modData. Power/battery/RF gameplay acceptance remains pending. Whole-gate
dismantling returns a player-installed drive and its actual
battery once, while destructive damage loses both. Mounting fasteners are consumed
and never refunded. Initial action durations
are 180 for installation and 120 for removal; both require Electrical 1/Mechanics 1.

## Required gameplay acceptance

### Translation loader audit (2026-10-09)

Installed game JAR SHA256:
`E1A69EB743EDE60B213A0FE7F8B83D4FCAB773036D256CC4543A336F3B058A33`.
Decompiled `zombie.core.Translator$1` registers `IG_UI`, not `IGUI`, as
the JSON category basename. Renamed all 29 battery compartment translation files
to `IG_UI.json`; the key remains `IGUI_ContainerTitle_sg_drive_battery`.
The game log had reported this key missing with the previous filename.

`zombie.scripting.objects.XuiSkinScript` handles entity UI `DisplayName` by
removing spaces and calling `Translator.getRecipeName`. Gate XUI styles now use
the existing `SlidingGateChainLink2` / `SlidingGateChainLink4` recipe keys instead
of English titles whose stripped forms did not match any translation.
Dismantling names also use these keys through vanilla `Translator.getRecipeName`,
so already placed gates are named in the current locale.

`tests/test_localization.py` checks the loader category filenames, all locale key
sets, nonempty values, formatting tags and player-facing script references.
`tests/test_gate_salvage.py` checks translated names for both gate widths.
Debug-only `SG Gate` / `SG Proto` tool labels still use English; ordinary gameplay
menus have no identified missing mod keys. In-game visual acceptance is pending.

Localization covers all 29 installed `Translate/*/language.json` locales (174 mod
JSON files, 32 keys per locale). Compared every locale's key set, markup and numeric
requirements against English; checked nonempty UTF-8 values. Spanish regional
variants have their own files, Chinese scripts are translated separately, and the
Strewberrie locale follows the vanilla word-replacement style with markup preserved.

- Dismantle each of the three appliances; retain ordinary metal/electrical scrap;
  confirm no motor on cancellation, failed removal, unrelated furniture or destruction.
- Craft the drive with both fastener alternatives and a mix, exact gas/rod usage,
  required skills, a nearby work surface and daylight/artificial light; reject darkness
  and absent surface. Confirm recipe/item translations and borrowed vanilla icons.
- Install/remove on 2/4-cell N/W gates; walk to the guide post; cancel, move away,
  remove tools/materials during the action, replace the gate and issue competing actions.
- Save/reload an installed drive; recover it through removal and whole-gate dismantling;
  ensure no duplicate equipment or recipe-component refunds.
- Dedicated server/two clients and coop: action reconstruction, material consumption
  once, object/item replication, late join, simultaneous installation/removal and restart.

Lua 5.1 mocks and native script parsing pass; these do not establish gameplay,
Bullet/GL appearance or real network packet behavior.
