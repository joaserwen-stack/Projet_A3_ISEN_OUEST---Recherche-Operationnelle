import time
import math
from utils import load_marchandises, print_results

# Dimensions wagon standard
L_WAG, l_WAG, H_WAG = 11.583, 2.294, 2.569
VOL_WAG = L_WAG * l_WAG * H_WAG


class Marchandise:
    __slots__ = ['id', 'rotations']

    def __init__(self, data: dict):
        self.id = data['id']
        L, l, H = data['longueur'], data['largeur'], data['hauteur']

        if data.get('retournable', 1) == 0:
            rot = [(L, l, H), (l, L, H)]
        else:
            rot = [(L, l, H), (L, H, l), (l, L, H), (l, H, L), (H, L, l), (H, l, L)]

        self.rotations = sorted(set(rot), key=lambda r: r[2])


class Wagon:
    __slots__ = ['boites', 'coins', 'vol_used']

    def __init__(self):
        self.boites: list[tuple] = []
        self.coins: set[tuple] = {(0.0, 0.0, 0.0)}
        self.vol_used: float = 0.0

    def intersecte(self, b1: tuple) -> bool:
        for b2 in self.boites:
            if (b1[0] < b2[0] + b2[3] - 1e-4 and b1[0] + b1[3] > b2[0] + 1e-4 and
                    b1[1] < b2[1] + b2[4] - 1e-4 and b1[1] + b1[4] > b2[1] + 1e-4 and
                    b1[2] < b2[2] + b2[5] - 1e-4 and b1[2] + b1[5] > b2[2] + 1e-4):
                return True
        return False

    def est_supportee(self, xmin: float, xmax: float, ymin: float, ymax: float,
                      zmin: float, seuil: float = 0.70) -> bool:
        if zmin <= 1e-4:
            return True

        aire_base = (xmax - xmin) * (ymax - ymin)
        aire_support = 0.0

        for b_xmin, b_ymin, b_zmin, b_L, b_l, b_H in self.boites:
            if abs(b_zmin + b_H - zmin) <= 1e-4:
                ix_min = max(xmin, b_xmin)
                ix_max = min(xmax, b_xmin + b_L)
                iy_min = max(ymin, b_ymin)
                iy_max = min(ymax, b_ymin + b_l)
                if ix_max > ix_min and iy_max > iy_min:
                    aire_support += (ix_max - ix_min) * (iy_max - iy_min)

        return (aire_support / aire_base) >= seuil

    def placer(self, coin: tuple, rL: float, rl: float, rH: float) -> None:
        cx, cy, cz = coin
        self.boites.append((cx, cy, cz, rL, rl, rH))
        self.vol_used += rL * rl * rH
        self.coins.discard(coin)
        for npt in [(cx + rL, cy, cz), (cx, cy + rl, cz), (cx, cy, cz + rH)]:
            if npt[0] <= L_WAG and npt[1] <= l_WAG and npt[2] <= H_WAG:
                self.coins.add(npt)


def placer_item(item: Marchandise, wagons: list[Wagon]) -> None:
    """First-fit across wagons, best position within wagon (minimise volume restant)."""
    for w in wagons:
        best_local = None  # (remaining, coin, rotation)

        for coin in sorted(w.coins, key=lambda c: (c[2], c[0], c[1])):
            cx, cy, cz = coin
            for rL, rl, rH in item.rotations:
                if cx + rL <= L_WAG + 1e-4 and cy + rl <= l_WAG + 1e-4 and cz + rH <= H_WAG + 1e-4:
                    if not w.intersecte((cx, cy, cz, rL, rl, rH)):
                        if w.est_supportee(cx, cx + rL, cy, cy + rl, cz):
                            remaining = VOL_WAG - w.vol_used - rL * rl * rH
                            if best_local is None or remaining < best_local[0]:
                                best_local = (remaining, coin, (rL, rl, rH))

        if best_local is not None:
            _, coin, (rL, rl, rH) = best_local
            w.placer(coin, rL, rl, rH)
            return

    # Aucun wagon disponible — ouverture d'un nouveau
    nw = Wagon()
    rL, rl, rH = item.rotations[0]
    nw.boites.append((0.0, 0.0, 0.0, rL, rl, rH))
    nw.vol_used = rL * rl * rH
    nw.coins = {(rL, 0.0, 0.0), (0.0, rl, 0.0), (0.0, 0.0, rH)}
    wagons.append(nw)


if __name__ == "__main__":
    print("=" * 65)
    print("  D3 ONLINE - CORNER POINTS BEST-FIT LOCAL")
    print("=" * 65)

    marchandises = load_marchandises()
    if not marchandises:
        raise SystemExit("Erreur : Impossible de charger les données.")

    vol_total = sum(m['longueur'] * m['largeur'] * m['hauteur'] for m in marchandises)
    borne_inf = math.ceil(vol_total / VOL_WAG)

    print(f"Chargement : {len(marchandises)} marchandises chargées.")
    print(f"Volume total : {vol_total:.2f} m³ | Borne inférieure théorique : {borne_inf} wagons")
    print("-" * 65)

    items = [Marchandise(m) for m in marchandises]
    wagons: list[Wagon] = []

    t_debut = time.time()
    for item in items:
        placer_item(item, wagons)
    temps_total = time.time() - t_debut

    nb_wagons = len(wagons)
    volume_perdu = nb_wagons * VOL_WAG - vol_total

    print_results("d=3", "Online Corner-Points Best-Fit Local", nb_wagons, volume_perdu, temps_total)
