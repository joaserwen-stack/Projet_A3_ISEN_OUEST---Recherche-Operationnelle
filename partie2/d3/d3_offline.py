import os
import time
import random
import math
from multiprocessing import Pool, cpu_count
from utils import load_marchandises, print_results

# =====================================================================
# Écrit par : Thomas
# =====================================================================

# --- CONSTANTES GÉOMÉTRIQUES DU PROBLÈME ---
# Dimensions réglementaires du wagon SNCF données dans l'énoncé
L_WAG, l_WAG, H_WAG = 11.583, 2.294, 2.569
VOL_WAG = L_WAG * l_WAG * H_WAG

# --- HYPERPARAMÈTRES DE L'ALGORITHME GÉNÉTIQUE ---
TEMPS_MAX = 300          # Timeout de sécurité fixé à 5 minutes (300 secondes)
TAILLE_POPULATION = 64   # Nombre d'individus (chromosomes) dans la population
N_ELITE = 16             # Conservation stricte des 16 meilleurs individus (élitisme)
N_IMMIGRANTS = 4         # Injection de sang neuf à chaque génération pour éviter les minima locaux
PROB_MUTATION = 0.60     # Forte probabilité de mutation pour maintenir la diversité génétique


class Marchandise:
    """
    Représente un objet à charger. Gère le calcul des différentes rotations 3D 
    admissibles en fonction des restrictions physiques de l'objet.
    """
    __slots__ = ['id', 'rotations']

    def __init__(self, data: dict):
        self.id = data['id']
        L, l, H = data['longueur'], data['largeur'], data['hauteur']

        # Si l'objet n'est pas retournable (ex: tête en haut obligatoire), 
        # on ne s'autorise que les rotations sur le plan horizontal (pivot Z)
        if data.get('retournable', 1) == 0:
            rot = [(L, l, H), (l, L, H)]
        else:
            # Sinon, génération des 6 orientations spatiales possibles en 3D
            rot = [(L, l, H), (L, H, l), (l, L, H), (l, H, L), (H, L, l), (H, l, L)]

        # Tri par hauteur croissante (r[2]) : astuce pour favoriser la stabilité 
        # en plaçant les objets avec un centre de gravité bas en priorité
        self.rotations = sorted(set(rot), key=lambda r: r[2])


class Wagon:
    """
    Modélise l'espace intérieur d'un wagon. Reçoit les boîtes intégrées, 
    gère l'intersection géométrique et calcule la surface de support.
    """
    __slots__ = ['boites', 'coins', 'vol_used']

    def __init__(self):
        self.boites: list[tuple] = []          # Boîtes placées : (x, y, z, L, l, H)
        self.coins: set[tuple] = {(0.0, 0.0, 0.0)}  # Liste des points d'ancrage libres (Points Extremums)
        self.vol_used: float = 0.0              # Cumul du volume des objets présents

    def intersecte(self, b1: tuple) -> bool:
        """
        Détection de collision 3D par chevauchement AABB (Axis-Aligned Bounding Boxes).
        Ajout d'une tolérance de 1e-4 pour éviter les faux positifs dus aux flottants.
        chaque ligne vérifie s'il y a un recouvrement sur les axes X, Y et Z simultanément.
        """
        for b2 in self.boites:
            if (b1[0] < b2[0] + b2[3] - 1e-4 and b1[0] + b1[3] > b2[0] + 1e-4 and
                    b1[1] < b2[1] + b2[4] - 1e-4 and b1[1] + b1[4] > b2[1] + 1e-4 and
                    b1[2] < b2[2] + b2[5] - 1e-4 and b1[2] + b1[5] > b2[2] + 1e-4):
                return True
        return False

    def est_supportee(self, xmin: float, xmax: float, ymin: float, ymax: float,
                      zmin: float, seuil: float = 0.70) -> bool:
        """
        Vérification de la gravité/stabilité : une boîte posée en hauteur (zmin > 0) 
        doit obligatoirement reposer sur le toit d'autres boîtes sur au moins 'seuil' % de sa base.
        """
        if zmin <= 1e-4:  # Posé directement sur le plancher du wagon -> Toujours stable
            return True

        aire_base = (xmax - xmin) * (ymax - ymin) # Aire totale sous la boîte courante
        aire_support = 0.0

        # On parcourt les boîtes déjà placées pour voir si leur sommet touche le bas de notre boîte
        for b_xmin, b_ymin, b_zmin, b_L, b_l, b_H in self.boites:
            # Vérification de coïncidence sur l'axe Z (sommet de b2 == base de b1)
            if abs(b_zmin + b_H - zmin) <= 1e-4:
                # Calcul de la zone d'intersection (recouvrement X/Y) entre les deux bases
                ix_min = max(xmin, b_xmin)
                ix_max = min(xmax, b_xmin + b_L)
                iy_min = max(ymin, b_ymin)
                iy_max = min(ymax, b_ymin + b_l)

                # Si l'intersection existe en 2D, on ajoute sa surface à l'aire de support cumulée
                if ix_max > ix_min and iy_max > iy_min:
                    aire_support += (ix_max - ix_min) * (iy_max - iy_min)

        # True si le pourcentage de surface en contact direct est supérieur ou égal au seuil demandé
        return (aire_support / aire_base) >= seuil


