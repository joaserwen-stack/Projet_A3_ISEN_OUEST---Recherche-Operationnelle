import time
import random
import math
from collections import namedtuple
from multiprocessing import Pool, cpu_count
from utils import load_marchandises, print_results

# ═══════════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════════
LONGUEUR_WAG = 11.583   # mètres
LARGEUR_WAG  = 2.294
HAUTEUR_WAG  = 2.569
VOLUME_WAG   = LONGUEUR_WAG * LARGEUR_WAG * HAUTEUR_WAG

TAILLE_POPULATION = 20
TEMPS_MAX         = 300   # secondes
SEUIL_CATACLYSME  = 200   # générations sans amélioration → reset
FREQ_OR_OPT       = 50    # générations entre deux appels Or-opt
MAX_TEMPS_OR_OPT  = 3.0   # secondes max par appel Or-opt

# ═══════════════════════════════════════════════════════════════════
# STRUCTURES
# ═══════════════════════════════════════════════════════════════════

# Boite placée dans un wagon : position (x,y,z) + dimensions (lon,larg,haut)
Boite = namedtuple('Boite', ['x', 'y', 'z', 'lon', 'larg', 'haut'])

# Meilleur placement trouvé pour un item lors du Best-Fit
PlacementCandidat = namedtuple('PlacementCandidat', ['volume_restant', 'index_wagon', 'coin', 'rotation'])


class Marchandise:
    def __init__(self, data):
        self.id = data['id']
        L, l, H = data['longueur'], data['largeur'], data['hauteur']

        if data.get('retournable', 1) == 0:
            rotations_possibles = [(L, l, H), (l, L, H)]
        else:
            rotations_possibles = [(L, l, H), (L, H, l), (l, L, H), (l, H, L), (H, L, l), (H, l, L)]

        # Tri par hauteur croissante : privilégier la pose à plat
        self.rotations = sorted(list(set(rotations_possibles)), key=lambda r: r[2])

        # Propriétés pour les seeds heuristiques (basées sur la rotation à plat)
        rotation_a_plat  = self.rotations[0]
        self.volume      = L * l * H
        self.hauteur_min = rotation_a_plat[2]
        self.aire_base   = rotation_a_plat[0] * rotation_a_plat[1]
        self.longueur    = rotation_a_plat[0]


class Wagon:
    def __init__(self):
        self.boites = []
        self.coins  = {(0.0, 0.0, 0.0)}

    @property
    def volume_utilise(self):
        return sum(b.lon * b.larg * b.haut for b in self.boites)

    def intersecte(self, c):
        """Retourne True si la boite candidate c chevauche une boite existante."""
        for b in self.boites:
            if (c.x < b.x + b.lon - 1e-4 and c.x + c.lon > b.x + 1e-4 and
                    c.y < b.y + b.larg - 1e-4 and c.y + c.larg > b.y + 1e-4 and
                    c.z < b.z + b.haut - 1e-4 and c.z + c.haut > b.z + 1e-4):
                return True
        return False

# ═══════════════════════════════════════════════════════════════════
# MULTIPROCESSING : workers au niveau module (requis pour pickle)
# ═══════════════════════════════════════════════════════════════════
_items_worker = None

def _init_worker(items):
    global _items_worker
    _items_worker = items

def _worker(args):
    ordre, record = args
    return evaluer(ordre, _items_worker, record)

