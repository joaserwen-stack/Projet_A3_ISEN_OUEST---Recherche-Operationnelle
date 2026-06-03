"""Bin-Packing 3D Offline — DBLF Normalisé + Algorithme Génétique + LNS"""
import sys
import time
import random
from typing import List, Tuple, Optional

try:
    sys.path.insert(0, __file__[:__file__.rfind('/')])
    from utils import load_marchandises, print_results
except ImportError:
    def load_marchandises(): return []
    def print_results(*args, **kwargs): pass

WX, WY, WZ = 11.583, 2.294, 2.569
WVOL       = WX * WY * WZ
EPS        = 1e-6

POP_SIZE = 80
N_GEN    = 200
STAG_MAX = 20
LNS_ITER = 3000

_ROT6 = [(0,1,2),(0,2,1),(1,0,2),(1,2,0),(2,0,1),(2,1,0)]
_ROT2 = [(0,1,2),(1,0,2)]


class Item3D:
    __slots__ = ('id', 'nom', 'dims', 'retournable', 'n_states', 'vol')

    def __init__(self, id_: int, nom: str, dims: Tuple[float,float,float], retournable: bool):
        self.id, self.nom, self.dims, self.retournable = id_, nom, dims, retournable
        self.n_states = 6 if retournable else 2
        self.vol = dims[0] * dims[1] * dims[2]

    def oriented(self, state: int) -> Tuple[float,float,float]:
        r = _ROT6[state] if self.retournable else _ROT2[state]
        return self.dims[r[0]], self.dims[r[1]], self.dims[r[2]]


class PlacedItem:
    __slots__ = ('item', 'x', 'y', 'z', 'dx', 'dy', 'dz')

    def __init__(self, item: Item3D, x: float, y: float, z: float, dx: float, dy: float, dz: float):
        self.item = item
        self.x, self.y, self.z = x, y, z
        self.dx, self.dy, self.dz = dx, dy, dz


class Space:
    __slots__ = ('x', 'y', 'z', 'w', 'l', 'h', 'vol')

    def __init__(self, x: float, y: float, z: float, w: float, l: float, h: float):
        self.x, self.y, self.z = x, y, z
        self.w, self.l, self.h = w, l, h
        self.vol = w * l * h