# --- MULTIPROCESSING GLOBALS ---
# Les workers de la Pool ont besoin d'accéder à la structure de données 
# sans que celle-ci ne soit sérialisée (pickled) à chaque appel de fonction.
_pool_dict_items = None


def _init_pool(di: dict) -> None:
    # Initialisation globale de la base d'objets sur chaque cœur CPU esclave
    global _pool_dict_items
    _pool_dict_items = di


def _eval_wrapper(args: tuple) -> tuple:
    # Unpack simple des arguments pour la map parallèle de multiprocessing
    individu, record = args
    return evaluer_liste(individu, _pool_dict_items, record)


# --- LOGIQUE CRITIQUE DE PLACEMENT INDIVIDUEL (COEUR DE L'ALGORITHME) ---

def evaluer_liste(ordre: list, dict_items: dict, record_wagons_actuel: int) -> tuple:
    """
    Prend une permutation d'IDs d'objets et simule son colisage physique (Packing).
    Implémente un algorithme glouton perfectionné reposant sur le concept des 'Coins' (Corners).
    """
    wagons: list[Wagon] = [] # Liste dynamique des wagons ouverts pour cet individu

    # Parcours séquentiel des objets dans l'ordre défini par le chromosome du GA
    for oid in ordre:
        item = dict_items[oid]
        best = None  # Stocke le meilleur emplacement trouvé pour cet objet particulier : (espace_restant, wagon_id, coin, rotation)

        # Essai d'insertion dans les wagons déjà ouverts (First Fit / Best Fit hybride)
        for wi, w in enumerate(wagons):
            placed = False
            # Tri topologique des coins par Z (hauteur), puis X, puis Y pour combler les trous du bas d'abord
            for coin in sorted(w.coins, key=lambda c: (c[2], c[0], c[1])):
                if placed:
                    break
                cx, cy, cz = coin
                # Test de toutes les rotations valides pour l'objet courant
                for rL, rl, rH in item.rotations:
                    # 1. Vérification stricte des limites géométriques du conteneur/wagon
                    if cx + rL <= L_WAG + 1e-4 and cy + rl <= l_WAG + 1e-4 and cz + rH <= H_WAG + 1e-4:
                        # 2. Vérification d'absence de chevauchement/collision avec les objets du wagon
                        if not w.intersecte((cx, cy, cz, rL, rl, rH)):
                            # 3. Vérification de la stabilité (la boîte doit tenir physiquement sans tomber)
                            if w.est_supportee(cx, cx + rL, cy, cy + rl, cz):
                                # Calcul du volume libre restant après placement (critère Best Fit)
                                remaining = VOL_WAG - w.vol_used - rL * rl * rH
                                # Si c'est le premier point valide ou si ce point optimise mieux l'espace
                                if best is None or remaining < best[0]:
                                    best = (remaining, wi, coin, (rL, rl, rH))
                                placed = True # Sortie du parcours des rotations pour ce coin précis
                                break

        # Si un emplacement valide a été trouvé parmi tous les wagons existants
        if best is not None:
            _, wi, coin, (rL, rl, rH) = best
            w = wagons[wi]
            cx, cy, cz = coin
            # Enregistrement définitif de la boîte dans le wagon choisi
            w.boites.append((cx, cy, cz, rL, rl, rH))
            w.vol_used += rL * rl * rH
            w.coins.discard(coin)  # Le point d'ancrage est consommé et disparait

            # Génération de 3 nouveaux "Points Extremums" (coins) créés sur les faces de la boîte ajoutée
            for npt in [(cx + rL, cy, cz), (cx, cy + rl, cz), (cx, cy, cz + rH)]:
                # On ne conserve le coin que s'il est à l'intérieur du volume utile du wagon
                if npt[0] <= L_WAG and npt[1] <= l_WAG and npt[2] <= H_WAG:
                    w.coins.add(npt)
        else:
            # ÉLAGAGE STRATÉGIQUE (Pruning) : Si l'ouverture d'un nouveau wagon nous fait dépasser 
            # le record absolu actuel, l'individu est inutile. On avorte directement l'évaluation.
            # Gain de temps machine colossal sur les grosses populations.
            if len(wagons) + 1 > record_wagons_actuel:
                return float('inf'), float('inf')

            # Pas de place nulle part : on ouvre un tout nouveau wagon de fret
            nw = Wagon()
            # Sélection de la première rotation de l'objet compatible avec les dimensions brutes du wagon
            chosen = next(
                ((rL, rl, rH) for rL, rl, rH in item.rotations
                 if rL <= L_WAG + 1e-4 and rl <= l_WAG + 1e-4 and rH <= H_WAG + 1e-4),
                item.rotations[0]
            )
            rL, rl, rH = chosen
            # Initialisation de la première boîte à l'origine (0,0,0) du nouveau wagon
            nw.boites.append((0.0, 0.0, 0.0, rL, rl, rH))
            nw.vol_used = rL * rl * rH
            # Génération des trois premiers coins du nouveau wagon le long des arêtes de la première boîte
            nw.coins = {(rL, 0.0, 0.0), (0.0, rl, 0.0), (0.0, 0.0, rH)}
            wagons.append(nw)

    if not wagons:
        return float('inf'), float('inf')

    nb_wagons = len(wagons)

    # CALCUL DE LA FITNESS COMPOSITE :
    # Sert à guider finement l'algorithme génétique. Si deux séquences utilisent par exemple 12 wagons,
    # on va préférer celle qui remplit le plus le 12ème wagon (donc laissant le maximum de vide pour les autres).
    # Formule : (Nombre de wagons - 1) + (Ratio de volume occupé dans le dernier wagon)
    fitness = (nb_wagons - 1) + (wagons[-1].vol_used / VOL_WAG)
    return nb_wagons, fitness