# ═══════════════════════════════════════════════════════════════════
# ÉVALUATION : permutation d'IDs → (nb_wagons, fitness)
#
# Placement par DBLF + Best-Fit :
#   DBLF (Deepest Bottom-Left Fill) : tri des coins candidats par
#     (x, z, y) → remplit de l'avant vers l'arrière, puis plancher,
#     puis Y — adapté aux wagons longs
#   Best-Fit : parmi les wagons pouvant accueillir l'item, choisit
#     celui avec le moins de volume résiduel → minimise les vides
# ═══════════════════════════════════════════════════════════════════
def evaluer(ordre, items, record):
    wagons = []

    for identifiant in ordre:
        item = items[identifiant]
        meilleur = None  # PlacementCandidat

        for index_wagon, wagon in enumerate(wagons):
            coins_tries = sorted(wagon.coins, key=lambda c: (c[0], c[2], c[1]))  # DBLF
            placement_trouve = False

            for coin in coins_tries:
                if placement_trouve:
                    break
                cx, cy, cz = coin

                for lon, larg, haut in item.rotations:
                    if cx + lon <= LONGUEUR_WAG + 1e-4 and cy + larg <= LARGEUR_WAG + 1e-4 and cz + haut <= HAUTEUR_WAG + 1e-4:
                        candidate = Boite(cx, cy, cz, lon, larg, haut)
                        if not wagon.intersecte(candidate):
                            volume_restant = VOLUME_WAG - wagon.volume_utilise - lon * larg * haut
                            if meilleur is None or volume_restant < meilleur.volume_restant:
                                meilleur = PlacementCandidat(volume_restant, index_wagon, coin, (lon, larg, haut))
                            placement_trouve = True
                            break

        if meilleur is not None:
            wagon = wagons[meilleur.index_wagon]
            cx, cy, cz = meilleur.coin
            lon, larg, haut = meilleur.rotation
            boite = Boite(cx, cy, cz, lon, larg, haut)
            wagon.boites.append(boite)
            wagon.coins.discard(meilleur.coin)
            for nouveau_coin in [(cx + lon, cy, cz), (cx, cy + larg, cz), (cx, cy, cz + haut)]:
                if nouveau_coin[0] <= LONGUEUR_WAG and nouveau_coin[1] <= LARGEUR_WAG and nouveau_coin[2] <= HAUTEUR_WAG:
                    wagon.coins.add(nouveau_coin)
        else:
            # Early exit : inutile de dépasser le record actuel
            if len(wagons) + 1 > record:
                return float('inf'), float('inf')
            nouveau_wagon = Wagon()
            lon, larg, haut = item.rotations[0]
            nouveau_wagon.boites.append(Boite(0.0, 0.0, 0.0, lon, larg, haut))
            nouveau_wagon.coins = {(lon, 0.0, 0.0), (0.0, larg, 0.0), (0.0, 0.0, haut)}
            wagons.append(nouveau_wagon)

    nb_wagons = len(wagons)
    if nb_wagons == 0:
        return float('inf'), float('inf')

    volume_dernier = wagons[-1].volume_utilise
    fitness = (nb_wagons - 1) + (volume_dernier / VOLUME_WAG)
    return nb_wagons, fitness

# ═══════════════════════════════════════════════════════════════════
# RECHERCHE LOCALE : Or-opt-1 (composante mémétique)
# Pour chaque item, teste toutes les positions de réinsertion et
# applique la première amélioration trouvée (first-improvement).
# Une seule passe sur les items, budget temps limité.
# ═══════════════════════════════════════════════════════════════════
def recherche_locale(ordre, items, record):
    ordre_actuel  = ordre[:]
    _, fitness_actuelle = evaluer(ordre_actuel, items, record)
    t_debut = time.time()

    for i in range(len(ordre_actuel)):
        if time.time() - t_debut > MAX_TEMPS_OR_OPT:
            break
        item_deplace = ordre_actuel[i]
        ordre_sans   = ordre_actuel[:i] + ordre_actuel[i+1:]

        for j in range(len(ordre_sans) + 1):
            if j == i:
                continue
            ordre_teste = ordre_sans[:j] + [item_deplace] + ordre_sans[j:]
            _, fitness_teste = evaluer(ordre_teste, items, record)
            if fitness_teste < fitness_actuelle:
                ordre_actuel   = ordre_teste
                fitness_actuelle = fitness_teste
                break  # first-improvement : passer à l'item suivant

    return ordre_actuel, fitness_actuelle

