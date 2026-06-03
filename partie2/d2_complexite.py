import time
import random
import copy
from utils import load_marchandises, print_results

# ==========================================
# 1. LE MOTEUR GÉOMÉTRIQUE (Les Lois de la Physique)
# ==========================================

def obtenir_rotations_valides(item, LONGUEUR_MAX, LARGEUR_MAX, HAUTEUR_MAX):
    L, l, h = item['longueur'], item['largeur'], item['hauteur']
    toutes_les_rotations = [(L, l, h), (L, h, l), (l, L, h), (l, h, L), (h, L, l), (h, l, L)]
    rotations_valides = []
    for rx, ry, rz in toutes_les_rotations:
        if rx <= LONGUEUR_MAX and ry <= LARGEUR_MAX and rz <= HAUTEUR_MAX:
            if (rx, ry, rz) not in rotations_valides:
                rotations_valides.append((rx, ry, rz))
    rotations_valides.sort(key=lambda x: (x[2], x[1], x[0]))
    return rotations_valides

def intersect_3d(b1, b2):
    return not (
        b1['x'] + b1['longueur'] <= b2['x'] or b2['x'] + b2['longueur'] <= b1['x'] or
        b1['y'] + b1['largeur'] <= b2['y'] or b2['y'] + b2['largeur'] <= b1['y'] or
        b1['z'] + b1['hauteur'] <= b2['z'] or b2['z'] + b2['hauteur'] <= b1['z']
    )

def evaluer_sequence(sequence_marchandises, LONGUEUR_MAX, LARGEUR_MAX, HAUTEUR_MAX):
    """
    Simule le remplissage pour UNE séquence précise.
    C'est ton moteur Corner-Points exact, utilisé ici comme "Juge" de l'évolution.
    """
    wagons = []
    for item in sequence_marchandises:
        rotations = obtenir_rotations_valides(item, LONGUEUR_MAX, LARGEUR_MAX, HAUTEUR_MAX)
        if not rotations: continue
        objet_place = False

        for wagon in wagons:
            sorted_candidates = sorted(wagon['candidates'], key=lambda p: (p[2], p[1], p[0]))
            for cx, cy, cz in sorted_candidates:
                for long_obj, larg_obj, haut_obj in rotations:
                    if cx + long_obj > LONGUEUR_MAX or cy + larg_obj > LARGEUR_MAX or cz + haut_obj > HAUTEUR_MAX:
                        continue
                    simulation = {'x': cx, 'y': cy, 'z': cz, 'longueur': long_obj, 'largeur': larg_obj, 'hauteur': haut_obj}
                    
                    collision = any(intersect_3d(simulation, obj) for obj in wagon['objets'])
                    if not collision:
                        wagon['objets'].append({
                            'id': item['id'], 'nom': item['nom'],
                            'x': cx, 'y': cy, 'z': cz,
                            'longueur': long_obj, 'largeur': larg_obj, 'hauteur': haut_obj
                        })
                        wagon['candidates'].remove((cx, cy, cz))
                        x_point, y_point, z_point = cx + long_obj, cy + larg_obj, cz + haut_obj
                        if x_point < LONGUEUR_MAX: wagon['candidates'].add((x_point, cy, cz))
                        if y_point < LARGEUR_MAX: wagon['candidates'].add((cx, y_point, cz))
                        if z_point < HAUTEUR_MAX: wagon['candidates'].add((cx, cy, z_point))
                        
                        points_morts = [pt for pt in wagon['candidates'] if cx <= pt[0] < cx + long_obj and cy <= pt[1] < cy + larg_obj and cz <= pt[2] < cz + haut_obj]
                        for pt in points_morts: wagon['candidates'].remove(pt)
                        objet_place = True
                        break
                if objet_place: break
            if objet_place: break

        if not objet_place:
            long_obj, larg_obj, haut_obj = rotations[0]
            nouveau_wagon = {
                'objets': [{'id': item['id'], 'nom': item['nom'], 'x': 0, 'y': 0, 'z': 0, 'longueur': long_obj, 'largeur': larg_obj, 'hauteur': haut_obj}],
                'candidates': set()
            }
            if long_obj < LONGUEUR_MAX: nouveau_wagon['candidates'].add((long_obj, 0, 0))
            if larg_obj < LARGEUR_MAX: nouveau_wagon['candidates'].add((0, larg_obj, 0))
            if haut_obj < HAUTEUR_MAX: nouveau_wagon['candidates'].add((0, 0, haut_obj))
            wagons.append(nouveau_wagon)

    return wagons

# ==========================================
# 2. L'ALGORITHME GÉNÉTIQUE (La théorie de l'évolution)
# ==========================================

def croisement_ordre(parent1, parent2):
    """Croisement de type OX (Order Crossover) pour ne pas dupliquer ou oublier d'objets."""
    taille = len(parent1)
    debut, fin = sorted(random.sample(range(taille), 2))
    
    # L'enfant prend une portion centrale du parent 1
    enfant = [None] * taille
    enfant[debut:fin] = parent1[debut:fin]
    
    # On remplit le reste avec l'ordre du parent 2
    ids_presents = {item['id'] for item in enfant[debut:fin]}
    pointeur_enfant = fin
    for item in parent2:
        if item['id'] not in ids_presents:
            if pointeur_enfant == taille: pointeur_enfant = 0
            enfant[pointeur_enfant] = item
            pointeur_enfant += 1
    return enfant