class Wagon:
    def __init__(self):
        self.spaces: List[Space] = [Space(0.0, 0.0, 0.0, WX, WY, WZ)]
        self.placed_items: List[PlacedItem] = []
        self.vol_used: float = 0.0

    @property
    def vol_free(self) -> float:
        return WVOL - self.vol_used

    def _contact_area(self, x: float, y: float, z: float, dx: float, dy: float, dz: float) -> float:
        x2, y2, z2 = x + dx, y + dy, z + dz
        area = 0.0
        if x  <= EPS:           area += dy * dz
        if abs(x2 - WX) <= EPS: area += dy * dz
        if y  <= EPS:           area += dx * dz
        if abs(y2 - WY) <= EPS: area += dx * dz
        if z  <= EPS:           area += dx * dy
        if abs(z2 - WZ) <= EPS: area += dx * dy
        for p in self.placed_items:
            px2, py2, pz2 = p.x+p.dx, p.y+p.dy, p.z+p.dz
            if abs(x-px2) <= EPS or abs(x2-p.x) <= EPS:
                area += max(0.0, min(y2,py2)-max(y,p.y)) * max(0.0, min(z2,pz2)-max(z,p.z))
            if abs(y-py2) <= EPS or abs(y2-p.y) <= EPS:
                area += max(0.0, min(x2,px2)-max(x,p.x)) * max(0.0, min(z2,pz2)-max(z,p.z))
            if abs(z-pz2) <= EPS or abs(z2-p.z) <= EPS:
                area += max(0.0, min(x2,px2)-max(x,p.x)) * max(0.0, min(y2,py2)-max(y,p.y))
        return area

    def place_item(self, item: Item3D) -> bool:
        best: Optional[tuple] = None

        for sp in self.spaces:
            for state in range(item.n_states):
                dx, dy, dz = item.oriented(state)
                if dx <= sp.w + EPS and dy <= sp.l + EPS and dz <= sp.h + EPS:
                    score = (self._contact_area(sp.x, sp.y, sp.z, dx, dy, dz) * 100
                             + (item.vol / sp.vol) * 50
                             - (sp.z / WZ) * 1000
                             - (sp.x / WX) * 100
                             - (sp.y / WY) * 10)
                    if best is None or score > best[0]:
                        best = (score, sp, dx, dy, dz)

        if best is None:
            return False

        _, sp, dx, dy, dz = best
        self.placed_items.append(PlacedItem(item, sp.x, sp.y, sp.z, dx, dy, dz))
        self.vol_used += item.vol
        self._split_spaces(sp.x, sp.y, sp.z, dx, dy, dz)
        return True

    def _split_spaces(self, ix: float, iy: float, iz: float, iw: float, il: float, ih: float):
        surviving, generated = [], []
        for s in self.spaces:
            if (s.x >= ix+iw-EPS or s.x+s.w <= ix+EPS or
                    s.y >= iy+il-EPS or s.y+s.l <= iy+EPS or
                    s.z >= iz+ih-EPS or s.z+s.h <= iz+EPS):
                surviving.append(s)
            else:
                if ix    > s.x+EPS:     generated.append(Space(s.x,   s.y,   s.z,   ix-s.x,          s.l,             s.h))
                if ix+iw < s.x+s.w-EPS: generated.append(Space(ix+iw, s.y,   s.z,   s.x+s.w-(ix+iw), s.l,             s.h))
                if iy    > s.y+EPS:     generated.append(Space(s.x,   s.y,   s.z,   s.w,             iy-s.y,          s.h))
                if iy+il < s.y+s.l-EPS: generated.append(Space(s.x,   iy+il, s.z,   s.w,             s.y+s.l-(iy+il), s.h))
                if iz    > s.z+EPS:     generated.append(Space(s.x,   s.y,   s.z,   s.w,             s.l,             iz-s.z))
                if iz+ih < s.z+s.h-EPS: generated.append(Space(s.x,   s.y,   iz+ih, s.w,             s.l,             s.z+s.h-(iz+ih)))

        self.spaces = surviving + generated
        self.spaces.sort(key=lambda s: s.vol, reverse=True)

        final: List[Space] = []
        for s1 in self.spaces:
            if not any(s1.x >= s2.x-EPS and s1.y >= s2.y-EPS and s1.z >= s2.z-EPS and
                       s1.x+s1.w <= s2.x+s2.w+EPS and s1.y+s1.l <= s2.y+s2.l+EPS and
                       s1.z+s1.h <= s2.z+s2.h+EPS for s2 in final):
                final.append(s1)
        self.spaces = final


def decode_sequence(seq: List[int], items: List[Item3D]) -> List[Wagon]:
    wagons = [Wagon()]
    for idx in seq:
        item = items[idx]
        if not any(w.place_item(item) for w in wagons):
            w = Wagon(); w.place_item(item); wagons.append(w)
    return wagons


def crossover_ox(p1: List[int], p2: List[int], a: int, b: int) -> List[int]:
    segment = set(p1[a:b+1])
    child = [-1] * len(p1)
    child[a:b+1] = p1[a:b+1]
    tail = [x for x in p2 if x not in segment]
    j = 0
    for i in range(len(child)):
        if child[i] == -1:
            child[i] = tail[j]; j += 1
    return child


def _evaluate(pop: List[List[int]], items: List[Item3D]):
    scored = []
    for seq in pop:
        wagons = decode_sequence(seq, items)
        fitness = len(wagons) + wagons[-1].vol_used / WVOL
        scored.append((fitness, len(wagons), seq, wagons))
    scored.sort(key=lambda x: x[0])
    return scored


def _cataclysm(elite: List[List[int]], heuristics: List[List[int]], n: int) -> List[List[int]]:
    pop = [s.copy() for s in elite[:3]]
    while len(pop) < POP_SIZE:
        seq = random.choice(heuristics).copy()
        for _ in range(random.randint(3, 12)):
            a, b = random.sample(range(n), 2)
            seq[a], seq[b] = seq[b], seq[a]
        pop.append(seq)
    return pop


def _next_gen(scored, best_wagons: List[Wagon], id_to_idx: dict, n: int) -> List[List[int]]:
    pop = [scored[0][2].copy(), scored[1][2].copy()]

    while len(pop) < POP_SIZE:
        c1, c2 = random.choice(scored), random.choice(scored)
        pop.append((c1 if c1[0] < c2[0] else c2)[2].copy())

    for i in range(2, POP_SIZE - 1, 2):
        if random.random() < 0.85:
            a, b = sorted(random.sample(range(n), 2))
            p1, p2 = pop[i], pop[i+1]
            pop[i], pop[i+1] = crossover_ox(p1, p2, a, b), crossover_ox(p2, p1, a, b)

    for i in range(2, POP_SIZE):
        if random.random() < 0.35:
            if random.random() < 0.5 and best_wagons:
                overflow = [id_to_idx[p.item.id] for p in best_wagons[-1].placed_items]
                if overflow:
                    target = random.choice(overflow)
                    if target in pop[i]:
                        pos = pop[i].index(target)
                        pop[i].insert(random.randint(0, int(n * 0.10)), pop[i].pop(pos))
            else:
                a, b = random.sample(range(n), 2)
                pop[i][a], pop[i][b] = pop[i][b], pop[i][a]
    return pop