# ═══════════════════════════════════════════════════════════════════
# OPÉRATEURS GÉNÉTIQUES
# ═══════════════════════════════════════════════════════════════════
def croisement(parent1, parent2):
    """Order Crossover (OX) : copie un segment de parent1, complète avec parent2."""
    n = len(parent1)
    debut, fin = sorted(random.sample(range(n), 2))
    enfant = [None] * n
    enfant[debut:fin+1] = parent1[debut:fin+1]
    deja_copie = set(enfant[debut:fin+1])

    position = (fin + 1) % n
    for i in range(n):
        gene = parent2[(fin + 1 + i) % n]
        if gene not in deja_copie:
            enfant[position] = gene
            position = (position + 1) % n
    return enfant


def mutation(ordre, prob=0.35):
    """3 opérateurs au choix uniforme : swap, insertion, 2-opt (reverse segment)."""
    if random.random() >= prob:
        return ordre
    operateur = random.randint(0, 2)
    if operateur == 0:  # swap : échange deux positions
        i, j = random.sample(range(len(ordre)), 2)
        ordre[i], ordre[j] = ordre[j], ordre[i]
    elif operateur == 1:  # insertion : déplace un item vers une autre position
        i = random.randrange(len(ordre))
        item = ordre.pop(i)
        j = random.randrange(len(ordre) + 1)
        ordre.insert(j, item)
    else:  # 2-opt : inverse un segment
        i, j = sorted(random.sample(range(len(ordre)), 2))
        ordre[i:j+1] = ordre[i:j+1][::-1]
    return ordre

# ═══════════════════════════════════════════════════════════════════
# INITIALISATION : population avec seeds heuristiques
# ═══════════════════════════════════════════════════════════════════
def creer_population(ids, items, taille):
    """4 seeds triés par critère heuristique + reste aléatoire."""
    seeds = [
        sorted(ids, key=lambda i: items[i].volume,      reverse=True),
        sorted(ids, key=lambda i: items[i].hauteur_min, reverse=True),
        sorted(ids, key=lambda i: items[i].aire_base,   reverse=True),
        sorted(ids, key=lambda i: items[i].longueur,    reverse=True),
    ]
    population = seeds[:]
    while len(population) < taille:
        individu = list(ids)
        random.shuffle(individu)
        population.append(individu)
    return population, len(seeds)

