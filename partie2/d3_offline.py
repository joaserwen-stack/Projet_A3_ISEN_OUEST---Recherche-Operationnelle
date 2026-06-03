import time
import math
import random
from utils import load_marchandises, print_results

# ═══════════════════════════════════════════════════════════════════
#   Bin-Packing 3D Offline — AG ultra-amélioré (mémétique) + B&B
#
#   Pipeline :
#     1. GA   — chromosome = (ordre des objets, orientation par objet)
#     2. Deep-Fit — décodeur géométrique : coins candidats + contact
#     3. Mémétique — recherche locale inter-wagons sur les élites
#     4. B&B  — post-optimisation : tente d'éliminer le plus petit wagon
# ═══════════════════════════════════════════════════════════════════

# --- Dimensions d'un wagon (en mètres) ---
LONGUEUR_WAGON = 11.583
LARGEUR_WAGON  = 2.294
HAUTEUR_WAGON  = 2.569
VOLUME_WAGON   = LONGUEUR_WAGON * LARGEUR_WAGON * HAUTEUR_WAGON  # ≈ 68.26 m³

EPS = 1e-9  # tolérance flottante

# --- Paramètres GA ---
TAILLE_POPULATION    = 30
NB_ELITES            = 5
TEMPS_MAX            = 60      # budget total en secondes (borne la boucle)
TOURNOI_K            = 3
MUT_BASE             = 0.35    # taux mutation de base (adaptatif au-dessus)
TAUX_OX              = 0.85    # probabilité de croisement
STAGNATION_MAX       = 8       # générations sans gain avant injection/restart

# --- Paramètres Deep-Fit ---
MAX_POINTS_CANDIDATS = 300

# --- Paramètres B&B ---
BB_TIMEOUT           = 3       # secondes par appel B&B


# ═══════════════════════════════════════════════════════════════════
#   ORIENTATIONS — respect strict de la contrainte `retournable`
# ═══════════════════════════════════════════════════════════════════

def calculer_orientations(objet):
    """
    Retourne la liste des orientations (l, w, h) valides d'un objet.

    retournable == 1 : rotation libre → 6 permutations de (l, w, h).
    retournable == 0 : la hauteur reste verticale (interdit de coucher
                       l'objet) ; seul le pivot à plat est permis →
                       2 orientations (l, w, h) et (w, l, h).
    Les doublons (dimensions égales) sont supprimés en conservant l'ordre.
    """
    l, w, h = objet['longueur'], objet['largeur'], objet['hauteur']
    if objet.get('retournable', 1) == 0:
        candidats = [(l, w, h), (w, l, h)]
    else:
        candidats = [(l, w, h), (l, h, w), (w, l, h),
                     (w, h, l), (h, l, w), (h, w, l)]
    vues, uniques = set(), []
    for o in candidats:
        if o not in vues:
            vues.add(o)
            uniques.append(o)
    return uniques


# ═══════════════════════════════════════════════════════════════════
#   DEEP-FIT — HELPERS GÉOMÉTRIQUES
#   Par wagon : boites = list[(x,y,z,l,w,h)], points = list[(x,y,z)]
# ═══════════════════════════════════════════════════════════════════

def chevauchement(px, py, pz, l, w, h, ox, oy, oz, ol, ow, oh):
    """True si les deux boîtes s'intersectent strictement (avec EPS)."""
    return (px < ox + ol - EPS and px + l > ox + EPS and
            py < oy + ow - EPS and py + w > oy + EPS and
            pz < oz + oh - EPS and pz + h > oz + EPS)


def placement_valide(px, py, pz, l, w, h, boites):
    """Objet (px,py,pz,l,w,h) dans le wagon ET sans chevauchement."""
    if (px + l > LONGUEUR_WAGON + EPS or
            py + w > LARGEUR_WAGON + EPS or
            pz + h > HAUTEUR_WAGON + EPS or
            px < -EPS or py < -EPS or pz < -EPS):
        return False
    for (ox, oy, oz, ol, ow, oh) in boites:
        if chevauchement(px, py, pz, l, w, h, ox, oy, oz, ol, ow, oh):
            return False
    return True


