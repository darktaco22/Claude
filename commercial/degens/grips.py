"""Contact solving for hands holding props, using rigctl.Hand. All results are in the palm frame
(X = Y x Z, Y = fingers, Z = palm normal) so they apply to any hand pose."""
import math
from mathutils import Vector, Matrix
import rigctl

FINGERS = ['finger1', 'finger2', 'finger3', 'finger4', 'finger5']
RATIO = {1: 1.0, 2: 1.15, 3: 0.8}


def curlQ(a, s, ang, spread=None):
    Q = {}
    for f, (base, extra) in ang.items():
        for j in (1, 2, 3):
            bn = f'{f}-{j}.{s}'
            if bn not in a.curl_axis: continue
            th = base * RATIO[j] + (extra if j > 1 else 0.0)
            q = rigctl.qrot(a.curl_axis[bn], th)
            if spread and j == 1 and f in spread:
                n = (a.rest[f'wrist.{s}'] @ a.palm[s]).to_3x3().col[2]
                q = rigctl.qrot(n, spread[f]) @ q
            Q[bn] = a.local_q(bn, q)
    return Q


def solve_wrap(a, s, sdf, start=None, max_base=1.25, clearance=0.0012, thumb_max=0.9):
    """Curl each finger until it touches the prop (sdf(p) < clearance anywhere on that finger)."""
    H = rigctl.Hand(a, s)
    ang = {f: [0.05, 0.0] for f in FINGERS}
    if start: ang.update({f: list(v) for f, v in start.items()})
    def touching(f, A):
        pts = H.posed(curlQ(a, s, A))
        return any(sdf(p) < clearance for p, fk, _ in pts if fk == f)
    for f in FINGERS:
        lim = thumb_max if f == 'finger1' else max_base
        step = 0.04
        # open it up first if it starts inside the prop
        while ang[f][0] > -0.9:
            A = {k: tuple(v) for k, v in ang.items()}
            if not touching(f, A): break
            ang[f][0] -= step
        while ang[f][0] + step <= lim:
            A = {k: tuple(v) for k, v in ang.items()}; A[f] = (ang[f][0] + step, 0.0)
            if touching(f, A): break
            ang[f][0] += step
        # then roll the tip in
        while ang[f][1] + step <= 0.9:
            A = {k: tuple(v) for k, v in ang.items()}; A[f] = (ang[f][0], ang[f][1] + step)
            if touching(f, A): break
            ang[f][1] += step
    final = {k: tuple(v) for k, v in ang.items()}
    pts = H.posed(curlQ(a, s, final))
    worst = {}
    for p, fk, _ in pts:
        key = fk or 'palm'; worst[key] = min(worst.get(key, 1.0), sdf(p))
    return final, worst


def cylinder(a, s, R, z0, z1, yoff=0.03):
    """A cylinder gripped in the palm; returns (curls, prop matrix in palm frame, worst sdf)."""
    H = rigctl.Hand(a, s)
    axis = Vector((a.idx_sign[s], 0, 0))
    def sdf_at(d):
        c = Vector((0, yoff, d))
        def f(p):
            q = p - c; h = q.dot(axis); r = (q - axis * h).length
            if h < z0 or h > z1: return 1.0
            return r - R
        return f
    open_pts = H.posed(curlQ(a, s, {f: (0.08, 0.0) for f in FINGERS}))
    d = R
    while any(sdf_at(d)(p) < 0.0008 for p, fk, _ in open_pts if fk != 'finger1'):
        d += 0.001
    curls, worst = solve_wrap(a, s, sdf_at(d))
    # the mug's handle (its local +X) points away from the palm, so it never meets the fingers
    z = axis; xx = Vector((0, 0, 1)); yy = z.cross(xx)
    M = Matrix((xx, yy, z)).transposed().to_4x4(); M.translation = Vector((0, yoff, d))
    return curls, M, worst


def phone(a, s, W=0.072, L=0.150, D=0.0082, yoff=0.034):
    """A phone lying across the palm, screen facing the palm normal, long axis toward the index side."""
    H = rigctl.Hand(a, s)
    top = Vector((a.idx_sign[s], 0, 0)); nrm = Vector((0, 0, 1)); side = top.cross(nrm)
    def sdf_at(d):
        c = Vector((0, yoff, d + D / 2))
        def f(p):
            q = p - c; e = Vector((abs(q.dot(side)) - W / 2, abs(q.dot(top)) - L / 2, abs(q.dot(nrm)) - D / 2))
            out = Vector((max(e.x, 0), max(e.y, 0), max(e.z, 0))).length
            return out + min(max(e.x, e.y, e.z), 0.0)
        return f
    open_pts = H.posed(curlQ(a, s, {f: (0.08, 0.0) for f in FINGERS}))
    d = 0.0
    while any(sdf_at(d)(p) < 0.0008 for p, fk, _ in open_pts if fk not in ('finger1',)):
        d += 0.001
    curls, worst = solve_wrap(a, s, sdf_at(d), max_base=1.3, thumb_max=0.7)
    # phone matrix: origin = centre of its back, +Y = top, +Z = screen
    y = top; z = nrm; x = y.cross(z)
    M = Matrix((x, y, z)).transposed().to_4x4(); M.translation = Vector((0, yoff, d))
    return curls, M, worst


def cigarette(a, s, r=0.0040, along=0.0):
    """Cigarette through the gap between index and middle finger (middle phalanges), axis along the
    palm normal, lit end out of the back of the hand. Returns (curls, spread, cig matrix, clearance)."""
    H = rigctl.Hand(a, s)
    curls = {'finger1': (0.25, 0.0), 'finger2': (0.22, 0.0), 'finger3': (0.25, 0.0), 'finger4': (0.85, 0.3), 'finger5': (0.95, 0.3)}
    best = None
    for sp in [i * 0.03 for i in range(0, 10)]:
        for sign in (1, -1):
            spread = {'finger2': sign * sp, 'finger3': -sign * sp * 0.5}
            pts = H.posed(curlQ(a, s, curls, spread))
            P2 = [p for p, fk, dom in pts if fk == 'finger2' and ('-2.' in dom or '-3.' in dom)]
            P3 = [p for p, fk, dom in pts if fk == 'finger3' and ('-2.' in dom or '-3.' in dom)]
            c2 = sum(P2, Vector()) / len(P2); c3 = sum(P3, Vector()) / len(P3)
            both = P2 + P3
            for u in (0.4, 0.5, 0.6):
                for dy in (-0.008, -0.004, 0.0, 0.004):
                    p0 = c2.lerp(c3, u) + Vector((0, dy, 0))
                    # clearance: distance from the line through p0 along Z to the two fingers
                    cl = min(Vector((p.x - p0.x, p.y - p0.y)).length for p in both)
                    if best is None or (cl >= r and (best[0] < r or sp < best[1])) or (best[0] < r and cl > best[0]):
                        best = (cl, sp, sign, p0.copy(), spread)
        if best and best[0] >= r: break
    cl, sp, sign, p0, spread = best
    z = Vector((0, 0, -1)); y = Vector((0, 1, 0)); x = y.cross(z)
    M = Matrix((x, y, z)).transposed().to_4x4()
    M.translation = Vector((p0.x, p0.y, p0.z)) - z * 0.016          # held at the filter/paper join
    return curls, spread, M, cl