# ═══════════════════════════════════════════════════════════════════
# EXÉCUTION PRINCIPALE
# Architecture : GA Mémétique V4.0
#   Population  → 4 seeds heuristiques + 16 aléatoires
#   Sélection   → élitisme top-10
#   Croisement  → OX (Order Crossover)
#   Mutation    → 3 opérateurs (swap / insertion / 2-opt), taux adaptatif
#                 stagnation 0–50 gens → 0.35 | 50–100 → 0.50 | 100+ → 0.65
#   Or-opt-1    → recherche locale first-improvement toutes les FREQ_OR_OPT gens
#   Cataclysme  → reset (sauf top-2) après SEUIL_CATACLYSME gens sans record
#   Pool        → évaluations parallèles sur cpu_count() workers
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 65)
    print("  D3 OFFLINE - GA MÉMÉTIQUE V4.0 (Or-opt + Multi-mut + Adapt)")
    print("=" * 65)

    marchandises = load_marchandises()
    if not marchandises:
        raise SystemExit("Erreur : Impossible de charger les données.")

    items = {m['id']: Marchandise(m) for m in marchandises}
    ids   = list(items.keys())

    volume_total = sum(m['longueur'] * m['largeur'] * m['hauteur'] for m in marchandises)
    borne_inf    = math.ceil(volume_total / VOLUME_WAG)
    nb_workers   = cpu_count()

    print(f"Chargement : {len(marchandises)} marchandises chargées.")
    print(f"Volume total : {volume_total:.2f} m³ | Borne inférieure théorique : {borne_inf} wagons")
    print(f"Parallélisation : {nb_workers} workers")

    population, nb_seeds = creer_population(ids, items, TAILLE_POPULATION)
    print(f"Population de départ : {nb_seeds} seeds heuristiques + {TAILLE_POPULATION - nb_seeds} aléatoires.")
    print("-" * 65)

    t_debut              = time.time()
    generation           = 0
    meilleur_nb_wagons   = float('inf')
    meilleure_fitness    = float('inf')
    gens_sans_record     = 0

    with Pool(processes=nb_workers, initializer=_init_worker, initargs=(items,)) as pool:
        while time.time() - t_debut < TEMPS_MAX:
            generation += 1

            # Évaluation parallèle de toute la population
            resultats  = pool.map(_worker, [(ind, meilleur_nb_wagons) for ind in population])
            scores_pop = sorted(
                [(nb, fit, ind) for (nb, fit), ind in zip(resultats, population)],
                key=lambda x: x[1]
            )
            nb_best, fit_best, ind_best = scores_pop[0]

            # Or-opt : recherche locale sur le meilleur individu
            if generation % FREQ_OR_OPT == 0:
                ind_ameliore, fit_ameliore = recherche_locale(ind_best, items, meilleur_nb_wagons)
                if fit_ameliore < fit_best:
                    nb_best, fit_best, ind_best = evaluer(ind_ameliore, items, meilleur_nb_wagons) + (ind_ameliore,)
                    scores_pop[0] = (nb_best, fit_best, ind_best)
                    print(f"   [Gen {generation:04d}] Or-opt amélioration → fitness {fit_best:.4f}")

            # Mise à jour du record global
            if fit_best < meilleure_fitness:
                meilleur_nb_wagons = nb_best
                meilleure_fitness  = fit_best
                gens_sans_record   = 0
                taux_dernier = (meilleure_fitness - (meilleur_nb_wagons - 1)) * 100
                print(f"[Gen {generation:04d}] NOUVEAU RECORD : {meilleur_nb_wagons} wagons "
                      f"(Dernier rempli à {taux_dernier:.1f}%) | Temps : {time.time() - t_debut:.2f}s")
                if meilleur_nb_wagons <= borne_inf:
                    print(f"\n[STOP] Borne inférieure ({borne_inf}) atteinte !")
                    break
            else:
                gens_sans_record += 1
                if generation % 50 == 0:
                    print(f"   [Gen {generation:04d}] Recherche... "
                          f"(stagnation : {gens_sans_record} gens | Temps : {time.time() - t_debut:.2f}s)")

            # Cataclysme : stagnation prolongée → reset sauf top-2
            if gens_sans_record >= SEUIL_CATACLYSME:
                top_2      = [ind for _, _, ind in scores_pop[:2]]
                population = top_2[:]
                while len(population) < TAILLE_POPULATION:
                    individu = list(ids)
                    random.shuffle(individu)
                    population.append(individu)
                gens_sans_record = 0
                print(f"   [Gen {generation:04d}] *** CATACLYSME *** top-2 conservé, reste réinitialisé")
                continue

            # Taux de mutation adaptatif selon la stagnation
            if gens_sans_record < 50:
                taux_mutation = 0.35
            elif gens_sans_record < 100:
                taux_mutation = 0.50
            else:
                taux_mutation = 0.65

            # Évolution : top-10 survivent, 10 enfants générés
            top_10  = [ind for _, _, ind in scores_pop[:10]]
            enfants = []
            while len(enfants) < 10:
                p1, p2  = random.sample(top_10, 2)
                enfant  = croisement(p1, p2)
                enfant  = mutation(enfant, prob=taux_mutation)
                enfants.append(enfant)

            population = top_10 + enfants

    temps_total   = time.time() - t_debut
    volume_perdu  = (meilleur_nb_wagons * VOLUME_WAG) - volume_total
    print("-" * 65)
    print("  FIN DU CHRONO DE CALCUL")
    print("-" * 65)
    print_results("d=3", "Offline V4.0 (GA Mémétique)", meilleur_nb_wagons, volume_perdu, temps_total)
