# Sliding Gates icons

The five originals in `generated/` were created with the built-in image generator,
one agent at a time. Prompts and reference roles are in `PROMPTS.md`.

Run `python tools/build_icons.py` from the repository to reproduce the game PNGs.
This preparation preserves the original artwork and alpha: bounds are measured
at alpha >= 16 to ignore faint stray pixels, then premultiplied-alpha Lanczos
resampling fits the subject inside a square with a two-pixel minimum margin.
It does not recolour, sharpen or repaint the images.

| Consumer | Texture in `mod/SlidingGates/42/media/textures` | Canvas |
| --- | --- | --- |
| ElectricMotor | Item_SG_ElectricMotor.png | 32 × 32 |
| GateDrive | Item_SG_GateDrive.png | 32 × 32 |
| GateRemote | Item_SG_GateRemote.png | 32 × 32 |
| ES_SlidingGateChainLink2 | SG_BuildGate2.png | 48 × 48 |
| ES_SlidingGateChainLink4 | SG_BuildGate4.png | 48 × 48 |

The installed vanilla `UI2.pack` uses 32 × 32 untrimmed canvases for Generator,
RemoteCrafted and CarBatteryCharger, and 48 × 48 for Build_ShortWireGate.
`ISInventoryPane` limits inventory rendering to 32 pixels.

`prepared/contact-sheet.png` shows 32/48/64-pixel variants on dark backgrounds
at actual size and light backgrounds enlarged 2×. Visual review confirms distinct
motor/drive silhouettes, the remote's red button and ring, and different gate
widths. Mesh detail naturally diminishes at small sizes.

PNG dimensions, RGBA, transparent borders and script references were checked.
The installed game's native drive/remote script parser also passed after the icon
changes. These checks do not establish appearance in a running game; inventory,
crafting and construction menus still need gameplay acceptance.
