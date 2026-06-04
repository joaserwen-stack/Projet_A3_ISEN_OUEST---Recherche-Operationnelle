"""Bin-Packing 3D Offline — Vrai MaxRects 3D & Deep Fit + Algorithme Génétique"""
import sys
import time
import random
from typing import List, Tuple, Optional

try:
    sys.path.insert(0, __file__[:__file__.rfind('/')])
    from utils import load_marchandises, print_results
except ImportError:
    def load_marchandises(): return []
    def print_results(*_, **__): pass

WX, WY, WZ = 11.583, 2.294, 2.569
WVOL       = WX * WY * WZ
EPS        = 1e-6

POP_SIZE = 80
N_GEN    = 200
STAG_MAX = 20

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

    def __init__(self, item: Item3D, x: float, y: float, z: float,
                 dx: float, dy: float, dz: float):
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

    def place_item(self, item: Item3D) -> bool:
        """Sélection Deep Fit Pure par tri lexicographique."""
        best_placement = None  # Stockera (key, sp, dx, dy, dz)

        for sp in self.spaces:
            for state in range(item.n_states):
                dx, dy, dz = item.oriented(state)
                if dx <= sp.w + EPS and dy <= sp.l + EPS and dz <= sp.h + EPS:
                    # CLÉ DE TRI DEEP FIT : Z d'abord (sol), puis X (fond), puis Y (gauche)
                    # Tie-break : -sp.vol pour choisir le plus grand espace à coordonnées égales
                    placement_key = (sp.z, sp.x, sp.y, -sp.vol)

                    if best_placement is None or placement_key < best_placement[0]:
                        best_placement = (placement_key, sp, dx, dy, dz)

        if best_placement is None:
            return False

        _, sp, dx, dy, dz = best_placement
        # L'objet est placé exactement au coin inférieur-gauche de l'espace sélectionné
        self.placed_items.append(PlacedItem(item, sp.x, sp.y, sp.z, dx, dy, dz))
        self.vol_used += item.vol

        # Découpe géométrique MaxRects 3D
        self._update_spaces(sp.x, sp.y, sp.z, dx, dy, dz)
        return True

    def _update_spaces(self, ix: float, iy: float, iz: float,
                       iw: float, il: float, ih: float) -> None:
        """Algorithme de division MaxRects 3D exact."""
        temp_spaces = []

        for sp in self.spaces:
            # Si l'espace ne chevauche PAS l'item placé, on le garde intact
            if (sp.x + sp.w <= ix + EPS or sp.x >= ix + iw - EPS or
                    sp.y + sp.l <= iy + EPS or sp.y >= iy + il - EPS or
                    sp.z + sp.h <= iz + EPS or sp.z >= iz + ih - EPS):
                temp_spaces.append(sp)
                continue

            # Si intersection, on coupe l'espace selon les 6 faces de l'objet placé
            # Face Gauche (-X)
            if ix > sp.x + EPS:
                temp_spaces.append(Space(sp.x, sp.y, sp.z, ix - sp.x, sp.l, sp.h))
            # Face Droite (+X)
            if sp.x + sp.w > ix + iw + EPS:
                temp_spaces.append(Space(ix + iw, sp.y, sp.z, (sp.x + sp.w) - (ix + iw), sp.l, sp.h))
            # Face Fond (-Y)
            if iy > sp.y + EPS:
                temp_spaces.append(Space(sp.x, sp.y, sp.z, sp.w, iy - sp.y, sp.h))
            # Face Devant (+Y)
            if sp.y + sp.l > iy + il + EPS:
                temp_spaces.append(Space(sp.x, iy + il, sp.z, sp.w, (sp.y + sp.l) - (iy + il), sp.h))
            # Face Dessous (-Z)
            if iz > sp.z + EPS:
                temp_spaces.append(Space(sp.x, sp.y, sp.z, sp.w, sp.l, iz - sp.z))
            # Face Dessus (+Z)
            if sp.z + sp.h > iz + ih + EPS:
                temp_spaces.append(Space(sp.x, sp.y, iz + ih, sp.w, sp.l, (sp.z + sp.h) - (iz + ih)))

        # Élimination des espaces dominés (inclus entièrement dans un plus grand)
        # On trie par volume décroissant pour insérer les plus grands blocs en premier
        temp_spaces.sort(key=lambda s: -s.vol)
        final: List[Space] = []
        for s1 in temp_spaces:
            if not any(
                    s1.x >= s2.x - EPS and s1.y >= s2.y - EPS and s1.z >= s2.z - EPS and
                    s1.x + s1.w <= s2.x + s2.w + EPS and
                    s1.y + s1.l <= s2.y + s2.l + EPS and
                    s1.z + s1.h <= s2.z + s2.h + EPS
                    for s2 in final
            ):
                final.append(s1)
        self.spaces = final


# ---------------------------------------------------------------------------
# Algorithme Génétique (Ordonnancement)
# ---------------------------------------------------------------------------

