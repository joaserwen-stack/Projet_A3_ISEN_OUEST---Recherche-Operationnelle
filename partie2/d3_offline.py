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
SEUIL_CATACLYSME = 200   # générations sans amélioration avant reset population
FREQ_OR_OPT = 50         # appliquer Or-opt au meilleur toutes les N générations
MAX_TIME_OR_OPT = 3.0    # budget temps (s) par appel Or-opt

# ═══════════════════════════════════════════════════════════════════
# CLASSES
# ═══════════════════════════════════════════════════════════════════
class Marchandise:
    def __init__(self, data):
        self.id = data['id']
        L, l, H = data['longueur'], data['largeur'], data['hauteur']

        if data.get('retournable', 1) == 0:
            rot = [(L, l, H), (l, L, H)]
        else:
            rot = [(L, l, H), (L, H, l), (l, L, H), (l, H, L), (H, L, l), (H, l, L)]

        # Trier par hauteur croissante pour tasser au sol en priorité
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
# MULTIPROCESSING : workers déclarés au niveau module pour pickling
# ═══════════════════════════════════════════════════════════════════
_pool_dict_items = None

def _init_pool(di):
    global _pool_dict_items
    _pool_dict_items = di

def _eval_wrapper(args):
    individu, record = args
    return evaluer_liste(individu, _pool_dict_items, record)

# ═══════════════════════════════════════════════════════════════════
# ÉVALUATION GÉOMÉTRIQUE
# Décodeur : permutation d'IDs → nb wagons + fitness
# Placement : DBLF (Deepest Bottom-Left Fill) + Best-Fit wagon
#   - DBLF : tri coins par (x, z, y) → remplit de l'avant vers l'arrière
#             puis plancher, puis Y — optimal pour wagons longs
#   - Best-Fit : parmi les wagons acceptant l'item, choisit celui avec
#                le moins de volume résiduel → minimise les vides
# ═══════════════════════════════════════════════════════════════════
def evaluer_liste(ordre, dict_items, record_wagons_actuel):
    wagons = []

    for oid in ordre:
        item = dict_items[oid]
        best = None  # (remaining_vol, wagon_idx, coin, rot_tuple)

        for wi, w in enumerate(wagons):
            vol_used = sum(b[3] * b[4] * b[5] for b in w.boites)
            placed_in_wagon = False
            for coin in sorted(w.coins, key=lambda c: (c[0], c[2], c[1])):  # DBLF
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
            # Early exit : dépasser le record actuel ne sert à rien
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
# RECHERCHE LOCALE : Or-opt-1 (composante mémétique)
# Passe unique first-improvement : pour chaque item, teste toutes les
# positions de réinsertion et applique la première amélioration trouvée.
# Transforme le GA pur en algorithme mémétique.
# ═══════════════════════════════════════════════════════════════════
def local_search_or_opt1(ordre, dict_items, record):
    current = ordre[:]
    _, current_fit = evaluer_liste(current, dict_items, record)
    t_start = time.time()

    for i in range(len(current)):
        if time.time() - t_start > MAX_TIME_OR_OPT:
            break
        item = current[i]
        sans_item = current[:i] + current[i+1:]
        for j in range(len(sans_item) + 1):
            if j == i:
                continue
            candidat = sans_item[:j] + [item] + sans_item[j:]
            _, fit = evaluer_liste(candidat, dict_items, record)
            if fit < current_fit:
                current = candidat
                current_fit = fit
                break  # first-improvement : passer à l'item suivant

    return current, current_fit

# ═══════════════════════════════════════════════════════════════════
# OPÉRATEURS GÉNÉTIQUES
# ═══════════════════════════════════════════════════════════════════
def croisement_ox(p1, p2):
    """Order Crossover (OX) : préserve les sous-séquences relatives."""
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

def mutation(ordre, prob=0.35):
    """3 opérateurs au choix uniforme : swap, insertion, 2-opt (reverse segment)."""
    if random.random() >= prob:
        return ordre
    op = random.randint(0, 2)
    if op == 0:  # swap
        i, j = random.sample(range(len(ordre)), 2)
        ordre[i], ordre[j] = ordre[j], ordre[i]
    elif op == 1:  # insertion : déplace 1 item vers une autre position
        i = random.randrange(len(ordre))
        item = ordre.pop(i)
        j = random.randrange(len(ordre) + 1)
        ordre.insert(j, item)
    else:  # 2-opt : inverse un segment aléatoire
        i, j = sorted(random.sample(range(len(ordre)), 2))
        ordre[i:j+1] = ordre[i:j+1][::-1]
    return ordre

