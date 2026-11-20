#!/usr/bin/env python3
"""esm_weather.py <FalloutNV.esm> [worldspace substring] : the climate of each matching worldspace (default "strip"):
its weathers with their chances, its sunrise/sunset times, and each weather's colour table (10 kinds x 6 times of
day: sunrise, day, sunset, night, high noon, midnight), fog distances and power. Read-only; for comparing skies with
the original (issue #2: the Strip's night sky)."""
import sys, struct, zlib
data = open(sys.argv[1], 'rb').read(); want = (sys.argv[2] if len(sys.argv) > 2 else 'strip').lower()
recs = {}
def walk(off, end):
    while off < end:
        typ, size = data[off:off + 4], struct.unpack_from('<I', data, off + 4)[0]
        if typ == b'GRUP': walk(off + 24, off + size); off += size; continue
        flags, fid = struct.unpack_from('<II', data, off + 8)
        if typ in (b'WRLD', b'CLMT', b'WTHR'):
            body = data[off + 24:off + 24 + size]
            if flags & 0x40000: body = zlib.decompress(body[4:])
            subs, p = [], 0
            while p + 6 <= len(body):
                st, sl = body[p:p + 4], struct.unpack_from('<H', body, p + 4)[0]; subs.append((st, body[p + 6:p + 6 + sl])); p += 6 + sl
            recs[fid] = (typ, subs)
        off += 24 + size
walk(0, len(data))
def edid(f): return next((v.rstrip(b'\0').decode('latin1') for s, v in recs[f][1] if s == b'EDID'), '?') if f in recs else '?%08X' % f
def hm(t): return '%02d:%02d' % (t // 6, t % 6 * 10)
KINDS = ['SkyUpper', 'Fog', 'Unused', 'Ambient', 'Sunlight', 'Sun', 'Stars', 'SkyLower', 'Horizon', 'CloudsUpper']
for fid, (t, subs) in recs.items():
    if t != b'WRLD' or want not in edid(fid).lower(): continue
    for c in [struct.unpack('<I', v[:4])[0] for s, v in subs if s == b'CNAM']:
        print('WRLD %08X %s: climate %08X %s' % (fid, edid(fid), c, edid(c)))
        for s, v in recs.get(c, (0, []))[1]:
            if s == b'TNAM': print('  sunrise %s-%s, sunset %s-%s' % (hm(v[0]), hm(v[1]), hm(v[2]), hm(v[3])))
            if s != b'WLST': continue
            for k in range(0, len(v), 12):
                w, ch, _ = struct.unpack_from('<IiI', v, k); print('  weather %08X %s, chance %d' % (w, edid(w), ch))
                for s2, v2 in recs.get(w, (0, []))[1]:
                    if s2 == b'NAM0':
                        per = len(v2) // 40
                        for kk in range(10): print('    %-12s' % KINDS[kk], [tuple(v2[4 * (kk * per + j):4 * (kk * per + j) + 3]) for j in range(per)])
                    if s2 == b'FNAM': print('    fog (day near, far, night near, far, power...)', struct.unpack_from('<%df' % (len(v2) // 4), v2))
