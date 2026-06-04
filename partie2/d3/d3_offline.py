import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import random
import math
from multiprocessing import Pool, cpu_count
from utils import load_marchandises, print_results

# Dimensions wagon standard
L_WAG, l_WAG, H_WAG = 11.583, 2.294, 2.569
VOL_WAG = L_WAG * l_WAG * H_WAG

# Paramètres GA
TEMPS_MAX = 300
TAILLE_POPULATION = 64
N_ELITE = 16
N_IMMIGRANTS = 4
PROB_MUTATION = 0.60


class Marchandise:
    __slots__ = ['id', 'rotations']

    def __init__(self, data: dict):
        self.id = data['id']
        L, l, H = data['longueur'], data['largeur'], data['hauteur']

        if data.get('retournable', 1) == 0:
            rot = [(L, l, H), (l, L, H)]
        else:
            rot = [(L, l, H), (L, H, l), (l, L, H), (l, H, L), (H, L, l), (H, l, L)]

        # Hauteur croissante : placement le plus stable en premier (CG bas)
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


# --- Multiprocessing : globals nécessaires pour éviter le pickling par worker ---

_pool_dict_items = None


def _init_pool(di: dict) -> None:
    global _pool_dict_items
    _pool_dict_items = di


def _eval_wrapper(args: tuple) -> tuple:
    individu, record = args
    return evaluer_liste(individu, _pool_dict_items, record)


# --- Placement 3D (chemin critique — logique figée) ---

def evaluer_liste(ordre: list, dict_items: dict, record_wagons_actuel: int) -> tuple:
    wagons: list[Wagon] = []

    for oid in ordre:
        item = dict_items[oid]
        best = None

        for wi, w in enumerate(wagons):
            placed = False
            for coin in sorted(w.coins, key=lambda c: (c[2], c[0], c[1])):
                if placed:
                    break
                cx, cy, cz = coin
                for rL, rl, rH in item.rotations:
                    if cx + rL <= L_WAG + 1e-4 and cy + rl <= l_WAG + 1e-4 and cz + rH <= H_WAG + 1e-4:
                        if not w.intersecte((cx, cy, cz, rL, rl, rH)):
                            if w.est_supportee(cx, cx + rL, cy, cy + rl, cz):
                                remaining = VOL_WAG - w.vol_used - rL * rl * rH
                                if best is None or remaining < best[0]:
                                    best = (remaining, wi, coin, (rL, rl, rH))
                                placed = True
                                break

        if best is not None:
            _, wi, coin, (rL, rl, rH) = best
            w = wagons[wi]
            cx, cy, cz = coin
            w.boites.append((cx, cy, cz, rL, rl, rH))
            w.vol_used += rL * rl * rH
            w.coins.discard(coin)
            for npt in [(cx + rL, cy, cz), (cx, cy + rl, cz), (cx, cy, cz + rH)]:
                if npt[0] <= L_WAG and npt[1] <= l_WAG and npt[2] <= H_WAG:
                    w.coins.add(npt)
        else:
            if len(wagons) + 1 > record_wagons_actuel:
                return float('inf'), float('inf')
            nw = Wagon()
            chosen = next(
                ((rL, rl, rH) for rL, rl, rH in item.rotations
                 if rL <= L_WAG + 1e-4 and rl <= l_WAG + 1e-4 and rH <= H_WAG + 1e-4),
                item.rotations[0]
            )
            rL, rl, rH = chosen
            nw.boites.append((0.0, 0.0, 0.0, rL, rl, rH))
            nw.vol_used = rL * rl * rH
            nw.coins = {(rL, 0.0, 0.0), (0.0, rl, 0.0), (0.0, 0.0, rH)}
            wagons.append(nw)

    if not wagons:
        return float('inf'), float('inf')

    nb_wagons = len(wagons)
    # Fitness = (N-1) + taux_dernier : distingue solutions à même nombre de wagons
    fitness = (nb_wagons - 1) + (wagons[-1].vol_used / VOL_WAG)
    return nb_wagons, fitness