def calculer_surface_contact(px, py, pz, l, w, h, boites):
    """
    Surface de contact de l'objet avec les 6 parois du wagon et les faces
    adjacentes des boîtes voisines. Score haut = emboîtement dense.
    """
    contact = 0.0
    # Parois du wagon
    if abs(px) < EPS:                          contact += w * h
    if abs(px + l - LONGUEUR_WAGON) < EPS:     contact += w * h
    if abs(py) < EPS:                          contact += l * h
    if abs(py + w - LARGEUR_WAGON) < EPS:      contact += l * h
    if abs(pz) < EPS:                          contact += l * w
    if abs(pz + h - HAUTEUR_WAGON) < EPS:      contact += l * w
    # Faces adjacentes des boîtes placées
    for (ox, oy, oz, ol, ow, oh) in boites:
        if abs(px - (ox + ol)) < EPS or abs(px + l - ox) < EPS:
            dy = min(py + w, oy + ow) - max(py, oy)
            dz = min(pz + h, oz + oh) - max(pz, oz)
            if dy > EPS and dz > EPS: contact += dy * dz
        if abs(py - (oy + ow)) < EPS or abs(py + w - oy) < EPS:
            dx = min(px + l, ox + ol) - max(px, ox)
            dz = min(pz + h, oz + oh) - max(pz, oz)
            if dx > EPS and dz > EPS: contact += dx * dz
        if abs(pz - (oz + oh)) < EPS or abs(pz + h - oz) < EPS:
            dx = min(px + l, ox + ol) - max(px, ox)
            dy = min(py + w, oy + ow) - max(py, oy)
            if dx > EPS and dy > EPS: contact += dx * dy
    return contact


def purger_points(points, boites):
    """
    Supprime les points strictement internes à une boîte, déduplique,
    trie (z, y, x) croissant, plafonne à MAX_POINTS_CANDIDATS.
    """
    valides = []
    vus = set()
    for (px, py, pz) in points:
        cle = (round(px, 6), round(py, 6), round(pz, 6))
        if cle in vus:
            continue
        dedans = False
        for (ox, oy, oz, ol, ow, oh) in boites:
            if (ox + EPS < px < ox + ol - EPS and
                    oy + EPS < py < oy + ow - EPS and
                    oz + EPS < pz < oz + oh - EPS):
                dedans = True
                break
        if not dedans:
            vus.add(cle)
            valides.append((px, py, pz))
    valides.sort(key=lambda p: (p[2], p[1], p[0]))
    return valides[:MAX_POINTS_CANDIDATS]


# ═══════════════════════════════════════════════════════════════════
#   DÉCODEUR DEEP-FIT + FITNESS
# ═══════════════════════════════════════════════════════════════════

