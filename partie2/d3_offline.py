import time
import random
import math
from multiprocessing import Pool, cpu_count
from utils import load_marchandises, print_results

L_WAG, l_WAG, H_WAG = 11.583, 2.294, 2.569
VOL_WAG = L_WAG * l_WAG * H_WAG
TEMPS_MAX = 300
TAILLE_POPULATION = 64


class Marchandise:
    def __init__(self, data):
        self.id = data['id']
        L, l, H = data['longueur'], data['largeur'], data['hauteur']

        if data.get('retournable', 1) == 0:
            rot = [(L, l, H), (l, L, H)]
        else:
            rot = [(L, l, H), (L, H, l), (l, L, H), (l, H, L), (H, L, l), (H, l, L)]

        # Trier par hauteur croissante : favorise les rotations à faible CG (stabilité sol)
        self.rotations = sorted(list(set(rot)), key=lambda r: r[2])


class Wagon:
    def __init__(self):
        self.boites = []
        self.coins = {(0.0, 0.0, 0.0)}  # Points extrêmes candidats pour le placement suivant
        self.vol_used = 0.0

    def intersecte(self, b1):
        for b2 in self.boites:
            if (b1[0] < b2[0] + b2[3] - 1e-4 and b1[0] + b1[3] > b2[0] + 1e-4 and
                    b1[1] < b2[1] + b2[4] - 1e-4 and b1[1] + b1[4] > b2[1] + 1e-4 and
                    b1[2] < b2[2] + b2[5] - 1e-4 and b1[2] + b1[5] > b2[2] + 1e-4):
                return True
        return False

    def est_supportee(self, xmin, xmax, ymin, ymax, zmin, seuil=0.70):
        eps = 1e-4

        if zmin <= eps:
            return True

        aire_support_totale = 0.0
        aire_base_boite = (xmax - xmin) * (ymax - ymin)

        for b in self.boites:
            b_xmin, b_ymin, b_zmin, b_L, b_l, b_H = b
            b_xmax = b_xmin + b_L
            b_ymax = b_ymin + b_l
            b_zmax = b_zmin + b_H

            if abs(b_zmax - zmin) <= eps:
                inter_xmin = max(xmin, b_xmin)
                inter_xmax = min(xmax, b_xmax)
                inter_ymin = max(ymin, b_ymin)
                inter_ymax = min(ymax, b_ymax)

                if inter_xmax > inter_xmin and inter_ymax > inter_ymin:
                    aire_support_totale += (inter_xmax - inter_xmin) * (inter_ymax - inter_ymin)

        return (aire_support_totale / aire_base_boite) >= seuil


_pool_dict_items = None

def _init_pool(di):
    global _pool_dict_items
    _pool_dict_items = di

def _eval_wrapper(args):
    individu, record = args
    return evaluer_liste(individu, _pool_dict_items, record)


def evaluer_liste(ordre, dict_items, record_wagons_actuel):
    wagons = []

    for oid in ordre:
        item = dict_items[oid]
        best = None

        for wi, w in enumerate(wagons):
            placed_in_wagon = False

            # Z en premier : tasser au sol avant de monter en hauteur
            for coin in sorted(w.coins, key=lambda c: (c[2], c[0], c[1])):
                if placed_in_wagon:
                    break
                cx, cy, cz = coin
                for rL, rl, rH in item.rotations:
                    if cx + rL <= L_WAG + 1e-4 and cy + rl <= l_WAG + 1e-4 and cz + rH <= H_WAG + 1e-4:
                        if not w.intersecte((cx, cy, cz, rL, rl, rH)):
                            if w.est_supportee(cx, cx + rL, cy, cy + rl, cz, seuil=0.70):
                                remaining = VOL_WAG - w.vol_used - rL * rl * rH
                                if best is None or remaining < best[0]:
                                    best = (remaining, wi, coin, (rL, rl, rH))
                                placed_in_wagon = True
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
            # Élagage : on abandonne toute solution strictement pire que le record courant
            if len(wagons) + 1 > record_wagons_actuel:
                return float('inf'), float('inf')

            nw = Wagon()
            # rotations[0] a la plus petite hauteur (tri ascendant) : placement le plus stable à l'origine
            rL, rl, rH = item.rotations[0]
            nw.boites.append((0.0, 0.0, 0.0, rL, rl, rH))
            nw.vol_used = rL * rl * rH
            nw.coins = {(rL, 0.0, 0.0), (0.0, rl, 0.0), (0.0, 0.0, rH)}
            wagons.append(nw)

    nb_wagons = len(wagons)
    if nb_wagons == 0:
        return float('inf'), float('inf')

    # Fitness fractionnaire : (N-1) wagons pleins + taux de remplissage du dernier
    # Permet au GA de distinguer des solutions avec le même nombre de wagons
    fitness = (nb_wagons - 1) + (wagons[-1].vol_used / VOL_WAG)

    return nb_wagons, fitness