# --- Extraction du contenu des wagons avec IDs (pour visualisation) ---

def extraire_wagons(ordre: list, dict_items: dict) -> list[list[tuple]]:
    """Re-runs packing on given order, collecting box positions with item IDs.

    Returns list of wagons; each wagon is a list of
    (cx, cy, cz, rL, rl, rH, item_id) tuples.
    """
    wagons_boites: list[list] = []
    wagons_coins: list[set] = []
    wagons_vol: list[float] = []

    def _intersecte(boites, b1):
        for b2 in boites:
            if (b1[0] < b2[0] + b2[3] - 1e-4 and b1[0] + b1[3] > b2[0] + 1e-4 and
                    b1[1] < b2[1] + b2[4] - 1e-4 and b1[1] + b1[4] > b2[1] + 1e-4 and
                    b1[2] < b2[2] + b2[5] - 1e-4 and b1[2] + b1[5] > b2[2] + 1e-4):
                return True
        return False

    def _est_supportee(boites, xmin, xmax, ymin, ymax, zmin, seuil=0.70):
        if zmin <= 1e-4:
            return True
        aire_base = (xmax - xmin) * (ymax - ymin)
        aire_sup = 0.0
        for b in boites:
            if abs(b[2] + b[5] - zmin) <= 1e-4:
                ox = min(xmax, b[0] + b[3]) - max(xmin, b[0])
                oy = min(ymax, b[1] + b[4]) - max(ymin, b[1])
                if ox > 0 and oy > 0:
                    aire_sup += ox * oy
        return (aire_sup / aire_base) >= seuil

    for oid in ordre:
        item = dict_items[oid]
        best = None

        for wi in range(len(wagons_boites)):
            placed = False
            for coin in sorted(wagons_coins[wi], key=lambda c: (c[2], c[0], c[1])):
                if placed:
                    break
                cx, cy, cz = coin
                for rL, rl, rH in item.rotations:
                    if cx + rL <= L_WAG + 1e-4 and cy + rl <= l_WAG + 1e-4 and cz + rH <= H_WAG + 1e-4:
                        if not _intersecte(wagons_boites[wi], (cx, cy, cz, rL, rl, rH)):
                            if _est_supportee(wagons_boites[wi], cx, cx + rL, cy, cy + rl, cz):
                                remaining = VOL_WAG - wagons_vol[wi] - rL * rl * rH
                                if best is None or remaining < best[0]:
                                    best = (remaining, wi, coin, (rL, rl, rH))
                                placed = True
                                break

        if best is not None:
            _, wi, coin, (rL, rl, rH) = best
            cx, cy, cz = coin
            wagons_boites[wi].append((cx, cy, cz, rL, rl, rH, oid))
            wagons_vol[wi] += rL * rl * rH
            wagons_coins[wi].discard(coin)
            for npt in [(cx + rL, cy, cz), (cx, cy + rl, cz), (cx, cy, cz + rH)]:
                if npt[0] <= L_WAG and npt[1] <= l_WAG and npt[2] <= H_WAG:
                    wagons_coins[wi].add(npt)
        else:
            chosen = next(
                ((rL, rl, rH) for rL, rl, rH in item.rotations
                 if rL <= L_WAG + 1e-4 and rl <= l_WAG + 1e-4 and rH <= H_WAG + 1e-4),
                item.rotations[0]
            )
            rL, rl, rH = chosen
            wagons_boites.append([(0.0, 0.0, 0.0, rL, rl, rH, oid)])
            wagons_coins.append({(rL, 0.0, 0.0), (0.0, rl, 0.0), (0.0, 0.0, rH)})
            wagons_vol.append(rL * rl * rH)

    return wagons_boites


# --- Opérateurs génétiques ---