# ═══════════════════════════════════════════════════════════════════
# EXÉCUTION PRINCIPALE
# Architecture : GA mémétique V4.0
#   - Population  : 4 seeds heuristiques + 16 aléatoires
#   - Sélection   : top-10 élitiste
#   - Croisement  : OX sur permutations
#   - Mutation    : 3 opérateurs (swap / insertion / 2-opt), taux adaptatif
#                   0–50 gens stagnation → prob 0.35
#                   50–100 gens         → prob 0.50
#                   100+ gens           → prob 0.65
#   - Or-opt-1    : recherche locale first-improvement sur meilleur individu
#                   toutes les FREQ_OR_OPT générations (composante mémétique)
#   - Cataclysme  : si stagnation > SEUIL_CATACLYSME, garder top-2 + reset
#   - Pool        : évaluations parallèles sur cpu_count() workers
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 65)
    print("  D3 OFFLINE - GA MÉMÉTIQUE V4.0 (Or-opt + Multi-mut + Adapt)")
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
    meilleur_individu = None
    gens_sans_amelioration = 0

    with Pool(processes=n_workers, initializer=_init_pool, initargs=(dict_items,)) as pool:
        while time.time() - t_debut < TEMPS_MAX:
            generation += 1

            # Évaluation parallèle
            args = [(individu, meilleur_nb_wagons) for individu in population]
            resultats = pool.map(_eval_wrapper, args)
            scores_pop = [(nb_w, fit, individu) for (nb_w, fit), individu in zip(resultats, population)]
            scores_pop.sort(key=lambda x: x[1])
            gen_best_nb, gen_best_fit, gen_best_ind = scores_pop[0]

            # Or-opt mémétique : recherche locale sur meilleur individu
            if generation % FREQ_OR_OPT == 0:
                improved_ind, improved_fit = local_search_or_opt1(gen_best_ind, dict_items, meilleur_nb_wagons)
                if improved_fit < gen_best_fit:
                    gen_best_fit = improved_fit
                    gen_best_nb = math.floor(improved_fit) + 1
                    gen_best_ind = improved_ind
                    scores_pop[0] = (gen_best_nb, gen_best_fit, gen_best_ind)
                    print(f"   [Gen {generation:04d}] Or-opt amélioration : fitness {improved_fit:.4f}")

            if gen_best_fit < meilleur_fitness:
                meilleur_nb_wagons = gen_best_nb
                meilleur_fitness = gen_best_fit
                meilleur_individu = gen_best_ind[:]
                gens_sans_amelioration = 0
                taux_dernier = (meilleur_fitness - (meilleur_nb_wagons - 1)) * 100
                print(f"[Gen {generation:04d}] NOUVEAU RECORD : {meilleur_nb_wagons} wagons (Dernier rempli à {taux_dernier:.1f}%) | Temps : {time.time() - t_debut:.2f}s")

                if meilleur_nb_wagons <= borne_inf:
                    print(f"\n[STOP] Borne inférieure théorique absolue ({borne_inf}) atteinte !")
                    break
            else:
                gens_sans_amelioration += 1
                if generation % 50 == 0:
                    print(f"   [Gen {generation:04d}] Recherche en cours... (stagnation : {gens_sans_amelioration} gens | Temps : {time.time() - t_debut:.2f}s)")

            # Cataclysme : stagnation prolongée → réinitialiser sauf top-2
            if gens_sans_amelioration >= SEUIL_CATACLYSME:
                top_2 = [indiv for _, _, indiv in scores_pop[:2]]
                population = top_2[:]
                while len(population) < TAILLE_POPULATION:
                    indiv = list(ids)
                    random.shuffle(indiv)
                    population.append(indiv)
                gens_sans_amelioration = 0
                print(f"   [Gen {generation:04d}] *** CATACLYSME *** diversité réinitialisée (top-2 conservé)")
                continue

            # Mutation adaptative : prob augmente avec la stagnation
            if gens_sans_amelioration < 50:
                mut_prob = 0.35
            elif gens_sans_amelioration < 100:
                mut_prob = 0.50
            else:
                mut_prob = 0.65

            top_10 = [indiv for nb, fit, indiv in scores_pop[:10]]
            enfants = []
            while len(enfants) < 10:
                p1, p2 = random.sample(top_10, 2)
                enfant = croisement_ox(p1, p2)
                enfant = mutation(enfant, prob=mut_prob)
                enfants.append(enfant)

            population = top_10 + enfants

    temps_total = time.time() - t_debut
    print("-" * 65)
    print("  FIN DU CHRONO DE CALCUL")
    print("-" * 65)

    volume_perdu = (meilleur_nb_wagons * VOL_WAG) - vol_total
    print_results("d=3", "Offline V4.0 (GA Mémétique)", meilleur_nb_wagons, volume_perdu, temps_total)