def decode_sequence(seq: List[int], items: List[Item3D]) -> List[Wagon]:
    wagons: List[Wagon] = [Wagon()]
    for idx in seq:
        item = items[idx]
        if not any(w.place_item(item) for w in wagons):
            nw = Wagon()
            nw.place_item(item)
            wagons.append(nw)
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


def _evaluate(seq_pop: List[List[int]], items: List[Item3D]):
    scored = []
    for seq in seq_pop:
        wagons = decode_sequence(seq, items)
        fitness = len(wagons) + wagons[-1].vol_used / WVOL
        scored.append((fitness, len(wagons), seq, wagons))
    scored.sort(key=lambda x: x[0])
    return scored


def _inject_diversity(scored, n_items: int) -> List[List[int]]:
    """Injection de diversité : Top-5 intact + hyper-mutation par inversion + immigrants aléatoires."""
    elite = [s[2] for s in scored[:5]]
    result = [s.copy() for s in elite]

    # Hyper-mutation par inversion de segments sur des parents de l'élite
    while len(result) < POP_SIZE // 2:
        parent = random.choice(elite).copy()
        a, b   = sorted(random.sample(range(n_items), 2))
        parent[a:b+1] = list(reversed(parent[a:b+1]))
        result.append(parent)

    # Immigrants aléatoires : exploration totale de nouvelles zones
    base = list(range(n_items))
    while len(result) < POP_SIZE:
        seq = base.copy(); random.shuffle(seq)
        result.append(seq)

    return result


def _next_gen(scored, best_wagons: List[Wagon], id_to_idx: dict, n_items: int) -> List[List[int]]:
    result = [scored[0][2].copy(), scored[1][2].copy()]

    while len(result) < POP_SIZE:
        c1, c2 = random.choice(scored), random.choice(scored)
        result.append((c1 if c1[0] < c2[0] else c2)[2].copy())

    for i in range(2, POP_SIZE - 1, 2):
        if random.random() < 0.85:
            a, b = sorted(random.sample(range(n_items), 2))
            p1, p2 = result[i], result[i+1]
            result[i], result[i+1] = crossover_ox(p1, p2, a, b), crossover_ox(p2, p1, a, b)

    for i in range(2, POP_SIZE):
        if random.random() < 0.35:
            if random.random() < 0.5:
                overflow = [id_to_idx[p.item.id] for p in best_wagons[-1].placed_items]
                if overflow:
                    target = random.choice(overflow)
                    if target in result[i]:
                        pos = result[i].index(target)
                        result[i].insert(random.randint(0, int(n_items * 0.10)), result[i].pop(pos))
            else:
                a, b = random.sample(range(n_items), 2)
                result[i][a], result[i][b] = result[i][b], result[i][a]
    return result


def main() -> None:
    data = load_marchandises()
    if not data:
        sys.exit(0)

    items = [
        Item3D(d['id'], d['nom'], (d['longueur'], d['largeur'], d['hauteur']), bool(d['retournable']))
        for d in data
    ]
    id_to_idx = {obj.id: i for i, obj in enumerate(items)}
    n_items = len(items)
    base = list(range(n_items))

    heuristics = [
        sorted(base, key=lambda i: items[i].vol, reverse=True),
        sorted(base, key=lambda i: max(items[i].dims), reverse=True),
        sorted(base, key=lambda i: min(items[i].dims) if items[i].retournable else items[i].dims[2], reverse=True),
        sorted(base, key=lambda i: items[i].dims[0] * items[i].dims[1], reverse=True),
    ]

    pop = [h.copy() for h in heuristics]
    while len(pop) < POP_SIZE:
        seq = base.copy(); random.shuffle(seq); pop.append(seq)

    best_n:      float       = float('inf')
    best_fit:    float       = float('inf')
    best_wagons: List[Wagon] = []
    stag = 0

    t0 = time.time()
    print(f"Bin-Packing 3D Offline - True MaxRects & Deep Fit (pop={POP_SIZE}, gen={N_GEN})")

    for gen in range(N_GEN):
        scored = _evaluate(pop, items)
        fit, n_wagons, _, wagons = scored[0]

        if n_wagons < best_n or (n_wagons == best_n and fit < best_fit - EPS):
            best_n, best_fit, best_wagons = n_wagons, fit, wagons
            print(f"  [{gen:3d}] {best_n} wagons  (fitness {best_fit:.4f})")
            stag = 0
        else:
            stag += 1

        if stag >= STAG_MAX:
            print(f"  [{gen:3d}] Stagnation détectée -> Injection de Diversité (Sang Neuf)")
            pop = _inject_diversity(scored, n_items)
            stag = 0
        else:
            pop = _next_gen(scored, best_wagons, id_to_idx, n_items)

    elapsed = time.time() - t0
    print(f"\n{'='*55}")
    print(f"  Résultat : {int(best_n)} wagons  |  {elapsed:.2f} s")
    print("=" * 55)

    print_results("d=3", "Offline", int(best_n), best_wagons[-1].vol_free, elapsed)
    taux = 100.0 * sum(w.vol_used for w in best_wagons) / (best_n * WVOL)
    print(f"  Taux d'occupation : {taux:.1f}%")


if __name__ == '__main__':
    main()