def placer_objets(ordre, orient, dictionnaire_objets, orientations_cache):
    """
    Décode un chromosome (ordre, orient) en placement réel via Deep-Fit.

    Le gène d'orientation est autoritaire : pour chaque objet, on essaie
    d'abord l'orientation orient[id] (meilleur point = contact max). On ne
    se rabat sur les autres orientations valides que si l'orientation du
    gène ne rentre nulle part.

    Retour : (wagons_result, wagons_points, wagons_boites)
        wagons_result : list[list[dict]]            (objets placés)
        wagons_points : list[list[(x,y,z)]]
        wagons_boites : list[list[(x,y,z,l,w,h)]]
    """
    wagons_result, wagons_points, wagons_boites = [], [], []

    for oid in ordre:
        objet = dictionnaire_objets[oid]
        oris = orientations_cache[oid]
        if not oris:
            continue  # objet non plaçable (aucune orientation) → ignoré

        # Ordre d'essai : gène d'abord, puis les autres en repli
        gene = orient.get(oid, 0) % len(oris)
        ordre_oris = [oris[gene]] + [oris[k] for k in range(len(oris)) if k != gene]

        meilleur = None
        for (l, w, h) in ordre_oris:
            meilleur_score = -1.0
            for idx in range(len(wagons_result)):
                for (px, py, pz) in wagons_points[idx]:
                    if placement_valide(px, py, pz, l, w, h, wagons_boites[idx]):
                        score = calculer_surface_contact(px, py, pz, l, w, h, wagons_boites[idx])
                        if score > meilleur_score:
                            meilleur_score = score
                            meilleur = (idx, px, py, pz, l, w, h)
            if meilleur is not None:
                break  # orientation du gène (ou 1er repli) a réussi

        if meilleur is not None:
            idx, px, py, pz, l, w, h = meilleur
            wagons_result[idx].append({'id': oid, 'nom': objet['nom'],
                'x': px, 'y': py, 'z': pz, 'longueur': l, 'largeur': w, 'hauteur': h})
            wagons_boites[idx].append((px, py, pz, l, w, h))
            wagons_points[idx].extend([(px+l, py, pz), (px, py+w, pz), (px, py, pz+h)])
            wagons_points[idx] = purger_points(wagons_points[idx], wagons_boites[idx])
        else:
            # Nouveau wagon : gène si elle rentre, sinon meilleure ori au coin
            faisables = [o for o in ordre_oris
                         if placement_valide(0, 0, 0, o[0], o[1], o[2], [])]
            if not faisables:
                continue  # ne rentre dans aucun wagon vide → ignoré
            l, w, h = max(faisables,
                key=lambda o: calculer_surface_contact(0, 0, 0, o[0], o[1], o[2], []))
            boite0 = [(0.0, 0.0, 0.0, l, w, h)]
            pts0 = purger_points([(l, 0.0, 0.0), (0.0, w, 0.0), (0.0, 0.0, h)], boite0)
            wagons_result.append([{'id': oid, 'nom': objet['nom'],
                'x': 0.0, 'y': 0.0, 'z': 0.0, 'longueur': l, 'largeur': w, 'hauteur': h}])
            wagons_boites.append(boite0)
            wagons_points.append(pts0)

    return wagons_result, wagons_points, wagons_boites


def meilleur_placement(chromosome, dictionnaire_objets, orientations_cache):
    """Décode un chromosome et retourne (nb_wagons, result, points, boites)."""
    ordre, orient = chromosome
    r, p, b = placer_objets(ordre, orient, dictionnaire_objets, orientations_cache)
    return len(r), r, p, b


def volume_wagon_objets(wagon):
    """Volume total des objets d'un wagon (list[dict])."""
    return sum(o['longueur'] * o['largeur'] * o['hauteur'] for o in wagon)


def fitness(chromosome, dictionnaire_objets, orientations_cache):
    """
    fitness = nb_wagons + (1 - remplissage du plus petit wagon).
    Plus BAS = meilleur. À nb_wagons égal, favorise un plus petit wagon
    presque vide (proche d'une élimination → -1 wagon).
    """
    ordre, orient = chromosome
    r, _, _ = placer_objets(ordre, orient, dictionnaire_objets, orientations_cache)
    if not r:
        return float('inf')
    vol_min = min(volume_wagon_objets(w) for w in r)
    return len(r) + (1.0 - vol_min / VOLUME_WAGON)


# ═══════════════════════════════════════════════════════════════════
#   OPÉRATEURS GÉNÉTIQUES
# ═══════════════════════════════════════════════════════════════════

def _orientation_couchee(oris):
    """Index de l'orientation à hauteur minimale (plus grande face au sol)."""
    return min(range(len(oris)), key=lambda k: oris[k][2])


def initialiser_population(ids, orientations_cache, dictionnaire_objets=None, taille=TAILLE_POPULATION):
    """
    Population mixte : seeds heuristiques (tris) + permutations aléatoires.
    orient des seeds = orientation couchée ; orient aléatoire sinon.
    dictionnaire_objets requis pour les tris ; si None, seeds = ordre brut.
    """
    population = []

    def orient_couche():
        return {i: _orientation_couchee(orientations_cache[i]) for i in ids}

    # Seeds heuristiques
    if dictionnaire_objets is not None:
        d = dictionnaire_objets
        cles = [
            lambda i: d[i]['longueur'] * d[i]['largeur'] * d[i]['hauteur'],  # volume
            lambda i: d[i]['longueur'],                                       # longueur
            lambda i: d[i]['hauteur'],                                        # hauteur
            lambda i: d[i]['longueur'] * d[i]['largeur'],                     # surface base
            lambda i: max(d[i]['longueur'], d[i]['largeur'], d[i]['hauteur']),# max dim
        ]
        for cle in cles:
            ordre = sorted(ids, key=cle, reverse=True)
            population.append((ordre, orient_couche()))

    # Compléter avec de l'aléatoire
    while len(population) < taille:
        ordre = ids[:]
        random.shuffle(ordre)
        orient = {i: random.randrange(len(orientations_cache[i])) for i in ids}
        population.append((ordre, orient))

    return population[:taille]