# --- FONCTION DE RECONSTRUCTION POUR LA VISUALISATION ---

def extraire_wagons(ordre: list, dict_items: dict) -> list[list[tuple]]:
    """
    Copie conforme exacte de la logique d'évaluation 'evaluer_liste'.
    Cependant, elle n'applique pas d'élagage (pas d'infini) et embarque l'ID réel des objets (oid).
    Elle sert uniquement en fin de script pour générer la structure exploitable par le script 3D.
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
            # On conserve la trace de l'ID de la marchandise (oid) à la fin du tuple
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


# --- OPÉRATEURS GÉNÉTIQUES ---

def croisement_ox(p1: list, p2: list) -> list:
    """
    Croisement d'ordre (Order Crossover - OX).
    Parfait pour les permutations d'identifiants uniques car il empêche les doublons.
    Mécanique :
      1. Sélectionne deux points de coupe aléatoires 'a' et 'b' sur le parent 1.
      2. Copie brute du segment central [a:b] du parent 1 dans l'enfant.
      3. Remplit les cases vides restantes en parcourant circulairement le parent 2 à partir 
         de la position 'b+1', en ignorant les éléments déjà copiés pour préserver l'unicité.
    """
    n = len(p1)
    a, b = sorted(random.sample(range(n), 2)) # Choix de la zone de transmission directe
    enfant = [None] * n
    enfant[a:b+1] = p1[a:b+1] # Recopie directe
    pris = set(enfant[a:b+1])  # Set de hachage pour des lookups O(1) rapides lors du remplissage

    pos = (b + 1) % n # Position d'écriture de départ dans l'enfant
    for i in range(n):
        curr = p2[(b + 1 + i) % n] # Lecture circulaire du parent 2
        if curr not in pris:
            enfant[pos] = curr
            pos = (pos + 1) % n # Déplacement circulaire de l'index d'écriture
    return enfant


def mutation(ordre: list, prob: float = PROB_MUTATION) -> list:
    """
    Introduit du désordre mutationnel (diversité) pour sortir des optima locaux.
    Si le tirage aléatoire valide la mutation, l'algorithme lance un dé (0 à 3) 
    pour appliquer l'un des 4 opérateurs de remaniement de liste disponibles.
    """
    if random.random() >= prob:
        return ordre # Pas de mutation

    op = random.randint(0, 3)
    if op == 0:  # SWAP : Permutation pure et simple de deux objets n'importe où dans la liste
        i, j = random.sample(range(len(ordre)), 2)
        ordre[i], ordre[j] = ordre[j], ordre[i]

    elif op == 1:  # INSERTION : Extraction d'un objet et réinjection à un autre index au hasard
        i = random.randrange(len(ordre))
        item = ordre.pop(i)
        ordre.insert(random.randrange(len(ordre) + 1), item)

    elif op == 2:  # 2-OPT (Inversion) : Retournement complet d'un sous-segment (ordre inverse)
        i, j = sorted(random.sample(range(len(ordre)), 2))
        ordre[i:j+1] = ordre[i:j+1][::-1]

    else:  # SCRAMBLE (Mélange) : Sélection d'une sous-section de la liste et brassage aléatoire complet
        i, j = sorted(random.sample(range(len(ordre)), 2))
        segment = ordre[i:j+1]
        random.shuffle(segment)
        ordre[i:j+1] = segment

    return ordre


# --- GESTION DU CYCLE DE VIE DES INDIVIDUS ---

def _individu_aleatoire(ids: list) -> list:
    # Génère une configuration d'ordre de chargement 100% aléatoire
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
        """
        Stratégie d'initialisation déterministe (Mode Offline).
        Puisque nous avons le droit de trier les marchandises avant de charger (Offline),
        on pré-calcule 4 solutions basées sur des tris éprouvés. Cela donne d'excellentes
        bases à la population au lieu de commencer uniquement avec du hasard total.
        """
        def seed_par(key_fn):
            # Fonction utilitaire de tri descendant basé sur une caractéristique géométrique de la première rotation
            return sorted(self.ids, key=lambda i: key_fn(self.dict_items[i].rotations[0]), reverse=True)
        return [
            seed_par(lambda r: r[0] * r[1] * r[2]),  # Seed 1 : Tri par Volume décroissant (Heuristique la plus robuste en 3D)
            seed_par(lambda r: r[2]),                  # Seed 2 : Tri par Hauteur décroissante
            seed_par(lambda r: r[0] * r[1]),           # Seed 3 : Tri par Surface au sol décroissante
            seed_par(lambda r: r[0]),                  # Seed 4 : Tri par Longueur décroissante
        ]

    def initialiser(self) -> None:
        """Prépare la population de départ en mélangeant les heuristiques injectées (seeds) et l'aléatoire."""
        seeds = self._creer_seeds()

        print("Pré-calcul des heuristiques initiales...")
        # Évaluation immédiate des solutions de tri déterministes pour fixer les premiers records
        for idx, seed in enumerate(seeds):
            nb_w, fit = evaluer_liste(seed, self.dict_items, self.meilleur_nb_wagons)
            if fit < self.meilleur_fitness:
                self.meilleur_nb_wagons = nb_w
                self.meilleur_fitness = fit
                self.meilleur_individu = seed[:]
                taux = (fit - (nb_w - 1)) * 100
                print(f"[Init] Seed {idx+1} validée → {nb_w} wagons (Dernier rempli à {taux:.1f}%)")

        self.population = seeds[:]
        # On comble le reste des slots disponibles de la population avec des individus aléatoires
        while len(self.population) < TAILLE_POPULATION:
            self.population.append(_individu_aleatoire(self.ids))

        n_aleatoires = TAILLE_POPULATION - len(seeds)
        print(f"Population prête : {len(seeds)} seeds + {n_aleatoires} aléatoires.")

    def _evaluer(self, pool: Pool) -> list[tuple]:
        """
        Étape d'évaluation parallèle.
        Distribue le calcul lourd des packings géométriques sur tous les cœurs logiques 
        disponibles du processeur en utilisant la Pool de processus de multiprocessing.
        """
        # On passe le record actuel à battre pour permettre le "pruning" à l'intérieur d'évaluer_liste
        args = [(indiv, self.meilleur_nb_wagons) for indiv in self.population]
        resultats = pool.map(_eval_wrapper, args)

        # Association des scores récoltés avec l'identité génétique de chaque chromosome
        scores = [(nb_w, fit, indiv) for (nb_w, fit), indiv in zip(resultats, self.population)]
        # Tri ascendant des scores : les meilleures fitness (les plus petites valeurs) se retrouvent en premier
        scores.sort(key=lambda x: x[1])
        return scores

    def _evoluer(self, scores: list[tuple]) -> None:
        """
        Transition générationnelle (Sélection, Croisement, Mutation, Immigration).
        Garantit la survie des gènes forts tout en entretenant l'exploration.
        """
        # ÉLITISME : Préservation absolue des 'N_ELITE' meilleurs individus sans altération
        elite = [indiv for _, _, indiv in scores[:N_ELITE]]
        n_enfants = TAILLE_POPULATION - N_ELITE - N_IMMIGRANTS

        # REPRODUCTION : Croisement des individus d'élite pour générer la descendance
        enfants = []
        while len(enfants) < n_enfants:
            p1, p2 = random.sample(elite, 2) # Sélection aléatoire de deux parents élites
            # Croisement OX puis tentative immédiate de mutation avant stockage
            enfants.append(mutation(croisement_ox(p1, p2)))

        # IMMIGRATION : Injection de sang neuf (individus aléatoires complets).
        # Essentiel pour casser la stagnation génétique (perte de diversité au sein de l'élite).
        immigrants = [_individu_aleatoire(self.ids) for _ in range(N_IMMIGRANTS)]

        # Constitution finale de la population de la génération montante
        self.population = elite + enfants + immigrants

    def run(self, pool: Pool, borne_inf: int) -> float:
        """Boucle itérative maîtresse du GA. Tourne jusqu'au timeout ou à la perfection physique."""
        t_debut = time.time()

        while time.time() - t_debut < TEMPS_MAX:
            self.generation += 1
            scores = self._evaluer(pool) # Évaluation parallèle multi-cœurs
            gen_best_nb, gen_best_fit, gen_best_indiv = scores[0] # Récupération de la tête de liste après tri

            # Si le champion de la génération actuelle surpasse le record historique de l'algorithme
            if gen_best_fit < self.meilleur_fitness:
                self.meilleur_nb_wagons = gen_best_nb
                self.meilleur_fitness = gen_best_fit
                self.meilleur_individu = gen_best_indiv[:]
                taux = (self.meilleur_fitness - (self.meilleur_nb_wagons - 1)) * 100
                elapsed = time.time() - t_debut
                print(f"[Gen {self.generation:03d}] NOUVEAU RECORD : {self.meilleur_nb_wagons} wagons "
                      f"(Dernier rempli à {taux:.1f}%) | Temps : {elapsed:.2f}s")

                # CONDITION D'ARRÊT OPTIMALE : Si le nombre de wagons égale la borne inférieure mathématique,
                # on a prouvé l'optimalité absolue de notre agencement. Inutile de continuer à chercher !
                if self.meilleur_nb_wagons <= borne_inf:
                    print(f"\n[STOP] Borne inférieure théorique absolue ({borne_inf}) atteinte !")
                    break
            elif self.generation % 50 == 0:
                # Log d'activité périodique pour s'assurer que le script ne s'est pas bloqué
                elapsed = time.time() - t_debut
                print(f"   [Gen {self.generation:03d}] Recherche en cours... (Temps : {elapsed:.2f}s)")

            # Mutation et brassage pour la génération d'après
            self._evoluer(scores)

        return time.time() - t_debut