def croisement_ox(p1: list, p2: list) -> list:
    """Order Crossover (OX) : préserve l'ordre relatif de p2 hors du segment copié de p1."""
    n = len(p1)
    a, b = sorted(random.sample(range(n), 2))
    enfant = [None] * n
    enfant[a:b+1] = p1[a:b+1]
    pris = set(enfant[a:b+1])

    pos = (b + 1) % n
    for i in range(n):
        curr = p2[(b + 1 + i) % n]
        if curr not in pris:
            enfant[pos] = curr
            pos = (pos + 1) % n
    return enfant


def mutation(ordre: list, prob: float = PROB_MUTATION) -> list:
    if random.random() >= prob:
        return ordre
    op = random.randint(0, 3)
    if op == 0:  # swap
        i, j = random.sample(range(len(ordre)), 2)
        ordre[i], ordre[j] = ordre[j], ordre[i]
    elif op == 1:  # insertion
        i = random.randrange(len(ordre))
        item = ordre.pop(i)
        ordre.insert(random.randrange(len(ordre) + 1), item)
    elif op == 2:  # 2-opt
        i, j = sorted(random.sample(range(len(ordre)), 2))
        ordre[i:j+1] = ordre[i:j+1][::-1]
    else:  # scramble
        i, j = sorted(random.sample(range(len(ordre)), 2))
        segment = ordre[i:j+1]
        random.shuffle(segment)
        ordre[i:j+1] = segment
    return ordre


# --- Algorithme génétique ---

def _individu_aleatoire(ids: list) -> list:
    indiv = list(ids)
    random.shuffle(indiv)
    return indiv


class AlgorithmeGenetique:
    def __init__(self, dict_items: dict, ids: list):
        self.dict_items = dict_items
        self.ids = ids
        self.population: list[list] = []
        self.meilleur_nb_wagons: float = float('inf')
        self.meilleur_fitness: float = float('inf')
        self.meilleur_individu: list = []
        self.generation: int = 0

    def _creer_seeds(self) -> list[list]:
        def seed_par(key_fn):
            return sorted(self.ids, key=lambda i: key_fn(self.dict_items[i].rotations[0]), reverse=True)
        return [
            seed_par(lambda r: r[0] * r[1] * r[2]),  # volume décroissant
            seed_par(lambda r: r[2]),                  # hauteur décroissante
            seed_par(lambda r: r[0] * r[1]),           # surface de base décroissante
            seed_par(lambda r: r[0]),                  # longueur décroissante
        ]

    def initialiser(self) -> None:
        seeds = self._creer_seeds()

        print("Pré-calcul des heuristiques initiales...")
        for idx, seed in enumerate(seeds):
            nb_w, fit = evaluer_liste(seed, self.dict_items, self.meilleur_nb_wagons)
            if fit < self.meilleur_fitness:
                self.meilleur_nb_wagons = nb_w
                self.meilleur_fitness = fit
                self.meilleur_individu = seed[:]
                taux = (fit - (nb_w - 1)) * 100
                print(f"[Init] Seed {idx+1} validée → {nb_w} wagons (Dernier rempli à {taux:.1f}%)")

        self.population = seeds[:]
        while len(self.population) < TAILLE_POPULATION:
            self.population.append(_individu_aleatoire(self.ids))

        n_aleatoires = TAILLE_POPULATION - len(seeds)
        print(f"Population prête : {len(seeds)} seeds + {n_aleatoires} aléatoires.")

    def _evaluer(self, pool: Pool) -> list[tuple]:
        args = [(indiv, self.meilleur_nb_wagons) for indiv in self.population]
        resultats = pool.map(_eval_wrapper, args)
        scores = [(nb_w, fit, indiv) for (nb_w, fit), indiv in zip(resultats, self.population)]
        scores.sort(key=lambda x: x[1])
        return scores

    def _evoluer(self, scores: list[tuple]) -> None:
        elite = [indiv for _, _, indiv in scores[:N_ELITE]]
        n_enfants = TAILLE_POPULATION - N_ELITE - N_IMMIGRANTS

        enfants = []
        while len(enfants) < n_enfants:
            p1, p2 = random.sample(elite, 2)
            enfants.append(mutation(croisement_ox(p1, p2)))

        immigrants = [_individu_aleatoire(self.ids) for _ in range(N_IMMIGRANTS)]
        self.population = elite + enfants + immigrants

    def run(self, pool: Pool, borne_inf: int) -> float:
        t_debut = time.time()

        while time.time() - t_debut < TEMPS_MAX:
            self.generation += 1
            scores = self._evaluer(pool)
            gen_best_nb, gen_best_fit, gen_best_indiv = scores[0]

            if gen_best_fit < self.meilleur_fitness:
                self.meilleur_nb_wagons = gen_best_nb
                self.meilleur_fitness = gen_best_fit
                self.meilleur_individu = gen_best_indiv[:]
                taux = (self.meilleur_fitness - (self.meilleur_nb_wagons - 1)) * 100
                elapsed = time.time() - t_debut
                print(f"[Gen {self.generation:03d}] NOUVEAU RECORD : {self.meilleur_nb_wagons} wagons "
                      f"(Dernier rempli à {taux:.1f}%) | Temps : {elapsed:.2f}s")
                if self.meilleur_nb_wagons <= borne_inf:
                    print(f"\n[STOP] Borne inférieure théorique absolue ({borne_inf}) atteinte !")
                    break
            elif self.generation % 50 == 0:
                elapsed = time.time() - t_debut
                print(f"   [Gen {self.generation:03d}] Recherche en cours... (Temps : {elapsed:.2f}s)")

            self._evoluer(scores)

        return time.time() - t_debut