def croisement_ox(parent1, parent2):
    """Order Crossover (OX) : enfant = segment de p1 + reste dans l'ordre de p2."""
    n = len(parent1)
    a, b = sorted(random.sample(range(n), 2))
    enfant = [None] * n
    enfant[a:b+1] = parent1[a:b+1]
    pris = set(parent1[a:b+1])
    pos = (b + 1) % n
    for k in range(n):
        gene = parent2[(b + 1 + k) % n]
        if gene not in pris:
            enfant[pos] = gene
            pos = (pos + 1) % n
    return enfant


def croisement_orient(orient1, orient2, orientations_cache):
    """Croisement uniforme du vecteur d'orientation (clé = id)."""
    enfant = {}
    for i in orient1:
        choix = orient1[i] if random.random() < 0.5 else orient2[i]
        enfant[i] = choix % len(orientations_cache[i])
    return enfant


def mutation_ordre(ordre):
    """Mutation in-place : swap ou inversion d'un segment (50/50)."""
    n = len(ordre)
    if n < 2:
        return
    a, b = sorted(random.sample(range(n), 2))
    if random.random() < 0.5:
        ordre[a], ordre[b] = ordre[b], ordre[a]
    else:
        ordre[a:b+1] = reversed(ordre[a:b+1])


def mutation_orientation(orient, orientations_cache):
    """Change l'orientation d'un objet tiré au hasard (si plusieurs possibles)."""
    candidats = [i for i in orient if len(orientations_cache[i]) > 1]
    if not candidats:
        return
    i = random.choice(candidats)
    orient[i] = random.randrange(len(orientations_cache[i]))


# ═══════════════════════════════════════════════════════════════════
#   RECHERCHE LOCALE MÉMÉTIQUE + MUTATION DIRIGÉE
# ═══════════════════════════════════════════════════════════════════

def recherche_locale(wagons_result, wagons_points, wagons_boites,
                     orientations_cache, deadline=None):
    """
    Tente de vider le plus petit wagon en déplaçant ses objets vers les
    autres wagons (toute orientation valide × tout point candidat).
    Si le wagon cible est vidé, il est supprimé (-1 wagon). Répète tant
    qu'une amélioration a lieu. Retour : (result, points, boites) éventuellement réduits.
    """
    result = [w[:] for w in wagons_result]
    points = [p[:] for p in wagons_points]
    boites = [b[:] for b in wagons_boites]

    amelioration = True
    while amelioration and len(result) > 1:
        if deadline is not None and time.time() > deadline:
            break
        amelioration = False
        idx_cible = min(range(len(result)), key=lambda i: volume_wagon_objets(result[i]))
        # objets du wagon cible, volume croissant (petits d'abord = plus faciles à recaser)
        objets_cible = sorted(result[idx_cible],
                              key=lambda o: o['longueur']*o['largeur']*o['hauteur'])
        deplaces = []
        for obj in objets_cible:
            oris = orientations_cache[obj['id']]
            place = False
            # wagons destinataires triés par remplissage décroissant
            dests = sorted([i for i in range(len(result)) if i != idx_cible],
                           key=lambda i: volume_wagon_objets(result[i]), reverse=True)
            for w_idx in dests:
                for (l, w, h) in oris:
                    for (px, py, pz) in points[w_idx]:
                        if placement_valide(px, py, pz, l, w, h, boites[w_idx]):
                            result[w_idx].append({'id':obj['id'],'nom':obj['nom'],
                                'x':px,'y':py,'z':pz,'longueur':l,'largeur':w,'hauteur':h})
                            boites[w_idx].append((px,py,pz,l,w,h))
                            points[w_idx].extend([(px+l,py,pz),(px,py+w,pz),(px,py,pz+h)])
                            points[w_idx] = purger_points(points[w_idx], boites[w_idx])
                            deplaces.append(obj['id'])
                            place = True
                            break
                    if place: break
                if place: break
        # Si tout le wagon cible a été recasé → le supprimer
        if len(deplaces) == len(result[idx_cible]):
            del result[idx_cible]; del points[idx_cible]; del boites[idx_cible]
            amelioration = True
        # sinon : rollback en repartant des structures d'origine de ce tour
        elif deplaces:
            result = [w[:] for w in wagons_result]
            points = [p[:] for p in wagons_points]
            boites = [b[:] for b in wagons_boites]
            break

    return result, points, boites


