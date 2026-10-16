"""Outer-side placement: the calibrated assembly mirrored across its fence line.

GLB evidence: posts are centred on local Z=0 (Blender Y=0, the fence line) and placed with
the perpendicular translate -0.38; the drive's pinion tip meets the rack only with its own
-0.6, so every model's fence plane is translate -0.38. An X-mirrored model rotated 180 degrees
equals the original reflected through its origin's perpendicular plane. Reflecting through
the fence plane therefore keeps the edge-parallel translate and maps perp -> 2*F - perp.
No negative scales. W (rotate.y=90) uses translate X as its perpendicular component.
"""
FENCE = -0.38


def mirror_script(name):
    """Base.SG_ChainLink_N_Right <-> Base.SG_ChainLink_N_Reverse; Base.SG_Rail <-> Base.SG_Rail_Reverse."""
    if '_N_Right' in name:
        return name.replace('_N_Right', '_N_Reverse')
    if '_N_Reverse' in name:
        return name.replace('_N_Reverse', '_N_Right')
    return name[:-len('_Reverse')] if name.endswith('_Reverse') else name + '_Reverse'


def fmt(value):
    text = f'{value:.4f}'.rstrip('0').rstrip('.')
    return '0' if text in ('-0', '') else text


def outer(fields):
    """Return the outer-side copy of a spriteModel/tile binding dict (string values)."""
    result = dict(fields)
    rx, ry, rz = map(float, fields['rotate'].split())
    tx, ty, tz = map(float, fields['translate'].split())
    if rx or rz or ry not in (0, 90):
        raise ValueError(f'unexpected rotation {fields["rotate"]}')
    if ry == 0:
        tz = 2 * FENCE - tz
    else:
        tx = 2 * FENCE - tx
    result['modelScript'] = mirror_script(fields['modelScript'].strip())
    result['rotate'] = f'0 {fmt(ry + 180)} 0'
    result['translate'] = f'{fmt(tx)} {fmt(ty)} {fmt(tz)}'
    return result
