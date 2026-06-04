import time
import random
import math
from multiprocessing import Pool, cpu_count
from utils import load_marchandises, print_results

# ═══════════════════════════════════════════════════════════════════
# CONSTANTES ET CONFIGURATION
# ═══════════════════════════════════════════════════════════════════
L_WAG, l_WAG, H_WAG = 11.583, 2.294, 2.569  # Dimensions d'un wagon en mètres
VOL_WAG = L_WAG * l_WAG * H_WAG
TEMPS_MAX = 300
TAILLE_POPULATION = 20

# ═══════════════════════════════════════════════════════════════════
# CLASSES (STRUCTURES DE DONNÉES PURES)
# ═══════════════════════════════════════════════════════════════════
class Marchandise:
    def __init__(self, data):
        self.id = data['id']
        L, l, H = data['longueur'], data['largeur'], data['hauteur']

        if data.get('retournable', 1) == 0:
            rot = [(L, l, H), (l, L, H)]
        else:
            rot = [(L, l, H), (L, H, l), (l, L, H), (l, H, L), (H, L, l), (H, l, L)]

        # L'heuristique vitale de la V1.5 : on trie pour tasser au sol
        self.rotations = sorted(list(set(rot)), key=lambda r: r[2])

class Wagon:
    def __init__(self):
        self.boites = []
        self.coins = {(0.0, 0.0, 0.0)}

    def intersecte(self, b1):
        for b2 in self.boites:
            if (b1[0] < b2[0] + b2[3] - 1e-4 and b1[0] + b1[3] > b2[0] + 1e-4 and
                    b1[1] < b2[1] + b2[4] - 1e-4 and b1[1] + b1[4] > b2[1] + 1e-4 and
                    b1[2] < b2[2] + b2[5] - 1e-4 and b1[2] + b1[5] > b2[2] + 1e-4):
                return True
        return False

# ═══════════════════════════════════════════════════════════════════
# MULTIPROCESSING : WORKER (module-level pour pickling)
# ═══════════════════════════════════════════════════════════════════
_pool_dict_items = None

def _init_pool(di):
    global _pool_dict_items
    _pool_dict_items = di

def _eval_wrapper(args):
    individu, record = args
    return evaluer_liste(individu, _pool_dict_items, record)

# ═══════════════════════════════════════════════════════════════════
# PHASE 2 : ÉVALUATION GÉOMÉTRIQUE (BEST-FIT V2.0)
# ═══════════════════════════════════════════════════════════════════
def evaluer_liste(ordre, dict_items, record_wagons_actuel):
    wagons = []

    for oid in ordre:
        item = dict_items[oid]
        best = None  # (remaining_vol, wagon_idx, coin, rot_tuple)

        for wi, w in enumerate(wagons):
            vol_used = sum(b[3] * b[4] * b[5] for b in w.boites)
            placed_in_wagon = False
            for coin in sorted(w.coins, key=lambda c: (c[0], c[2], c[1])):
                if placed_in_wagon:
                    break
                cx, cy, cz = coin
                for rL, rl, rH in item.rotations:
                    if cx + rL <= L_WAG + 1e-4 and cy + rl <= l_WAG + 1e-4 and cz + rH <= H_WAG + 1e-4:
                        if not w.intersecte((cx, cy, cz, rL, rl, rH)):
                            remaining = VOL_WAG - vol_used - rL * rl * rH
                            if best is None or remaining < best[0]:
                                best = (remaining, wi, coin, (rL, rl, rH))
                            placed_in_wagon = True
                            break

        if best is not None:
            _, wi, coin, (rL, rl, rH) = best
            w = wagons[wi]
            cx, cy, cz = coin
            w.boites.append((cx, cy, cz, rL, rl, rH))
            w.coins.discard(coin)
            for npt in [(cx + rL, cy, cz), (cx, cy + rl, cz), (cx, cy, cz + rH)]:
                if npt[0] <= L_WAG and npt[1] <= l_WAG and npt[2] <= H_WAG:
                    w.coins.add(npt)
        else:
            # EARLY EXIT
            if len(wagons) + 1 > record_wagons_actuel:
                return float('inf'), float('inf')

            nw = Wagon()
            rL, rl, rH = item.rotations[0]
            nw.boites.append((0.0, 0.0, 0.0, rL, rl, rH))
            nw.coins = {(rL, 0.0, 0.0), (0.0, rl, 0.0), (0.0, 0.0, rH)}
            wagons.append(nw)

    nb_wagons = len(wagons)
    if nb_wagons == 0:
        return float('inf'), float('inf')

    vol_dernier_wagon = sum(b[3] * b[4] * b[5] for b in wagons[-1].boites)
    fitness = (nb_wagons - 1) + (vol_dernier_wagon / VOL_WAG)

    return nb_wagons, fitness