def mutation_wagon_cible(ordre, wagons_result):
    """
    Mutation dirigée : remonte les objets du wagon le moins rempli en tête
    de l'ordre (ils seront placés en premier au prochain décodage → plus de
    chances d'être absorbés ailleurs). Retourne un nouvel ordre (permutation).
    """
    if not wagons_result:
        return ordre[:]
    idx = min(range(len(wagons_result)), key=lambda i: volume_wagon_objets(wagons_result[i]))
    ids_cible = [o['id'] for o in wagons_result[idx]]
    tete = [i for i in ordre if i in ids_cible]
    reste = [i for i in ordre if i not in ids_cible]
    return tete + reste


# ═══════════════════════════════════════════════════════════════════
#   B&B POST-OPTIMISATION — ÉLIMINATION DU PLUS PETIT WAGON
# ═══════════════════════════════════════════════════════════════════

def bb_post_optimisation(wagons_result, wagons_points, wagons_boites,
                         orientations_cache, borne_inferieure):
    """
    Tente d'éliminer le wagon de volume minimal en redistribuant ses objets
    dans les N-1 wagons restants via un Branch & Bound récursif.
    Élagages : (1) volume résiduel < volume restant → coupe ;
               (2) timeout BB_TIMEOUT.
    Objets triés volume desc (gros = contraignants d'abord).
    Retour : (result, points, boites) à N-1 wagons, ou None si échec.
    """
    N = len(wagons_result)
    if N <= borne_inferieure or N < 2:
        return None

    volumes = [volume_wagon_objets(w) for w in wagons_result]
    idx_cible = min(range(N), key=lambda i: volumes[i])

    objets_queue = sorted(wagons_result[idx_cible],
        key=lambda o: o['longueur']*o['largeur']*o['hauteur'], reverse=True)

    r_result = [wagons_result[i][:] for i in range(N) if i != idx_cible]
    r_points = [wagons_points[i][:] for i in range(N) if i != idx_cible]
    r_boites = [wagons_boites[i][:] for i in range(N) if i != idx_cible]

    t0 = time.time()

    def vol_residuel_total():
        return sum(VOLUME_WAGON - sum(b[3]*b[4]*b[5] for b in r_boites[i])
                   for i in range(len(r_boites)))

    def bb(k):
        if k == len(objets_queue):
            return True
        vol_restant = sum(objets_queue[i]['longueur']*objets_queue[i]['largeur']*objets_queue[i]['hauteur']
                          for i in range(k, len(objets_queue)))
        if vol_residuel_total() < vol_restant - EPS:
            return False
        if time.time() - t0 > BB_TIMEOUT:
            return False
        objet = objets_queue[k]
        oris = orientations_cache[objet['id']]
        for w_idx in range(len(r_result)):
            for (px, py, pz) in r_points[w_idx]:
                for (l, w, h) in oris:
                    if placement_valide(px, py, pz, l, w, h, r_boites[w_idx]):
                        old_r = r_result[w_idx][:]
                        old_p = r_points[w_idx][:]
                        old_b = r_boites[w_idx][:]
                        r_result[w_idx].append({'id':objet['id'],'nom':objet['nom'],
                            'x':px,'y':py,'z':pz,'longueur':l,'largeur':w,'hauteur':h})
                        r_boites[w_idx].append((px,py,pz,l,w,h))
                        r_points[w_idx].extend([(px+l,py,pz),(px,py+w,pz),(px,py,pz+h)])
                        r_points[w_idx] = purger_points(r_points[w_idx], r_boites[w_idx])
                        if bb(k+1):
                            return True
                        r_result[w_idx] = old_r
                        r_points[w_idx] = old_p
                        r_boites[w_idx] = old_b
        return False

    if bb(0):
        return r_result, r_points, r_boites
    return None


