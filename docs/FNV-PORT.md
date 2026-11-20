# Fallout: New Vegas: native port with the Dungeon Siege II recompiler

This branch takes the static recompiler from this repository (x86 → C → clang) and points it at the player's own
**GOG Fallout: New Vegas 1.4.0.525** `FalloutNV.exe`
(sha256 `89e7020487e80f20ddc92ea641c4433b2c6839a82f45a076e414d167d11dd0fe`, installer
`setup_fallout_new_vegas_1.4.0.525_(12010).exe`). As with Dungeon Siege, nothing from the game is committed. All
generated code goes under `recomp/work/`, which git ignores.

## Linux port status (2026-10-07, this repository)

The whole executable plus Bink and both Vorbis DLLs link into `FalloutNVLinux` (libvorbisfile is relocated to
0x11000000, see `tools/rebase_pe.py`); all 280 imports are implemented. Checked against the original game running
under Proton in headless gamescope (`tests/fnv_ref.py`, `tests/scenario.py`), same inputs, same moments:

- intro movie, main menu and its music, new game, Doc Mitchell's dialogue (voices correlate 0.999 with a reference
  decode), subtitles, name entry, the Reflectron (face), the DLC messages, saving, loading (Continue)
- Goodsprings by day, dusk and night, the saloon, Vault 22, the Lucky 38 penthouse (30-50 dB PSNR against the
  original); the pause menu; the Pip-Boy (35 dB); a gecko next to the player (creature rendering, the combat HUD)
- the intro movie's sound: correlation 1.0000 with a reference decode of FNVIntro.bik (`tools/audiocmp.py`)
- a 10-minute tour through 12 interiors (Lucky 38, Gomorrah, the Tops, Hoover Dam, Vaults 11 and 22, Freeside,
  Novac, Primm, Hidden Valley, Forlorn Hope): no crash; player position and heading after a `coc` read back
  identical to the original's
- all 1809 unique shaders in the game's .sdp packages translate (MojoShader, patched) and compile
  (`tools/sdp_glsl_check.c`)

