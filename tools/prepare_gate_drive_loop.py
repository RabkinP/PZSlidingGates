"""Make a seamless loop from the approved synthetic motor's steady section."""
from array import array
import math
from pathlib import Path
import wave

ROOT = Path(__file__).resolve().parents[1]
RATE = 48000
LOOP_SECONDS = 4
CROSSFADE = 0.15


def save(path, samples):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes(samples.tobytes())


def main():
    with wave.open(str(ROOT/'art/audio/gate-drive-prototype-v3.wav'), 'rb') as wav:
        assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 2, RATE)
        source = array('h')
        source.frombytes(wav.readframes(wav.getnframes()))
    fade = round(CROSSFADE*RATE)
    start = round(0.75*RATE)
    # Use only steady running, with extra material for the circular crossfade.
    section = source[start:start+LOOP_SECONDS*RATE+fade]
    assert len(section) == LOOP_SECONDS*RATE+fade
    loop = section[fade:-fade]
    for i in range(fade):
        blend = (1-math.cos(math.pi*i/(fade-1)))/2
        loop.append(round(section[-fade+i]*(1-blend)+section[i]*blend))
    # Choose a near-zero start within the unmodified section, for a clean onset.
    offset = min(range(RATE//2, RATE), key=lambda i: abs(loop[i]))
    loop = loop[offset:]+loop[:offset]
    assert len(loop) == LOOP_SECONDS*RATE and max(abs(v) for v in loop) < 32767
    master = ROOT/'art/audio/gate-drive-loop-v1.wav'
    save(master, loop)
    save(ROOT/'art/audio/gate-drive-loop-preview.wav', loop+loop)
    save(ROOT/'mod/SlidingGates/42/media/sound/SG_GateMotorRunning.wav', loop)
    steps = sorted(abs(loop[i]-loop[i-1]) for i in range(1, len(loop)))
    seam = abs(loop[0]-loop[-1])
    assert seam <= steps[round(len(steps)*0.99)]
    print(f'4s mono PCM16/{RATE}Hz loop; start={loop[0]}, wrap step={seam}, normal p99 step={steps[round(len(steps)*0.99)]}')
    print(master)


if __name__ == '__main__':
    main()