# ═══════════════════════════════════════════════════════════════════
# OPERATEURS GENETIQUES
# ═══════════════════════════════════════════════════════════════════
def croisement_ox(p1, p2):
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

def mutation_swap(ordre, prob=0.35):
    if random.random() < prob:
        idx1, idx2 = random.sample(range(len(ordre)), 2)
        ordre[idx1], ordre[idx2] = ordre[idx2], ordre[idx1]
    return ordre

# ═══════════════════════════════════════════════════════════════════
# EXECUTION PRINCIPALE
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 65)
    print("  D3 OFFLINE - ALGORITHME GÉNÉTIQUE V2.0 (Best-Fit + Pool)")
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

    # Population initiale : 4 seeds heuristiques + reste aléatoire
    def seed_par(key_fn):
        return sorted(ids, key=lambda i: key_fn(dict_items[i].rotations[0]), reverse=True)

    seeds = [
        seed_par(lambda r: r[0] * r[1] * r[2]),   # volume desc
        seed_par(lambda r: r[2]),                   # hauteur desc
        seed_par(lambda r: r[0] * r[1]),            # aire base desc
        seed_par(lambda r: r[0]),                   # longueur desc
    ]
    population = seeds[:]
    while len(population) < TAILLE_POPULATION:
        indiv = list(ids)
        random.shuffle(indiv)
        population.append(indiv)
    print(f"Population de départ : {len(seeds)} seeds heuristiques + {TAILLE_POPULATION - len(seeds)} aléatoires.")
    print("-" * 65)

    t_debut = time.time()
    generation = 0
    meilleur_nb_wagons = float('inf')
    meilleur_fitness = float('inf')

    with Pool(processes=n_workers, initializer=_init_pool, initargs=(dict_items,)) as pool:
        while time.time() - t_debut < TEMPS_MAX:
            generation += 1

            args = [(individu, meilleur_nb_wagons) for individu in population]
            resultats = pool.map(_eval_wrapper, args)
            scores_pop = [(nb_w, fit, individu) for (nb_w, fit), individu in zip(resultats, population)]

            scores_pop.sort(key=lambda x: x[1])
            gen_best_nb, gen_best_fit, _ = scores_pop[0]

            if gen_best_fit < meilleur_fitness:
                meilleur_nb_wagons = gen_best_nb
                meilleur_fitness = gen_best_fit
                taux_dernier = (meilleur_fitness - (meilleur_nb_wagons - 1)) * 100
                print(f"[Gen {generation:03d}] NOUVEAU RECORD : {meilleur_nb_wagons} wagons (Dernier rempli à {taux_dernier:.1f}%) | Temps : {time.time() - t_debut:.2f}s")

                if meilleur_nb_wagons <= borne_inf:
                    print(f"\n[STOP] Borne inférieure théorique absolue ({borne_inf}) atteinte !")
                    break
            elif generation % 50 == 0:
                print(f"   [Gen {generation:03d}] Recherche en cours... (Temps : {time.time() - t_debut:.2f}s)")

            top_10 = [indiv for nb, fit, indiv in scores_pop[:10]]

            enfants = []
            while len(enfants) < 10:
                p1, p2 = random.sample(top_10, 2)
                enfant = croisement_ox(p1, p2)
                enfant = mutation_swap(enfant, prob=0.35)
                enfants.append(enfant)

            population = top_10 + enfants

    temps_total = time.time() - t_debut
    print("-" * 65)
    print("  FIN DU CHRONO DE CALCUL")
    print("-" * 65)

    volume_perdu = (meilleur_nb_wagons * VOL_WAG) - vol_total
    print_results("d=3", "Offline V2.0 (Best-Fit + Pool)", meilleur_nb_wagons, volume_perdu, temps_total)
