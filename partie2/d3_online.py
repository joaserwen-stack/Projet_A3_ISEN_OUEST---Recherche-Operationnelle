import time
from utils import load_marchandises, print_results

def obtenir_rotations_valides(item, LONGUEUR_MAX, LARGEUR_MAX, HAUTEUR_MAX):
    """
    Génère les 6 orientations physiques possibles d'un objet.
    Trie les rotations pour privilégier la hauteur (Z) la plus faible.
    """
    L, l, h = item['longueur'], item['largeur'], item['hauteur']
    toutes_les_rotations = [
        (L, l, h), (L, h, l), (l, L, h),
        (l, h, L), (h, L, l), (h, l, L)
    ]
    rotations_valides = []
    for rx, ry, rz in toutes_les_rotations:
        if rx <= LONGUEUR_MAX and ry <= LARGEUR_MAX and rz <= HAUTEUR_MAX:
            if (rx, ry, rz) not in rotations_valides:
                rotations_valides.append((rx, ry, rz))
                
    # Tri par hauteur croissante (Z), puis largeur (Y), puis longueur (X)
    rotations_valides.sort(key=lambda x: (x[2], x[1], x[0]))
    return rotations_valides

def intersect_3d(b1, b2):
    """
    Détection de collision géométrique 3D entre deux boîtes (AABB).
    Renvoie True si les volumes se chevauchent.
    """
    return not (
        b1['x'] + b1['longueur'] <= b2['x'] or b2['x'] + b2['longueur'] <= b1['x'] or
        b1['y'] + b1['largeur'] <= b2['y'] or b2['y'] + b2['largeur'] <= b1['y'] or
        b1['z'] + b1['hauteur'] <= b2['z'] or b2['z'] + b2['hauteur'] <= b1['z']
    )

def true_online_3d_corner_points_speed(marchandises, LONGUEUR_MAX, LARGEUR_MAX, HAUTEUR_MAX):
    """
    Algorithme Heuristique Online par Points d'Ancrage (Corner-Points).
    Optimisé avec des structures de données de type SET pour le challenge de vitesse.
    """
    wagons = [] # Contient les wagons, chaque wagon est une liste d'objets placés

    for item in marchandises:
        rotations = obtenir_rotations_valides(item, LONGUEUR_MAX, LARGEUR_MAX, HAUTEUR_MAX)
        if not rotations:
            continue

        objet_place = False

        # Parcours des wagons existants (First-Fit)
        for wagon in wagons:
            # OPTIMISATION FLASH : Utilisation d'un set pour éliminer les coordonnées doublons
            candidates = {(0, 0, 0)}
            
            for obj in wagon:
                x_point = obj['x'] + obj['longueur']
                y_point = obj['y'] + obj['largeur']
                z_point = obj['z'] + obj['hauteur']
                
                # Filtrage à la naissance : on n'ajoute le point que s'il est dans les murs du wagon
                if x_point < LONGUEUR_MAX: candidates.add((x_point, obj['y'], obj['z']))
                if y_point < LARGEUR_MAX: candidates.add((obj['x'], y_point, obj['z']))
                if z_point < HAUTEUR_MAX: candidates.add((obj['x'], obj['y'], z_point))

            # Tri des points uniques pour remplir du bas vers le haut, du fond vers l'avant
            sorted_candidates = sorted(candidates, key=lambda p: (p[2], p[1], p[0]))

            # Test des emplacements disponibles
            for cx, cy, cz in sorted_candidates:
                for long_obj, larg_obj, haut_obj in rotations:
                    
                    # Vérification des limites physiques du wagon
                    if cx + long_obj > LONGUEUR_MAX or cy + larg_obj > LARGEUR_MAX or cz + haut_obj > HAUTEUR_MAX:
                        continue

                    simulation = {'x': cx, 'y': cy, 'z': cz, 'longueur': long_obj, 'largeur': larg_obj, 'hauteur': haut_obj}

                    # Vérification des collisions avec les objets déjà présents
                    collision = False
                    for obj in wagon:
                        if intersect_3d(simulation, obj):
                            collision = True
                            break

                    # Si l'espace est libre, on valide immédiatement (First-Fit)
                    if not collision:
                        wagon.append({
                            'id': item['id'], 'nom': item['nom'],
                            'x': cx, 'y': cy, 'z': cz,
                            'longueur': long_obj, 'largeur': larg_obj, 'hauteur': haut_obj
                        })
                        objet_place = True
                        break
                if objet_place: break
            if objet_place: break

        # Si aucun wagon ouvert n'a pu accueillir l'objet, on ouvre un nouveau wagon
        if not objet_place:
            long_obj, larg_obj, haut_obj = rotations[0]
            wagons.append([{
                'id': item['id'], 'nom': item['nom'],
                'x': 0, 'y': 0, 'z': 0,
                'longueur': long_obj, 'largeur': larg_obj, 'hauteur': haut_obj
            }])

    return wagons

if __name__ == "__main__":
    print("\n--- Démarrage Bin Packing 3D (ON-LINE ULTRA-SPEED) ---")
    
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