def croisement_ox(p1, p2):
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


def mutation(ordre, prob=0.60):
    if random.random() >= prob:
        return ordre
    op = random.randint(0, 3)
    if op == 0:  # swap
        i, j = random.sample(range(len(ordre)), 2)
        ordre[i], ordre[j] = ordre[j], ordre[i]
    elif op == 1:  # insertion
        i = random.randrange(len(ordre))
        item = ordre.pop(i)
        j = random.randrange(len(ordre) + 1)
        ordre.insert(j, item)
    elif op == 2:  # 2-opt (inversion de segment)
        i, j = sorted(random.sample(range(len(ordre)), 2))
        ordre[i:j+1] = ordre[i:j+1][::-1]
    else:  # scramble
        i, j = sorted(random.sample(range(len(ordre)), 2))
        segment = ordre[i:j+1]
        random.shuffle(segment)
        ordre[i:j+1] = segment
    return ordre


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

    def seed_par(key_fn):
        return sorted(ids, key=lambda i: key_fn(dict_items[i].rotations[0]), reverse=True)

    # 4 seeds déterministes couvrant différentes stratégies de tri initial
    seeds = [
        seed_par(lambda r: r[0] * r[1] * r[2]),  # volume décroissant
        seed_par(lambda r: r[2]),                  # hauteur décroissante
        seed_par(lambda r: r[0] * r[1]),           # surface de base décroissante
        seed_par(lambda r: r[0]),                  # longueur décroissante
    ]

    print("-" * 65)
    print("Pré-calcul des heuristiques initiales...")
    meilleur_nb_wagons = float('inf')
    meilleur_fitness = float('inf')

    for idx, seed in enumerate(seeds):
        nb_w, fit = evaluer_liste(seed, dict_items, meilleur_nb_wagons)
        if fit < meilleur_fitness:
            meilleur_nb_wagons = nb_w
            meilleur_fitness = fit
            taux = (fit - (nb_w - 1)) * 100
            print(f"[Init] Seed {idx+1} validée → {nb_w} wagons (Dernier rempli à {taux:.1f}%)")

    population = seeds[:]
    while len(population) < TAILLE_POPULATION:
        indiv = list(ids)
        random.shuffle(indiv)
        population.append(indiv)

    print(f"Population prête : {len(seeds)} seeds + {TAILLE_POPULATION - len(seeds)} aléatoires.")
    print("-" * 65)

    t_debut = time.time()
    generation = 0

    with Pool(processes=n_workers, initializer=_init_pool, initargs=(dict_items,)) as pool:
        while time.time() - t_debut < TEMPS_MAX:
            generation += 1

            args = [(individu, meilleur_nb_wagons) for individu in population]
            resultats = pool.map(_eval_wrapper, args)

            scores_pop = [(nb_w, fit, individu) for (nb_w, fit), individu in zip(resultats, population)]
            scores_pop.sort(key=lambda x: x[1])
            gen_best_nb, gen_best_fit, gen_best_ind = scores_pop[0]

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

            # Élitisme : top 16 survivent, 4 immigrants aléatoires maintiennent la diversité
            top_16 = [indiv for _, _, indiv in scores_pop[:16]]

            enfants = []
            while len(enfants) < (TAILLE_POPULATION - 16 - 4):
                p1, p2 = random.sample(top_16, 2)
                enfant = croisement_ox(p1, p2)
                enfant = mutation(enfant, prob=0.60)
                enfants.append(enfant)

            immigrants = []
            for _ in range(4):
                indiv = list(ids)
                random.shuffle(indiv)
                immigrants.append(indiv)

            population = top_16 + enfants + immigrants

    temps_total = time.time() - t_debut
    print("-" * 65)
    print("  FIN DU CHRONO DE CALCUL")
    print("-" * 65)

    volume_perdu = (meilleur_nb_wagons * VOL_WAG) - vol_total
    print_results("d=3", "Offline V6.0", meilleur_nb_wagons, volume_perdu, temps_total)
