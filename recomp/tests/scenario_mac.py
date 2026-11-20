#!/usr/bin/env python3
"""scenario_mac.py <scenario> <tag> [ENV=VALUE ...] : one of scenario.py's native sessions (or one below) played by the
Mac build (work/fnv/app/FalloutNVNative), test mode, muted, 1280x720, a fresh data folder holding the scenario's save;
screenshots in work/scen-mac-<scenario>-<tag>/. Extra ENV=VALUE pairs go to the game (DSR_MSAA=4, DSR_FPSCAP=0,
DS_RESOLUTION=2560x1440, MTL_DEBUG_LAYER=1, ...). GAME=<folder> overrides ~/Games/FalloutNVNative/game-files.

Console notes (the Mac's DirectInput path): after a coc/cow the console still shows but takes no typing until it is
toggled again, so commands after a cell change go through a fresh console() (open, type, close); the idle vanity
camera starts about 27 s after the last input."""
import os, sys, shutil, subprocess
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, 'tests'))
import scenario as sc

@sc.scenario('strip-matched', 200)
def _():                               # as the reference's 60-strip: from the save, gamehour 21, coc StripGomorrah, HUD on
    s, t = sc.console(100, 'set gamehour to 21', 'coc StripGomorrah'); s = s[:-1]
    return sc.LOAD + s + [(t + 12, 'key', 'grave')] + [(t + d, 'shot', 'strip-%02d' % d) for d in (15, 25, 40, 60)]
@sc.scenario('strip-refseq', 330)
def _():                               # the reference session's own order: the hour set in the Saloon (its echo shot), the Strip later
    s, t = sc.console(100, 'coc GSProspectorSaloonInterior'); s = s[:-1]
    s2, t2 = sc.console(t + 40, 'set gamehour to 21'); s2 = s2[:-1] + [(t2 - 1, 'shot', 'echo'), (t2, 'key', 'grave')]
    s3, t3 = sc.console(t2 + 75, 'coc StripGomorrah'); s3 = s3[:-1]
    return sc.LOAD + s + s2 + s3 + [(t3 + 10, 'key', 'f'), (t3 + 15, 'shot', 'strip15'), (t3 + 22, 'shot', 'strip22')]
@sc.scenario('water', 280)
def _():                               # as the reference's 64 / 78: Hoover Dam from above, first person, noon
    s, t = sc.console(100, 'tgm', 'tcl', 'set gamehour to 12', 'cow WastelandNV 17 7'); s = s[:-1]
    s2, at2 = sc.console(t + 40, 'player.setpos z 5000', 'player.setangle x 30', 'player.setangle z 0')
    return sc.LOAD + s + s2 + [(at2 + 6, 'shot', 'water'), (at2 + 8, 'shot', 'water2')]

if __name__ == '__main__':
    name, tag = sys.argv[1], sys.argv[2]
    extra = dict(a.split('=', 1) for a in sys.argv[3:])
    secs, fn = sc.SCENARIOS[name]; steps = sorted(fn(), key=lambda s: s[0]); secs = max(secs, int(steps[-1][0]) + 8)
    base = os.path.join(HERE, 'work', 'scen-mac-%s-%s' % (name, tag))
    if os.path.isdir(base): shutil.rmtree(base)
    data = os.path.join(base, 'data'); saves = os.path.join(data, 'drive_c/Users/player/Documents/My Games/FalloutNV/Saves')
    os.makedirs(saves)
    if any(st[0] == 67 and st[2] == 'Return' for st in steps): shutil.copy(sc.SAVE, saves)
    env = dict(os.environ, DS_TEST='1', W32_AUDIO_MUTE='1', DS_EXIT_AFTER=str(secs), DS_RESOLUTION='1280x720', DS_SHOT_RAW='1',
               DS_SCRIPT=sc.native_script(steps, base)); env.update(extra)
    game = os.environ.get('GAME', os.path.expanduser('~/Games/FalloutNVNative/game-files'))
    with open(os.path.join(base, 'log.txt'), 'w') as log:
        rc = subprocess.run(['timeout', '-s', 'KILL', str(secs + 30), os.path.join(HERE, 'work/fnv/app/FalloutNVNative'),
                             '--exe', os.path.join(HERE, 'work/fnv/FalloutNV.exe'), '--game', game, '--data', data],
                            cwd=HERE, env=env, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL).returncode
    print(name, tag, 'rc', rc, base, sorted(f for f in os.listdir(base) if f.endswith('.png')))
