# Powered gate audio

Current source: the approved synthetic motor prototype, created without sampled
audio by `tools/synth_gate_drive.py`. The approved `art/audio/gate-drive-prototype-v3.wav`
has no start/stop beeps or silent padding. `tools/prepare_gate_drive_loop.py` takes
only its steady section and makes a four-second circular loop using a 150ms cosine
crossfade. A near-zero rotation gives a clean onset; no gain change is applied.
Outputs: `art/audio/gate-drive-loop-v1.wav`, an eight-second two-repeat listening
preview, and `mod/SlidingGates/42/media/sound/SG_GateMotorRunning.wav`.
The loop is mono/48 kHz PCM16 and supersedes the earlier slow-washer recording.
The originally extracted vanilla candidates remain in PZMining.

Waveform checks: wrap step 258 PCM units, below normal p99 step 930; no silent
20ms windows or clipping. These are signal checks, not a substitute for listening.

`SG_sounds.txt` registers one looped 3D clip. Native parser evidence is
`render-audit/motor-sound-native.txt`; reproduce with `probe-motor-sound.py`.

Installed engine API evidence (current jar, inspected with CFR):

- `IsoWorld.getFreeEmitter(float,float,float)` positions a world-owned emitter,
  adds it to `currentEmitters`, and disables remote playback. The world ticks and
  recycles it after its sounds stop; the mod does not take ownership or tick it.
- `FMODSoundEmitter.playSoundImpl(String,IsoObject)` selects the clip and plays it
  locally. Clients already receive authoritative gate state, so no sound packet
  should be sent again. `BaseSoundEmitter.stopSound(long)` stops the held handle.
- Lua `addSound(IsoObject,int,int,int,int,int)` enters `WorldSoundManager`.
  Only the authority uses this path. Its radius/volume are separate from audible
  clip attenuation and user audio preferences.

Powered requests are marked before motion state publication. Snapshots carry
`motor` and `motionRemaining`; manual input never sets the flag. Local loops are
deduplicated by gate identity and stopped by final state or remaining-time expiry.
Unload, replacement, removal, destruction and pause release the handle; resume
gets another pooled emitter. Recovery after a restart settles silently.

`tests/test_gate_motor.py` covers both widths/orientations in SP/authority and
client state ordering, late join, expiry, unload/removal, pause and rejection.
All 11 existing/new test scripts passed after integration. Gameplay must still
verify actual playback, distance/volume balance, pausing, two clients, and zombies.