# ═══════════════════════════════════════════════════════════════════
#   VALIDATION GÉOMÉTRIQUE STRICTE
# ═══════════════════════════════════════════════════════════════════

def valider_solution(wagons_result, dictionnaire_objets):
    """
    Vérifie qu'une solution est physiquement valide. Retourne (ok, message).
      - tous les objets placés exactement une fois
      - aucun débordement de wagon
      - aucun chevauchement intra-wagon
      - orientation légale : objet non-retournable garde sa hauteur d'origine
    """
    ids_places = []
    for wagon in wagons_result:
        for o in wagon:
            ids_places.append(o['id'])
            # bornes
            if (o['x'] + o['longueur'] > LONGUEUR_WAGON + EPS or
                    o['y'] + o['largeur'] > LARGEUR_WAGON + EPS or
                    o['z'] + o['hauteur'] > HAUTEUR_WAGON + EPS or
                    o['x'] < -EPS or o['y'] < -EPS or o['z'] < -EPS):
                return False, f"objet {o['id']} déborde du wagon"
            # contrainte retournable
            ref = dictionnaire_objets[o['id']]
            if ref.get('retournable', 1) == 0 and abs(o['hauteur'] - ref['hauteur']) > EPS:
                return False, f"objet {o['id']} non-retournable mais hauteur modifiée"
        # chevauchements
        for i in range(len(wagon)):
            a = wagon[i]
            ba = (a['x'],a['y'],a['z'],a['longueur'],a['largeur'],a['hauteur'])
            for j in range(i+1, len(wagon)):
                b = wagon[j]
                bb_ = (b['x'],b['y'],b['z'],b['longueur'],b['largeur'],b['hauteur'])
                if chevauchement(*ba, *bb_):
                    return False, f"chevauchement objets {a['id']} et {b['id']}"

    attendus = set(dictionnaire_objets.keys())
    obtenus = set(ids_places)
    if len(ids_places) != len(obtenus):
        return False, "objet placé en double"
    if obtenus != attendus:
        manquants = attendus - obtenus
        return False, f"objets manquants : {sorted(manquants)}"
    return True, "OK"