# --- SCRIPT DE CONFIGURATION ET EXÉCUTION ---

if __name__ == "__main__":
    print("=" * 65)
    print("  D3 OFFLINE - ALGORITHME GÉNÉTIQUE V6.0 (Retour aux bases)")
    print("=" * 65)

    # Récupération de la base SQLite ou du JSON via la fonction partagée du projet
    marchandises = load_marchandises()
    if not marchandises:
        raise SystemExit("Erreur : Impossible de charger les données.")

    # Instanciation du dictionnaire d'objets métiers optimisés (__slots__)
    dict_items = {m['id']: Marchandise(m) for m in marchandises}
    ids = list(dict_items.keys())

    # Détermination de la Borne Inférieure Théorique Absolue (Relaxation continue du Bin Packing) :
    # Somme des volumes de toutes les marchandises divisée par le volume utile maximum d'un wagon SNCF.
    # On applique un 'ceil' car on ne peut pas fractionner un wagon.
    vol_total = sum(m['longueur'] * m['largeur'] * m['hauteur'] for m in marchandises)
    borne_inf = math.ceil(vol_total / VOL_WAG)
    n_workers = cpu_count() # Récupération automatique du nombre de cœurs logiques (threads) de la machine

    print(f"Chargement : {len(marchandises)} marchandises chargées.")
    print(f"Volume total : {vol_total:.2f} m³ | Borne inférieure théorique : {borne_inf} wagons")
    print(f"Parallélisation : {n_workers} workers")
    print("-" * 65)

    # Initialisation de la structure GA et pré-calcul des structures de tri
    ga = AlgorithmeGenetique(dict_items, ids)
    ga.initialiser()

    print("-" * 65)
    # Lancement de la boucle d'optimisation avec gestion de la Pool de processus
    with Pool(processes=n_workers, initializer=_init_pool, initargs=(dict_items,)) as pool:
        temps_total = ga.run(pool, borne_inf)

    print("-" * 65)
    print("  FIN DU CHRONO DE CALCUL")
    print("-" * 65)

    # Calcul analytique final de la perte d'espace totale (Volume perdu cumulé)
    volume_perdu = (ga.meilleur_nb_wagons * VOL_WAG) - vol_total
    print_results("d=3", "Offline V6.0", ga.meilleur_nb_wagons, volume_perdu, temps_total)

    # RECONSTRUCTION ET EXPORTATION GÉOMÉTRIQUE :
    # Ré-exécution de l'ordre gagnant pour récupérer les triplets de coordonnées exacts (X, Y, Z)
    print("\nExtraction du contenu des wagons...")
    wagons_boites = extraire_wagons(ga.meilleur_individu, dict_items)
    print(f"{len(wagons_boites)} wagons extraits.")

    # Tentative de génération des fichiers visuels de rendu pour la soutenance orale
    try:
        from d3_visualisation import visualiser_wagons
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rendus")
        os.makedirs(output_dir, exist_ok=True)
        visualiser_wagons(wagons_boites, output_dir=output_dir)
        print(f"Images sauvegardées dans : {output_dir}")
    except ImportError:
        print("d3_visualisation non disponible — visualisation ignorée.")