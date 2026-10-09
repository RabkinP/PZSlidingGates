"""Create a deterministic, original gate-drive listening prototype (no samples)."""
from array import array
import math
from pathlib import Path
import random
import wave

ROOT = Path(__file__).resolve().parents[1]
RATE = 48000
DURATION = 8.0
START, STOP = 0.4, 6.4
TAU = math.tau


def smooth(x):
    x = max(0.0, min(1.0, x))
    return x*x*(3.0-2.0*x)


def synth():
    rng = random.Random(91827)
    rotor = gear = 0.0
    low = mid = fine = 0.0
    samples = []
    for i in range(round(RATE*DURATION)):
        t = i/RATE
        elapsed = t-START
        active = START <= t < STOP
        engage = smooth(elapsed/0.35)
        disengage = smooth((STOP-t)/0.28)
        level = engage*disengage if active else 0.0
        speed = (0.48+0.52*engage)*(0.35+0.65*disengage)
        speed *= 1+0.006*math.sin(TAU*0.73*t)+0.003*math.sin(TAU*2.1*t)
        rotor += TAU*29.0*speed/RATE
        gear += TAU*435.0*speed/RATE
        white = rng.uniform(-1, 1)
        low += 0.018*(white-low)
        mid += 0.11*(white-mid)
        fine += 0.35*(white-fine)
        # Low electric hum plus housing vibration, rather than an engine exhaust.
        electrical = 0.18*math.sin(TAU*100*t)+0.035*math.sin(TAU*200*t)
        housing = 0.095*math.sin(rotor*2)+0.065*math.sin(rotor*4)+0.025*math.sin(rotor*7)
        mesh = (0.064*math.sin(gear)+0.023*math.sin(gear*2)+0.009*math.sin(gear*3))
        mesh *= 0.88+0.12*math.sin(rotor)
        # Slight periodic rack/roller chatter, not random loud hammer blows.
        tooth = max(0, math.sin(rotor*0.42))**14
        chatter = tooth*(0.027*math.sin(TAU*930*t)+0.014*math.sin(TAU*1630*t))
        friction = 0.18*low+0.06*(mid-low)+0.012*(fine-mid)
        flutter = 0.94+0.04*math.sin(rotor)+0.02*math.sin(rotor*0.31)
        value = level*flutter*(electrical+housing+mesh+chatter+friction)
        samples.append(value)
    # Leave ample headroom and avoid hard clipping. Mono spatial playback asset.
    gain = 0.72/max(abs(v) for v in samples)
    pcm = array('h', (round(v*gain*32767) for v in samples))
    path = ROOT/'art/audio/gate-drive-prototype-v2.wav'
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes(pcm.tobytes())
    rms = math.sqrt(sum((v/32768)**2 for v in pcm)/len(pcm))
    print(f'{path}: {DURATION}s mono PCM16/{RATE}Hz, peak -2.9 dBFS, RMS {20*math.log10(rms):.1f} dBFS')


if __name__ == '__main__':
    synth()