if __name__ == "__main__":
    print("=" * 65)
    print("  D3 OFFLINE — AG ultra-amélioré (mémétique) + B&B")
    print("=" * 65)

    objets = load_marchandises()
    print(f"Objets chargés : {len(objets)}")
    if not objets:
        raise SystemExit("Aucun objet à charger.")

    ids = [o['id'] for o in objets]
    dictionnaire_objets = {o['id']: o for o in objets}
    orientations_cache = {o['id']: calculer_orientations(o) for o in objets}

    # Borne inférieure théorique (volume)
    vol_total = sum(o['longueur']*o['largeur']*o['hauteur'] for o in objets)
    borne_inferieure = math.ceil(vol_total / VOLUME_WAGON)
    print(f"Borne inférieure théorique : {borne_inferieure} wagons "
          f"(volume {vol_total:.1f} m³)")

    t_debut = time.time()
    deadline = t_debut + TEMPS_MAX

    population = initialiser_population(ids, orientations_cache, dictionnaire_objets,
                                        taille=TAILLE_POPULATION)

    meilleur_nb = float('inf')
    meilleur_result = None
    meilleur_points = None
    meilleur_boites = None
    sans_amelioration = 0
    gen = 0

    while time.time() < deadline:
        gen += 1
        # Évaluer
        scored = []
        for indiv in population:
            scored.append((fitness(indiv, dictionnaire_objets, orientations_cache), indiv))
            if time.time() >= deadline:
                break
        scored.sort(key=lambda x: x[0])

        # Mise à jour du meilleur global (décodage complet du top)
        nb, r, p, b = meilleur_placement(scored[0][1], dictionnaire_objets, orientations_cache)

        # Mémétique sur le meilleur (budget temps borné)
        r, p, b = recherche_locale(r, p, b, orientations_cache, deadline=min(deadline, time.time()+1.0))
        nb = len(r)

        if nb < meilleur_nb:
            meilleur_nb = nb
            meilleur_result = r
            meilleur_points = p
            meilleur_boites = b
            sans_amelioration = 0
            print(f"  [Gen {gen:03d}] nouveau meilleur : {nb} wagons")
            # B&B post-opt sur le record
            out = bb_post_optimisation(r, p, b, orientations_cache, borne_inferieure)
            if out is not None and len(out[0]) < meilleur_nb:
                meilleur_nb = len(out[0])
                meilleur_result = out[0]
                meilleur_points = out[1]
                meilleur_boites = out[2]
                print(f"  [B&B] réduit à {meilleur_nb} wagons")
        else:
            sans_amelioration += 1

        if meilleur_nb <= borne_inferieure:
            print("  Borne inférieure atteinte — arrêt.")
            break

        # Taux de mutation adaptatif : monte si diversité basse
        fitness_distinctes = len({round(s, 4) for s, _ in scored})
        diversite = fitness_distinctes / max(1, len(scored))
        taux_mut = min(0.9, MUT_BASE + (1.0 - diversite) * 0.5)

        # Nouvelle génération
        nouvelle = [scored[i][1] for i in range(min(NB_ELITES, len(scored)))]

        # Stagnation → injection d'aléatoire (diversification)
        if sans_amelioration >= STAGNATION_MAX:
            sans_amelioration = 0
            for _ in range(TAILLE_POPULATION // 4):
                ordre = ids[:]; random.shuffle(ordre)
                orient = {i: random.randrange(len(orientations_cache[i])) for i in ids}
                nouvelle.append((ordre, orient))

        while len(nouvelle) < TAILLE_POPULATION:
            # Sélection par tournoi
            p1 = min(random.sample(scored, min(TOURNOI_K, len(scored))), key=lambda x: x[0])[1]
            p2 = min(random.sample(scored, min(TOURNOI_K, len(scored))), key=lambda x: x[0])[1]

            if random.random() < TAUX_OX:
                enfant_ordre = croisement_ox(p1[0], p2[0])
            else:
                enfant_ordre = p1[0][:]
            enfant_orient = croisement_orient(p1[1], p2[1], orientations_cache)

            # Mutations
            if random.random() < taux_mut:
                mutation_ordre(enfant_ordre)
            if random.random() < taux_mut:
                mutation_orientation(enfant_orient, orientations_cache)
            # Mutation dirigée wagon-cible (occasionnelle, basée sur le meilleur courant)
            if meilleur_result is not None and random.random() < 0.15:
                enfant_ordre = mutation_wagon_cible(enfant_ordre, meilleur_result)

            nouvelle.append((enfant_ordre, enfant_orient))

        population = nouvelle

    temps_total = time.time() - t_debut

    # --- Validation stricte ---
    ok, msg = valider_solution(meilleur_result, dictionnaire_objets)
    print(f"\nValidation géométrique : {'OK' if ok else 'ÉCHEC — ' + msg}")
    if not ok:
        raise SystemExit("Solution invalide — investiguer avant de présenter.")

    # --- Métriques ---
    volume_dispo = meilleur_nb * VOLUME_WAGON
    volume_perdu = volume_dispo - vol_total
    print_results("d=3", "Offline (AG mémétique + B&B)",
                  meilleur_nb, volume_perdu, temps_total)
    print(f"  Borne inférieure : {borne_inferieure} wagons | "
          f"taux occupation : {vol_total/volume_dispo*100:.1f}% | générations : {gen}")

    print("\nAperçu des 3 premiers wagons :")
    for i in range(min(3, meilleur_nb)):
        print(f"\n--- WAGON {i+1} ({len(meilleur_result[i])} objets) ---")
        for o in meilleur_result[i]:
            print(f"  - [{o['nom']}] X:{o['x']:.2f} Y:{o['y']:.2f} Z:{o['z']:.2f} "
                  f"({o['longueur']}×{o['largeur']}×{o['hauteur']})")