def mutation(individu, taux_mutation=0.1):
    """Échange la position de deux objets au hasard."""
    if random.random() < taux_mutation:
        idx1, idx2 = random.sample(range(len(individu)), 2)
        individu[idx1], individu[idx2] = individu[idx2], individu[idx1]
    return individu

def hybrid_offline_genetic(marchandises, LONGUEUR_MAX, LARGEUR_MAX, HAUTEUR_MAX, taille_pop=20, nb_generations=15):
    """Le cerveau global : gère l'évolution des séquences de rangement."""
    print(f"🌍 Création de la population initiale ({taille_pop} individus)...")
    
    # 1. On crée une population de départ (Des listes de colis triées au hasard)
    # On injecte quand même un individu trié par volume décroissant pour aider l'algorithme !
    population = []
    individu_tri_volume = sorted(marchandises, key=lambda x: x['longueur'] * x['largeur'] * x['hauteur'], reverse=True)
    population.append(individu_tri_volume)
    
    for _ in range(taille_pop - 1):
        ind = list(marchandises)
        random.shuffle(ind)
        population.append(ind)

    meilleur_score_global = float('inf')
    meilleure_solution_globale = None

    for gen in range(nb_generations):
        # 2. Évaluation (Le jugement de Darwin)
        scores = []
        for individu in population:
            resultat_wagons = evaluer_sequence(individu, LONGUEUR_MAX, LARGEUR_MAX, HAUTEUR_MAX)
            nb_wagons = len(resultat_wagons)
            # La Fitness = On cherche le moins de wagons possible.
            # S'il y a égalité, on regarde l'espace vide du dernier wagon pour affiner.
            espace_vide_dernier = (LONGUEUR_MAX * LARGEUR_MAX * HAUTEUR_MAX) - sum(obj['longueur']*obj['largeur']*obj['hauteur'] for obj in resultat_wagons[-1]['objets'])
            score = nb_wagons + (espace_vide_dernier / 1000) # Formule d'ajustement
            scores.append((score, resultat_wagons, individu))

        # Tri par les meilleurs scores (les plus petits)
        scores.sort(key=lambda x: x[0])
        
        meilleur_score_actuel = scores[0][0]
        nb_wagons_actuel = len(scores[0][1])
        
        print(f"🧬 Génération {gen+1}/{nb_generations} | Meilleur actuel : {nb_wagons_actuel} wagons")

        if meilleur_score_actuel < meilleur_score_global:
            meilleur_score_global = meilleur_score_actuel
            meilleure_solution_globale = scores[0][1]

        # 3. Sélection & Reproduction (On garde les 5 meilleurs pour faire des enfants)
        elite = [s[2] for s in scores[:5]]
        nouvelle_population = elite.copy() # On garde les meilleurs tels quels (Élitisme)

        # On croise les meilleurs entre eux pour remplir la population
        while len(nouvelle_population) < taille_pop:
            parent1, parent2 = random.sample(elite, 2)
            enfant = croisement_ordre(parent1, parent2)
            enfant = mutation(enfant, taux_mutation=0.2)
            nouvelle_population.append(enfant)

        population = nouvelle_population

    return [w['objets'] for w in meilleure_solution_globale]

if __name__ == "__main__":
    print("\n" + "="*60)
    print(" 🧠 Démarrage Bin Packing 3D (OFFLINE - ALGO GÉNÉTIQUE)")
    print("="*60)
    
    items = load_marchandises()
    
    if items:
        LONGUEUR_WAGON = 11.583 
        LARGEUR_WAGON = 2.294
        HAUTEUR_WAGON = 2.569
        
        start_time = time.time()
        # On limite volontairement à 20 individus sur 15 générations pour que ton PC ne crashe pas
        resultat = hybrid_offline_genetic(items, LONGUEUR_MAX=LONGUEUR_WAGON, LARGEUR_MAX=LARGEUR_WAGON, HAUTEUR_MAX=HAUTEUR_WAGON, taille_pop=20, nb_generations=15)
        temps_calcul = time.time() - start_time
        
        nb_wagons = len(resultat)
        volume_total_dispo = nb_wagons * (LONGUEUR_WAGON * LARGEUR_WAGON * HAUTEUR_WAGON)
        volume_objets = sum(obj['longueur'] * obj['largeur'] * obj['hauteur'] for obj in items)
        total_unused_volume = volume_total_dispo - volume_objets
        
        print("\n" + "="*60 + "\n 🏆 RÉSULTAT DE L'ÉVOLUTION\n" + "="*60)
        print_results(dimension_label="d=3", mode_label="Offline (Genetic + Corner-Points)", nb_wagons=nb_wagons, total_unused=total_unused_volume, execution_time=temps_calcul)