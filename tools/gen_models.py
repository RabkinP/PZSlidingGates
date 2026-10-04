"""Generate mod/.../media/scripts/SG_models.txt (model scripts + spriteModels).

Placement formula (verified in game, see research/vanilla-gates.md):
  translate_x = -0.5 - b + k      (b: Blender X of the part, k: carrier shift towards -x in cells)
  translate_z = -0.5 + y_b + SHIFT_Z
SHIFT_Z moves the whole assembly across the fence line towards the inner side (+z = south for N-edge gates)
so posts/brackets stand beside the fence instead of inside it.

Usage:  python tools/gen_models.py [SHIFT_Z]
"""
import os, sys

SHIFT_Z = float(sys.argv[1]) if len(sys.argv) > 1 else 0.12
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mod", "SlidingGates", "42", "media", "scripts", "SG_models.txt")

LEAVES = ["SG_ChainLink_N_Left", "SG_ChainLink_N_Right", "SG_ChainLink_W_Left", "SG_ChainLink_W_Right"]
STATIC = ["SG_GuidePost", "SG_CatcherPost", "SG_Rail", "SG_Drive"]
# (name, Blender X b, carrier shift k, Blender Y y_b)
PLACE = {
    "SG_CatcherPost": (-0.04, 0, 0.0),
    "SG_GuidePost": (2.04, 2, 0.0),
    "SG_Rail": (0.0, 0, 0.0),       # per-cell piece: b == k for every carrier, so -0.5
    "SG_Drive": (2.0, 2, -0.22),
}

def f(v):
    return ("%.4f" % v).rstrip("0").rstrip(".") if "." in ("%.4f" % v) else "%.4f" % v

def sprite_model(name, model, tx, tz, scale="1.0", anim=None):
    s = f"    spriteModel {name}\n    {{\n        modelScript = Base.{model},\n"
    s += f"        translate = {f(tx)} 0.0 {f(tz)},\n        rotate = 0.0 0.0 0.0,\n        scale = {scale},\n"
    if anim:
        s += f"        animation = Open,\n        animationTime = {anim},\n"
    return s + "    }\n\n"

o = "module Base\n{\n"
for n in LEAVES:
    o += f"""    animationsMesh {n}
    {{
        meshFile = IsoObject/{n},
        keepMeshAnimations = true,
    }}

    model {n}
    {{
        mesh = IsoObject/{n},
        texture = IsoObject/SG_ChainLink_Atlas,
        animationsMesh = {n},
        shader = door,
        static = false,
        undoCoreScale = true,
    }}

"""
for n in STATIC:
    o += f"""    model {n}
    {{
        mesh = IsoObject/{n},
        texture = IsoObject/SG_ChainLink_Atlas,
        shader = door,
        static = true,
        undoCoreScale = true,
    }}

"""
tz0 = -0.5 + SHIFT_Z
for n in LEAVES:
    for st, t in (("Closed", "0.0"), ("Open", "2.0")):
        o += sprite_model(f"{n}_{st}", n, -0.5, tz0, anim=t)
for n in ("SG_ChainLink_N_Right", "SG_ChainLink_N_Left"):   # gate carriers one cell left of the model origin
    for st, t in (("Closed", "0.0"), ("Open", "2.0")):
        o += sprite_model(f"{n}_G_{st}", n, 0.5, tz0, anim=t)
for n in STATIC:
    b, k, yb = PLACE[n]
    o += sprite_model(f"{n}_Static", n, -0.5 - b + k, -0.5 + yb + SHIFT_Z)
o += sprite_model("SG_Hidden", "SG_Rail", 0.0, 0.0, scale="0.001")
o += "}\n"
open(OUT, "w", encoding="utf-8").write(o)
print("written", os.path.normpath(OUT), "SHIFT_Z =", SHIFT_Z)
