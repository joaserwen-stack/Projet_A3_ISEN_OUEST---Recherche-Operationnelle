import time
import random
import math
from utils import load_marchandises, print_results

# ═══════════════════════════════════════════════════════════════════
# CONSTANTES ET CONFIGURATION
# ═══════════════════════════════════════════════════════════════════
L_WAG, l_WAG, H_WAG = 11.583, 2.294, 2.569  # Dimensions d'un wagon en mètres
VOL_WAG = L_WAG * l_WAG * H_WAG
TEMPS_MAX = 60
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
# PHASE 2 : ÉVALUATION GÉOMÉTRIQUE (MOTEUR EXACT V1.5)
# ═══════════════════════════════════════════════════════════════════
def evaluer_liste(ordre, dict_items, record_wagons_actuel):
    wagons = []

    for oid in ordre:
        item = dict_items[oid]
        place = False

        for w in wagons:
            for coin in sorted(w.coins, key=lambda c: (c[2], c[1], c[0])):
                cx, cy, cz = coin
                for rL, rl, rH in item.rotations:
                    if cx + rL <= L_WAG + 1e-4 and cy + rl <= l_WAG + 1e-4 and cz + rH <= H_WAG + 1e-4:
                        # AJOUT : On mémorise l'ID de l'objet (oid)
                        boite_cand = (cx, cy, cz, rL, rl, rH, oid)
                        if not w.intersecte(boite_cand):
                            w.boites.append(boite_cand)
                            w.coins.discard(coin)

                            for npt in [(cx + rL, cy, cz), (cx, cy + rl, cz), (cx, cy, cz + rH)]:
                                if npt[0] <= L_WAG and npt[1] <= l_WAG and npt[2] <= H_WAG:
                                    w.coins.add(npt)
                            place = True
                            break
                if place: break
            if place: break

        if not place:
            if len(wagons) + 1 > record_wagons_actuel:
                return float('inf'), float('inf'), []

            nw = Wagon()
            rL, rl, rH = item.rotations[0]
            # AJOUT : On mémorise l'ID ici aussi
            nw.boites.append((0.0, 0.0, 0.0, rL, rl, rH, oid))
            nw.coins = {(rL, 0.0, 0.0), (0.0, rl, 0.0), (0.0, 0.0, rH)}
            wagons.append(nw)

    nb_wagons = len(wagons)
    if nb_wagons == 0:
        return float('inf'), float('inf'), []

    vol_dernier_wagon = sum(b[3] * b[4] * b[5] for b in wagons[-1].boites)
    fitness = (nb_wagons - 1) + (vol_dernier_wagon / VOL_WAG)

    return nb_wagons, fitness, wagons

# ═══════════════════════════════════════════════════════════════════
# OPERATEURS GENETIQUES (IDENTIQUES V1.5)
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
    print("  D3 OFFLINE - ALGORITHME GÉNÉTIQUE V1.5 (ARCHI. POO)")
    print("=" * 65)

    marchandises = load_marchandises()
    if not marchandises:
        raise SystemExit("Erreur : Impossible de charger les données.")

    # Chargement en tant qu'objets "Marchandise"
    dict_items = {m['id']: Marchandise(m) for m in marchandises}
    ids = list(dict_items.keys())

    vol_total = sum(m['longueur'] * m['largeur'] * m['hauteur'] for m in marchandises)
    borne_inf = math.ceil(vol_total / VOL_WAG)
    print(f"Chargement : {len(marchandises)} marchandises chargées.")
    print(f"Volume total : {vol_total:.2f} m³ | Borne inférieure théorique : {borne_inf} wagons")

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
    meilleur_agencement_global = []

    while time.time() - t_debut < TEMPS_MAX:
        generation += 1

        # Phase 2 : Évaluation classique
        scores_pop = []
        for individu in population:
            nb_w, fitness, wagons_agencement = evaluer_liste(individu, dict_items, meilleur_nb_wagons)
            scores_pop.append((nb_w, fitness, individu, wagons_agencement))

        # Tri et recherche du meilleur
        scores_pop.sort(key=lambda x: x[1])
        gen_best_nb, gen_best_fit, _, gen_best_wagons = scores_pop[0]

        if gen_best_fit < meilleur_fitness:
            meilleur_nb_wagons = gen_best_nb
            meilleur_fitness = gen_best_fit
            meilleur_agencement_global = gen_best_wagons
            taux_dernier = (meilleur_fitness - (meilleur_nb_wagons - 1)) * 100
            print(f"[Gen {generation:03d}] NOUVEAU RECORD : {meilleur_nb_wagons} wagons (Dernier rempli à {taux_dernier:.1f}%) | Temps : {time.time() - t_debut:.2f}s")

            if meilleur_nb_wagons <= borne_inf:
                print(f"\n[STOP] Borne inférieure théorique absolue ({borne_inf}) atteinte !")
                break
        elif generation % 50 == 0:
            print(f"   [Gen {generation:03d}] Recherche en cours... (Temps : {time.time() - t_debut:.2f}s)")

        # Phase 3 : Évolution classique
        # Ajustement du unpacking pour gérer les 4 variables
        top_10 = [indiv for nb, fit, indiv, wag in scores_pop[:10]]

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
    
    # Correction de l'appel pour correspondre à ta fonction print_results
    print_results(dimension_label="d=3", mode_label="Offline V1.5 (POO Optimisée)", nb_wagons=meilleur_nb_wagons, total_unused=volume_perdu, execution_time=temps_total)

    print("\n" + "="*65)
    print(" 📦 EXTRACTION DES DONNÉES DU WAGON 1 POUR LA 3D")
    print("="*65)
    
    if meilleur_agencement_global:
        donnees_pour_graphique = []
        for boite in meilleur_agencement_global[0].boites:
            obj_format = {'id': boite[6], 'x': boite[0], 'y': boite[1], 'z': boite[2], 'longueur': boite[3], 'largeur': boite[4], 'hauteur': boite[5]}
            donnees_pour_graphique.append(obj_format)
        
        print("donnees_wagon_1 = [")
        for d in donnees_pour_graphique:
            print(f"    {d},")
        print("]")
    else:
        print("Erreur: Aucun agencement n'a pu être généré.")