Fixed while comparing: D3D9 pixel centres (night was rendered as day: the 1x1 adaptation quad never rasterised),
16 samplers (yellow terrain), occlusion queries (sun glare indoors), blend/scissor/depth-bias/two-sided stencil,
and relatively addressed constant arrays (skinned meshes thrown across the screen as dark planes: FNV's skinning
shaders declare 18 bones and index 26+, see `third_party/mojoshader/README.md`), and silence after loading a save
(the DirectSound mixer waited for the primary buffer to be played, which only the intro movie's player does).
Also checked: firing a pistol (ammo, recoil, shot sounds), containers and the quantity dialog, mouse hover and
clicks in menus and message boxes (scripts need `mmove`, the real mouse path: message boxes follow the Windows
cursor, which `dimove` doesn't move). The launch window (`recomp/host/linux_launcher/fnv_launcher.py`, as the original's launcher does) sets the
render resolution (any size, ultrawide presets, Custom), full screen or windowed, the frame rate (60 by default;
any cap, the display's rate with VSync, or unlimited: the host sets Fallout.ini's `[HAVOK] fMaxTime` to 1 / rate so
physics keep up) and antialiasing (FXAA, MSAA 2/4/8x, MSAA + FXAA; the renderer's own, as a driver override: the
game's MSAA path draws its scene without a depth buffer here). Environment: `DS_RESOLUTION`, `DS_WINDOW_MODE`,
`DSR_FPSCAP`, `DSR_VSYNC`, `DSR_MSAA`, `DSR_FXAA`; `FNV_NO_LAUNCHER=1` skips the window.

VATS: the tutorial panel, the targeting camera and body-part highlight with hit chances, and queued attacks firing
(ten geckos placed with AI off so one is in view; not compared with the original, whose spawn spots differ).

Not yet verified: the VATS kill cam (it fell between screenshots), the end slides, and the third `coc` of `load-cells` (Gomorrah) whose third-person camera faces differently from the
original's (15 dB; the player's position and heading read back identical, the camera after chained `coc`s does not).

`tests/saves/fnvtest1.fos` is a save made just after character creation; the `load-*` scenarios start from it.

Still to do:
1. Performance: done for Linux. Vertex and index buffers are kept on the GPU (DSR_VBUF_DATA, only the ranges the game
   locked are sent again) and shader draws name buffers and D3D element types (DSR_DRAW_PROG_VB): Goodsprings went
   from 30 to ~100 fps, the interior tour from a median of ~30 to 123. `W32_PROFILE` + `tools/profile.py` is a
   sampling profiler for the next round. User-pointer draws still take the float4 path.
2. The Mac side (also needs the three buffer records in `renderer.m`; until then the D3D9 layer uses them on Linux only): MojoShader's Metal profile in place of GLSL; `renderer.m` needs DSR_GLSL_CREATE's MSL equivalent.
3. The 127 unresolved jump tables, `_except_handler4`, C++ exceptions if the game throws.

The installer note below refers to the macOS repository's `game-installer` release (this repository has none).

## Status (2026-10-06, done on Linux x86-64)

| Step | State |
|---|---|
| Analysis (`tools/analyze.py`) | 92,603 functions, 95.6% of `.text`; 1,323 jump tables resolved, 127 unresolved (87 bounded heuristically while lifting) |
| SSE/SSE2/MMX in the lifter (`tools/sse.py`, `runtime/rt_sse.h`) | **new**. FNV runs about 250k SSE instructions; DS2 had none. XMM/MMX/MXCSR are in `Ctx`. All 375 sampled SIMD instances (every distinct form FNV uses, up to 3 each) match Unicorn bit for bit (`tests/fuzz_sse.py`, 37,440 random runs in total) |
| Integer/x87 lifter on FNV's instruction mix (`tests/fuzz_insn.py`, first run on a non-DS executable) | 11,942 instances × 20 runs. One real bug found and fixed: `shrd`'s overflow flag. Also added: 16-bit `mul`/`imul`/`div`/`idiv`, and `xchg` with memory as an atomic swap. Remaining differences are expected: x87 transcendentals (`fprem`/`fyl2x`/`f2xm1`, last-bit differences from the double model) and `cpuid` (a fixed fake CPU). That fuzzer does not seed XMM state, so its SSE rows are not meaningful; `fuzz_sse.py` covers SSE |
| Lifting (`tools/lift.py --game fnv`) | all 92,603 functions lifted, 0 internal errors. What's left unsupported is data decoded as code (`in`/`out`/`hlt`/far jumps/segment registers/`enter` nesting, about 330 sites) |
| Compiling the generated C | **all files compile** (FNV + Bink: 93,440 functions, 236 objects) with the project's flags (`-O2 -ffp-contract=off`), 0 errors, ~900 MB of C, ~1.5 min on 24 cores |
| Bink (`binkw32.dll` from the game folder) | lifted into the same image set as DS2's Bink (`build_fnv.sh`); every one of its imports is already implemented |
| Linking / running | **not yet**: see "Runtime gaps" |
| Shaders → Metal | **15,775 of 15,791** `.sdp` shader entries (1,809 unique bytecodes, vs_1_1 to ps_3_0) translate to MSL with MojoShader plus `tools/mojoshader-metal-centroid.patch`. The only failure is `PARTICLE.vso` (indexed constant array). The MSL has **not** been compiled with `xcrun metal` yet: that needs the Mac |

The installer (split zip) is attached to this repository's `game-installer` release. Its notes show how to join and
extract it, and the release is not part of the git history.

Build the C (Mac or Linux):

```sh
recomp/build_fnv.sh "/path/to/Fallout New Vegas/FalloutNV.exe"      # -> recomp/work/fnv/c/*.c and obj/
```

**Not re-run yet: the Dungeon Siege II build.** These changes are additive (`--game` defaults to `ds2`, and
`rt_cpuid_sse2` is off by default), but on the Mac run DS2's `recomp/build.sh` once as a regression check.

## What carries over unchanged from DS2

The execution model (guest memory at the PE's base, real guest stack, lazy flags, x87 as doubles), the Win32 layer
(loader, heaps, threads, SEH, files, registry, USER32/GDI), D3D9 device/surfaces/textures/buffers/state blocks/queries,
D3DX texture loading, DirectSound on Core Audio, Winsock and the Metal renderer.

## Runtime gaps, roughly in order of the work

1. **Start-up glue for a second game.** `runtime/win32/run.c`, `loader.c`, `edition.h`, `files.c` and the host app
   assume Dungeon Siege II (window title, paths such as `C:\GOG Games\Dungeon Siege`, `DungeonSiege2.exe`, the DS2
   `HOOKS`/`OVERRIDES` in `lift.py`, which `--game fnv` now turns off). FNV needs its own profile: exe name, game
   folder → `C:\Games\Fallout New Vegas`, `My Games\FalloutNV` for `Fallout.ini`/saves, registry key
   `HKLM\Software\Bethesda Softworks\FalloutNV\Installed Path`.
2. **Imports not implemented yet.** 111 of FalloutNV.exe's 280 imports are missing:
   - KERNEL32 (20): `CreateSemaphoreA`/`ReleaseSemaphore`, `TryEnterCriticalSection`,
     `InitializeCriticalSectionAndSpinCount`, `InterlockedCompareExchange`/`InterlockedExchangeAdd`,
     `GetPrivateProfile*`/`WritePrivateProfileStringA` (the INI files), `GlobalMemoryStatusEx`, `GetFileSizeEx`,
     `SetFilePointerEx`, `SetThreadIdealProcessor`, `GetCommandLineW`, `GetModuleHandleW`, console calls.
   - WSOCK32 by ordinal (21): DS2's `winsock.c` has these by name; map the ordinals.
   - DSOUND `#11` (`DirectSoundCreate8`), XINPUT1_3 `#2`/`#3` (`XInputGetState`/`XInputSetState`, to GameController.framework),
     DINPUT8 `DirectInput8Create` (keyboard and mouse devices).
   - USER32 (7), SHELL32 (3: `SHGetFolderPathA` → My Documents), COMCTL32 (3), WINMM `mmio*` (7, RIFF/WAV reading),
     ole32 `CoFreeUnusedLibraries`, d3d9 `D3DPERF_SetOptions`.
   - GalaxyWrp.dll (11 `SteamAPI_*` shims): stub as "no Steam/Galaxy" (`SteamAPI_Init` returns false).
   - libvorbisfile (6 `ov_*`): implement natively on the host's libvorbisfile, or stb_vorbis.
   - d3dx9_38 (25): matrix/vector/plane maths (easy), `D3DXCreate*TextureFromFileInMemory` (DS2 has the
     non-`_38` ones), `D3DXGetShaderConstantTable`, `D3DXAssembleShader`/`D3DXCompileShader` (see whether the game
     calls them in normal play; Gamebryo usually loads the precompiled `.sdp` shaders).
3. **Programmable shaders on Metal.** DS2's `d3d9.c` stores `CreateVertexShader`/`CreatePixelShader` bytecode but
   never runs it, because DS2 draws fixed-function plus HLSL effects. FNV draws almost everything with SM 2/3
   bytecode. Plan: MojoShader (zlib) with the centroid patch at create time → MSL → `MTLLibrary`. Then bind
   `SetVertexShaderConstantF`/`PixelShaderConstantF` (already stored in `vsc`/`psc`) as a constant buffer, and map
   MojoShader's attribute and sampler names to the vertex declaration and texture stages. Cache the compiled
   libraries by bytecode hash. `PARTICLE.vso` needs MojoShader's relative-addressing fix or a hand port.
4. **Render targets.** FNV renders to several targets (HDR, depth, shadow maps, water reflections, MRT). DS2's
   `SetRenderTarget` handles index 0 only.
5. **CPU identity.** `rt_cpuid` reports a family-5 Pentium without MMX/SSE (what DS2 expects). Set `rt_cpuid_sse2 = 1`
   in the FNV profile so the C runtime and engine see an SSE2 CPU. FNV's code uses SSE unconditionally anyway.
6. **Threads.** FNV runs real worker threads (IO, AI linear tasks, Havok). The runtime already runs guest threads
   natively. `lock`-prefixed ops become atomics or the runtime bus lock, and `xchg` with memory is an atomic swap
   (fixed for FNV; DS2 emitted a plain read and write). The two mechanisms do not exclude each other.
   arm64 atomics fault on unaligned addresses where x86 locked ops don't: watch for SIGBUS at a locked instruction.
   Look for races the x86 memory model hid; arm64 is weakly ordered.
7. **C++ exceptions / SEH.** 6,500 functions install C++ EH frames (destructors on unwind). Only 5 are `__try`
   blocks, all in the C runtime, and 4 of those use `_except_handler4`, which `lift.py` doesn't parse yet. If the
   game throws in normal play, catch continuations are needed (DS2 PLAN item 4).

## Floating-point notes for the Mac

- The generated code must keep `-ffp-contract=off`: an arm64 fused multiply-add changes results.
- `rt_fpcr_sync` puts the host rounding mode under the **x87** control word. SSE has its own (MXCSR). If FNV ever
  runs the x87 in a directed rounding mode while SSE code runs, SSE results would round the wrong way on arm64.
  Watch for `fldcw`/`ldmxcsr` with non-default rounding.
- A NaN created from non-NaN inputs is `0x7fc00000` on arm64 and `0xffc00000` on x86. Bit-tests on NaNs are rare.
- `rcpps`/`rsqrtps`/`rsqrtss` return exact results, not the hardware's 12-bit approximations.

## Tests

```sh
recomp/.venv/bin/python recomp/tests/fuzz_sse.py recomp/work/fnv/FalloutNV.exe recomp/work/fnv/analysis.json build
recomp/.venv/bin/python recomp/tests/fuzz_sse.py recomp/work/fnv/FalloutNV.exe recomp/work/fnv/analysis.json run 60
FUZZ_EXE=recomp/work/fnv/FalloutNV.exe FUZZ_ANALYSIS=recomp/work/fnv/analysis.json recomp/.venv/bin/python recomp/tests/fuzz_insn.py build
FUZZ_EXE=... FUZZ_ANALYSIS=... recomp/.venv/bin/python recomp/tests/fuzz_insn.py run 20
# shaders: build MojoShader (git ad5dff8) with tools/mojoshader-metal-centroid.patch, then
cc -I mojoshader recomp/tools/sdp2msl.c libmojoshader.a -lm -o sdp2msl && ./sdp2msl out/ "<game>/Data/Shaders/"*.sdp
for f in out/*.metal; do xcrun -sdk macosx metal -c "$f" -o /dev/null || echo "$f"; done      # Mac only
```

## Mac visual and performance review, 2026-10-10

The Metal fallback upload now supplies all 16 bytes it asks the driver to copy; the old 4-byte stack source fails
AddressSanitizer through an instrumented forwarding device. Frame-trace export now synchronizes with GPU callbacks
and concurrent quit requests, drops unfinished samples and detaches its allocation only once. Its regression passes
ASAN/UBSAN and ThreadSanitizer. Background test-mode activation changes no longer pause the guest.

Relative shader constants now read the complete signed Direct3D register address, including local `DEF` overrides,
and return zero outside the register bank. The actual-GPU regression fails on the previous implementation (an
out-of-range read returns poisoned neighboring data) and passes with and without constant-table metadata. All
15,791 entries in the installed SDP packages translate; their 1,745 unique generated Metal sources compile.
`tools/sdp2msl.c` now uses an entrypoint name accepted by Metal and reports translation failures through its exit code.

The renderer now honors anisotropic minification requests and includes the requested maximum in its sampler cache.
Previously, the D3D9 producer sent this state but the Metal sampler ignored it. Ordinary point/linear draws stay
isotropic, and invalid maximum values are clamped to Metal's 1–16 range. The forwarding-device regression checks
state changes and cache reuse. This follows [Direct3D filtering](https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3dtexturefiltertype)
and [Metal sampler anisotropy](https://developer.apple.com/documentation/metal/mtlsamplerdescriptor/maxanisotropy).

The capped-frame wait uses short sleeps until its final ~200 microseconds instead of spinning for as much as 2 ms.
In a standalone M1 Pro thread-CPU measurement, old/new cost per frame was 1.116/0.151 ms at 60 Hz and 0.928/0.089 ms
at 120 Hz. Scheduler noise affects lateness; this does not establish tighter latency or faster uncapped gameplay.

The original visual reference is documented in [issue #1](https://github.com/Joshspeakman/fallout-nv-macos/issues/1):
original GOG 1.4.0.525 through UMU-Proton 10.0-4 on Prime, rather than native Windows. Matching Mac captures use the
same save, 1280×720 and the supplied INIs. All 11 supplied ESM/ESP hashes match. The reference uses 4× MSAA; the
Metal renderer now has it too (`DSR_MSAA`, the launch window's Antialiasing row, 4x by default: see below). Anisotropic
filtering improves the road detail toward the reference. Dynamic weather/exposure, particles and NPC movement limit
pixel comparisons. The idle vanity camera must be cancelled before taking a matching first-person view.

The matching first-person Goodsprings noon/dusk/night views and Saloon corridor preserve the reference lighting.
The Strip now loads correctly in the shared scripted scenarios (`StripGomorrah`, replacing the invalid `TheStrip`).
Its signs, lamps and palms render; sky color differs in this run. Hoover Dam water animates. A later original-game
control with `iMultiSample=0` reproduces the strong moving cloud reflections seen on both the previous `359c217`
nightly and this audit build. Its verified archive SHA256 is
`66666577dabaddc416ad7c178a0c23df1e5ef0207c42827f82df28c59b21569c`; Prime kept the same INI water flags and loaded
weather. The matched still supports retaining the current water semantics. Runtime weather ID and reflection
booleans could not be queried, so this is not proof of deterministic parity. The Strip sky and the Metal backend's
MSAA (2026-11-18): `DSR_MSAA=2|4` (8 falls back to the most the GPU takes: 4 on Apple GPUs) multisamples the screen-sized render targets, depth buffers and float render-target
textures; each pass resolves as it ends (depth and stencil: sample 0) and every pipeline is made per sample count.
Checked at 1280×720: Goodsprings noon power poles and wires antialiased; Pip-Boy, HUD, the Strip at night and the
Hoover Dam water draw as before, and with no Metal validation errors. The game's own MSAA path stays off, so the dam
water matches the original's antialiasing-off control (`78-water-msaa0.png`: strong cloud reflections), not the 4×
reference's flat water. Uncapped Goodsprings: about 86 fps either way (the CPU is the limit); GPU time 4.3 → 4.6 ms at
1280×720, 5.7 → 7.2 ms at 2560×1440 with 4x.

The Strip sky stays different: at 21:00 the Mac's is navy, the reference's lilac. The Strip has one weather
(`NVTheStripWeather`, 100%) and its climate's sunset ends at 20:00, so night colours at 21:00 are what the data asks
for; the Mac's sky at 20:00 is close to the reference's. Replaying the reference's own order (the hour set in the
Saloon, the Strip ~90 s later, first person; the hour's echo checked) gives navy again. Settling it needs an original
capture with the hour set outdoors (an issue of its own); the original 4× reference is retained separately.

A 13-minute copied-profile tour exited normally and exported 44,072 valid completed frame records. Selected settled
windows had median frame intervals near 16.7 ms in the Saloon and at the dam, and 17.0 ms at dusk. The Strip window
was slower at 19.2 ms (about 52 FPS). These are representative short windows, not an all-game 60 FPS guarantee.

Cold pipeline compilation is a remaining hitch source: this audit saw some compilations lasting tens of milliseconds.
The original and revised runs visit different shader variants and cache states, so their compile maxima are not a
matched speed comparison. A native CPU sample of the revised build collected too few stacks for a reliable old/new
CPU attribution; the standalone wait benchmark and live frame logs are the available performance evidence.

Validation commands (run from the repository root; generated shader text stays private):

```sh
clang -O1 -g -fsanitize=address,undefined recomp/tests/frame_trace_test.c -o /tmp/fnv-frame-trace
/tmp/fnv-frame-trace
clang -O1 -g -fsanitize=thread recomp/tests/frame_trace_test.c -o /tmp/fnv-frame-trace-tsan
/tmp/fnv-frame-trace-tsan
clang -O2 recomp/tests/frame_wait_test.c -o /tmp/fnv-frame-wait
/tmp/fnv-frame-wait
```

`renderer_init_test.m`, `sampler_test.m` and `msl_compile_test.m` include their build instructions. Build
`mojo_metal_test.m` with Foundation/Metal and the MojoShader objects from `recomp/work/fnv/obj/rt/mojo` after a runtime
rebuild. The compiler test consumes the directory exported by `sdp2msl`.


The follow-up upload-ring regression (`recomp/tests/renderer_ring_test.sh`, no game files required) reproduces
an out-of-bounds range when a single upload exceeds ring capacity. The renderer now grows the ring after pending
GPU work completes and reserves enough space for an entire draw before setting encoder state. The normal 256 MB
capacity is unchanged. Oversized allocation, draw reservation, real GPU copy and wrapping pass ASAN/UBSAN.
This is a stability fix; no average-FPS increase is claimed.