def _lns_improve(seq: List[int], wagons: List[Wagon], items: List[Item3D],
                 id_to_idx: dict, n: int) -> tuple:
    """
    Large Neighborhood Search: hill-climbing après GA.
    Extrait des items du dernier wagon, les réinsère ailleurs, accepte si mieux.
    """
    best_seq    = seq.copy()
    best_wagons = wagons
    best_fit    = len(wagons) + wagons[-1].vol_used / WVOL

    for _ in range(LNS_ITER):
        last_idxs = [id_to_idx[p.item.id] for p in best_wagons[-1].placed_items]
        if not last_idxs:
            break

        candidate = best_seq.copy()
        k = min(len(last_idxs), random.randint(1, 3))
        targets = random.sample(last_idxs, k)

        for t in targets:
            candidate.remove(t)
        for t in targets:
            # Réinsérer dans les 30% premiers — zone de "priorité haute"
            candidate.insert(random.randint(0, max(1, int(n * 0.30))), t)

        cand_wagons = decode_sequence(candidate, items)
        cand_fit    = len(cand_wagons) + cand_wagons[-1].vol_used / WVOL

        if cand_fit < best_fit:
            best_seq, best_wagons, best_fit = candidate, cand_wagons, cand_fit
            print(f"  [LNS] {len(best_wagons)} wagons  (fitness {best_fit:.4f})")

    return best_seq, best_wagons


if __name__ == '__main__':
    data = load_marchandises()
    if not data:
        sys.exit(0)

    items = [Item3D(d['id'], d['nom'], (d['longueur'], d['largeur'], d['hauteur']), bool(d['retournable'])) for d in data]
    id_to_idx = {obj.id: i for i, obj in enumerate(items)}
    n = len(items)
    base = list(range(n))

    heuristics = [
        sorted(base, key=lambda i: items[i].vol, reverse=True),
        sorted(base, key=lambda i: max(items[i].dims), reverse=True),
        sorted(base, key=lambda i: min(items[i].dims) if items[i].retournable else items[i].dims[2], reverse=True),
        sorted(base, key=lambda i: items[i].dims[0] * items[i].dims[1], reverse=True),
    ]

    pop = [h.copy() for h in heuristics]
    while len(pop) < POP_SIZE:
        seq = base.copy(); random.shuffle(seq); pop.append(seq)

    best_n, best_fit, best_seq, best_wagons = float('inf'), float('inf'), None, None
    stag = 0

    t0 = time.time()
    print(f"Bin-Packing 3D Offline  (pop={POP_SIZE}, gen={N_GEN})")

    for gen in range(N_GEN):
        scored = _evaluate(pop, items)
        fit, n_wagons, seq, wagons = scored[0]

        if n_wagons < best_n or (n_wagons == best_n and fit < best_fit - EPS):
            best_n, best_fit, best_seq, best_wagons = n_wagons, fit, seq.copy(), wagons
            print(f"  [{gen:3d}] {best_n} wagons  (fitness {best_fit:.4f})")
            stag = 0
        else:
            stag += 1

        if stag >= STAG_MAX:
            print(f"  [{gen:3d}] Redémarrage")
            pop = _cataclysm([s[2] for s in scored], heuristics, n)
            stag = 0
        else:
            pop = _next_gen(scored, best_wagons, id_to_idx, n)

    print(f"\n  --- LNS ({LNS_ITER} itérations) ---")
    best_seq, best_wagons = _lns_improve(best_seq, best_wagons, items, id_to_idx, n)
    best_n = len(best_wagons)

    elapsed = time.time() - t0
    print(f"\n{'='*55}")
    print(f"  Résultat : {best_n} wagons  |  {elapsed:.2f} s")
    print("=" * 55)

    print_results("d=3", "Offline", best_n, best_wagons[-1].vol_free, elapsed)
    taux = 100.0 * sum(w.vol_used for w in best_wagons) / (best_n * WVOL)
    print(f"  Taux d'occupation : {taux:.1f}%")