if __name__ == "__main__":
    print("=" * 65)
    print("  D3 OFFLINE - ALGORITHME GÉNÉTIQUE V6.0 (Retour aux bases)")
    print("=" * 65)

    marchandises = load_marchandises()
    if not marchandises:
        raise SystemExit("Erreur : Impossible de charger les données.")

    dict_items = {m['id']: Marchandise(m) for m in marchandises}
    ids = list(dict_items.keys())

    vol_total = sum(m['longueur'] * m['largeur'] * m['hauteur'] for m in marchandises)
    borne_inf = math.ceil(vol_total / VOL_WAG)
    n_workers = cpu_count()

    print(f"Chargement : {len(marchandises)} marchandises chargées.")
    print(f"Volume total : {vol_total:.2f} m³ | Borne inférieure théorique : {borne_inf} wagons")
    print(f"Parallélisation : {n_workers} workers")
    print("-" * 65)

    ga = AlgorithmeGenetique(dict_items, ids)
    ga.initialiser()

    print("-" * 65)
    with Pool(processes=n_workers, initializer=_init_pool, initargs=(dict_items,)) as pool:
        temps_total = ga.run(pool, borne_inf)

    print("-" * 65)
    print("  FIN DU CHRONO DE CALCUL")
    print("-" * 65)

    volume_perdu = (ga.meilleur_nb_wagons * VOL_WAG) - vol_total
    print_results("d=3", "Offline V6.0", ga.meilleur_nb_wagons, volume_perdu, temps_total)

    # Extraction du contenu des wagons pour visualisation
    print("\nExtraction du contenu des wagons...")
    wagons_boites = extraire_wagons(ga.meilleur_individu, dict_items)
    print(f"{len(wagons_boites)} wagons extraits.")

    try:
        from d3_visualisation import visualiser_wagons
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rendus")
        os.makedirs(output_dir, exist_ok=True)
        visualiser_wagons(wagons_boites, output_dir=output_dir)
        print(f"Images sauvegardées dans : {output_dir}")
    except ImportError:
        print("d3_visualisation non disponible — visualisation ignorée.")
