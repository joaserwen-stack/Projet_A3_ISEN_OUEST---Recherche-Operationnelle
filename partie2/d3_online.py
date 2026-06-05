import time
from utils import load_marchandises, print_results

def obtenir_rotations_valides(item, LONGUEUR_MAX, LARGEUR_MAX, HAUTEUR_MAX):
    """Génère et trie les 6 orientations physiques possibles (Flattest Z first)."""
    L, l, h = item['longueur'], item['largeur'], item['hauteur']
    toutes_les_rotations = [ # Toutes les permutations possibles des dimensions
        (L, l, h), (L, h, l), (l, L, h), 
        (l, h, L), (h, L, l), (h, l, L)
    ]
    rotations_valides = [] # Filtrage des rotations qui dépassent les dimensions du wagon
    for rx, ry, rz in toutes_les_rotations: # Vérification stricte des limites du wagon
        if rx <= LONGUEUR_MAX and ry <= LARGEUR_MAX and rz <= HAUTEUR_MAX: # Uniquement les rotations qui rentrent dans le wagon
            if (rx, ry, rz) not in rotations_valides:
                rotations_valides.append((rx, ry, rz))
    rotations_valides.sort(key=lambda x: (x[2], x[1], x[0]))
    return rotations_valides

# AABB 3D : Axis-Aligned Bounding Box pour la détection de collision rapide
def intersect_3d(b1, b2):
    """Détection de collision géométrique standard (AABB)."""
    return not (
        b1['x'] + b1['longueur'] <= b2['x'] or b2['x'] + b2['longueur'] <= b1['x'] or
        b1['y'] + b1['largeur'] <= b2['y'] or b2['y'] + b2['largeur'] <= b1['y'] or
        b1['z'] + b1['hauteur'] <= b2['z'] or b2['z'] + b2['hauteur'] <= b1['z']
    )

def true_online_3d_corner_points_speed(marchandises, LONGUEUR_MAX, LARGEUR_MAX, HAUTEUR_MAX):
    """
    Algorithme Online Corner-Points optimisé pour la scalabilité (Challenge Temps).
    Chaque wagon maintient son propre historique de points d'ancrage actifs.
    """
    # Chaque wagon est modélisé par un dictionnaire pour éviter la régénération des points
    wagons = [] 

    for item in marchandises:
        rotations = obtenir_rotations_valides(item, LONGUEUR_MAX, LARGEUR_MAX, HAUTEUR_MAX)
        if not rotations: 
            continue

        objet_place = False

        # Parcours des wagons ouverts (First-Fit)
        for wagon in wagons:
            # On extrait et trie la liste restreinte des points valides de ce wagon
            sorted_candidates = sorted(wagon['candidates'], key=lambda p: (p[2], p[1], p[0]))

            for cx, cy, cz in sorted_candidates:
                for long_obj, larg_obj, haut_obj in rotations:
                    
                    # Vérification des frontières du wagon
                    if cx + long_obj > LONGUEUR_MAX or cy + larg_obj > LARGEUR_MAX or cz + haut_obj > HAUTEUR_MAX:
                        continue

                    simulation = {'x': cx, 'y': cy, 'z': cz, 'longueur': long_obj, 'largeur': larg_obj, 'hauteur': haut_obj}

                    # Vérification des collisions uniquement avec les objets réels du wagon
                    collision = False
                    for obj in wagon['objets']:
                        if intersect_3d(simulation, obj):
                            collision = True
                            break

                    if not collision:
                        # Emplacement validé ! On crée l'objet
                        nouvel_obj = {
                            'id': item['id'], 'nom': item['nom'],
                            'x': cx, 'y': cy, 'z': cz,
                            'longueur': long_obj, 'largeur': larg_obj, 'hauteur': haut_obj
                        }
                        wagon['objets'].append(nouvel_obj)
                        
                        # 1. Le point utilisé est consommé, on le retire
                        wagon['candidates'].remove((cx, cy, cz))
                        
                        # 2. On génère les 3 nouveaux points d'appui potentiels si dans les clous
                        x_point, y_point, z_point = cx + long_obj, cy + larg_obj, cz + haut_obj
                        if x_point < LONGUEUR_MAX: wagon['candidates'].add((x_point, cy, cz))
                        if y_point < LARGEUR_MAX: wagon['candidates'].add((cx, y_point, cz))
                        if z_point < HAUTEUR_MAX: wagon['candidates'].add((cx, cy, z_point))
                        
                        # 3. Élagage Volumétrique : On supprime les points existants désormais "noyés" dans l'objet
                        points_morts = []
                        for px, py, pz in wagon['candidates']:
                            if cx <= px < cx + long_obj and cy <= py < cy + larg_obj and cz <= pz < cz + haut_obj:
                                points_morts.append((px, py, pz))
                        for pt in points_morts:
                            wagon['candidates'].remove(pt)

                        objet_place = True
                        break
                if objet_place: break
            if objet_place: break

        # Si aucun espace dans aucun wagon : Ouverture d'un nouveau wagon
        if not objet_place:
            long_obj, larg_obj, haut_obj = rotations[0]
            nouveau_wagon = {
                'objets': [{
                    'id': item['id'], 'nom': item['nom'],
                    'x': 0, 'y': 0, 'z': 0,
                    'longueur': long_obj, 'largeur': larg_obj, 'hauteur': haut_obj
                }],
                'candidates': set()
            }
            # Initialisation des points de départ du wagon vide autour du premier colis
            if long_obj < LONGUEUR_MAX: nouveau_wagon['candidates'].add((long_obj, 0, 0))
            if larg_obj < LARGEUR_MAX: nouveau_wagon['candidates'].add((0, larg_obj, 0))
            if haut_obj < HAUTEUR_MAX: nouveau_wagon['candidates'].add((0, 0, haut_obj))
            
            wagons.append(nouveau_wagon)

    # Extraction finale pour correspondre exactement au format attendu par print_results
    return [w['objets'] for w in wagons]

if __name__ == "__main__":
    print("\n--- Démarrage Bin Packing 3D (ON-LINE CHALLENGE-SPEED) ---")
    
    items = load_marchandises()
    
    if items:
        LONGUEUR_WAGON = 11.583 
        LARGEUR_WAGON = 2.294
        HAUTEUR_WAGON = 2.569
        
        start_time = time.time()
        resultat = true_online_3d_corner_points_speed(items, LONGUEUR_MAX=LONGUEUR_WAGON, LARGEUR_MAX=LARGEUR_WAGON, HAUTEUR_MAX=HAUTEUR_WAGON)
        temps_calcul = time.time() - start_time
        
        nb_wagons = len(resultat)
        volume_total_dispo = nb_wagons * (LONGUEUR_WAGON * LARGEUR_WAGON * HAUTEUR_WAGON)
        volume_objets = sum(obj['longueur'] * obj['largeur'] * obj['hauteur'] for obj in items)
        total_unused_volume = volume_total_dispo - volume_objets
        
        print_results(dimension_label="d=3", mode_label="Online Speed Corner-Points", nb_wagons=nb_wagons, total_unused=total_unused_volume, execution_time=temps_calcul)