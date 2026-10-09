"""Decode selected vanilla FSB samples with the installed FMOD library.

Usage: python research/extract-motor-audio.py OUTPUT_DIRECTORY
Exports raw sample WAVs, not the complete Studio event mix/effects.
"""
import ctypes as C
from array import array
import json
from pathlib import Path
import struct
import sys
import tempfile
import wave

GAME = Path('E:/SteamLibrary/steamapps/common/ProjectZomboid')
BANK = GAME/'media/sound/banks/Desktop/ZomboidSound.bank'
WANTED = {
    'object_clothing_dryer_loop': 'ClothingDryerRunning',
    'object_clothing_washer_loop_fast': 'ClothingWasherRunning',
    'object_clothing_washer_loop_slow': 'ClothingWasherRunning',
    'object_clothing_washer_full_load_loop': 'ClothingWasherRunning',
    'object_clothing_washer_full_load_fast_loop': 'ClothingWasherRunning',
    'object_generator_loop': 'GeneratorLoop',
}


def main():
    output = Path(sys.argv[1]).resolve()
    raw = BANK.read_bytes()
    base = raw.index(b'FSB5')
    version, count, headers, names_size, data_size, mode = struct.unpack_from('<6I', raw, base+4)
    assert version == 1
    names_start = base+60+headers
    selected = []
    for index in range(count):
        offset = struct.unpack_from('<I', raw, names_start+index*4)[0]
        start = names_start+offset
        name = raw[start:raw.index(b'\0', start)].decode('utf8')
        if name in WANTED:
            selected.append((index, name))
    assert len(selected) == len(WANTED)
    lib = C.CDLL(str(GAME/'fmod.dll'))

    def api(name, args):
        function = getattr(lib, 'FMOD_'+name)
        function.argtypes = args
        function.restype = C.c_int
        return function

    ptr = C.c_void_p
    pp = C.POINTER(ptr)
    ip = C.POINTER(C.c_int)
    up = C.POINTER(C.c_uint)
    create = api('System_Create', [pp, C.c_uint])
    release = api('System_Release', [ptr])
    set_output = api('System_SetOutput', [ptr, C.c_int])
    init = api('System_Init', [ptr, C.c_int, C.c_uint, ptr])
    create_stream = api('System_CreateStream', [ptr, C.c_char_p, C.c_uint, ptr, pp])
    get_sub = api('Sound_GetSubSound', [ptr, C.c_int, pp])
    get_format = api('Sound_GetFormat', [ptr, ip, ip, ip, ip])
    get_defaults = api('Sound_GetDefaults', [ptr, C.POINTER(C.c_float), ip])
    get_length = api('Sound_GetLength', [ptr, up, C.c_uint])
    read = api('Sound_ReadData', [ptr, ptr, C.c_uint, up])
    seek = api('Sound_SeekData', [ptr, C.c_uint])
    sound_release = api('Sound_Release', [ptr])

    def check(result):
        if result:
            raise RuntimeError(f'FMOD error {result}')

    system = ptr()
    check(create(C.byref(system), 0x00020309))
    try:
        check(set_output(system, 2))  # FMOD_OUTPUTTYPE_NOSOUND
        check(init(system, 32, 0, None))
        with tempfile.TemporaryDirectory(prefix='pz-motor-audio-', dir=Path(__file__).resolve().parent) as scratch:
            fsb_path = Path(scratch)/'source.fsb'
            fsb_path.write_bytes(raw[base:base+60+headers+names_size+data_size])
            del raw
            parent = ptr()
            check(create_stream(system, str(fsb_path).encode(), 0x2000, None, C.byref(parent)))  # OPENONLY
            try:
                output.mkdir(parents=True, exist_ok=True)
                manifest = []
                for index, name in selected:
                    destination = output/(name+'.wav')
                    if destination.exists():
                        with wave.open(str(destination), 'rb') as wav:
                            entry = dict(file=destination.name, event=WANTED[name], sample_index=index,
                                         seconds=round(wav.getnframes()/wav.getframerate(), 3),
                                         sample_rate=wav.getframerate(), channels=wav.getnchannels(),
                                         bits=wav.getsampwidth()*8)
                        manifest.append(entry)
                        print(json.dumps(entry))
                        continue
                    sound = ptr()
                    check(get_sub(parent, index, C.byref(sound)))
                    check(seek(sound, 0))
                    kind, fmt, channels, bits = [C.c_int() for _ in range(4)]
                    check(get_format(sound, C.byref(kind), C.byref(fmt), C.byref(channels), C.byref(bits)))
                    assert fmt.value in (1, 2, 3, 4, 5), f'Expected PCM, got {fmt.value}'
                    frequency = C.c_float()
                    priority = C.c_int()
                    check(get_defaults(sound, C.byref(frequency), C.byref(priority)))
                    length = C.c_uint()
                    check(get_length(sound, C.byref(length), 4))  # FMOD_TIMEUNIT_PCMBYTES
                    decoded = bytearray()
                    buffer = C.create_string_buffer(65536)
                    while len(decoded) < length.value:
                        obtained = C.c_uint()
                        result = read(sound, buffer, min(len(buffer), length.value-len(decoded)), C.byref(obtained))
                        if obtained.value:
                            decoded.extend(buffer.raw[:obtained.value])
                        if result not in (0, 13):  # FMOD_ERR_FILE_EOF = 13
                            check(result)
                        if result == 13 or not obtained.value:
                            break
                    # Vorbis codec can report a rounded length at the tail.
                    assert 0 <= length.value-len(decoded) <= 16384 and decoded, (name, len(decoded), length.value)
                    rate = round(frequency.value)
                    seconds = len(decoded)/(rate*channels.value*(bits.value//8))
                    output_bits = bits.value
                    if fmt.value == 5:  # FMOD decoded Vorbis to PCM float32; WAV preview uses PCM16.
                        values = array('f')
                        values.frombytes(decoded)
                        decoded = array('h', (max(-32768, min(32767, round(v*32768))) for v in values)).tobytes()
                        output_bits = 16
                    with wave.open(str(destination), 'wb') as wav:
                        wav.setnchannels(channels.value)
                        wav.setsampwidth(output_bits//8)
                        wav.setframerate(rate)
                        wav.writeframes(decoded)
                    entry = dict(file=destination.name, event=WANTED[name], sample_index=index,
                                 seconds=round(seconds, 3), sample_rate=rate,
                                 channels=channels.value, bits=output_bits)
                    manifest.append(entry)
                    print(json.dumps(entry))
                (output/'manifest.json').write_text(json.dumps(dict(bank=str(BANK),
                    note='Raw decoded source samples, without Studio event mixing/effects.',
                    samples=manifest), indent=2), encoding='utf8')
            finally:
                check(sound_release(parent))
    finally:
        check(release(system))


if __name__ == '__main__':
    main()
