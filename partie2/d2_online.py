import time
from utils import load_marchandises, print_results

def first_fit_2d_shelf(marchandises, LONGUEUR_MAX, LARGEUR_MAX):
    wagons = []           # Liste qui contiendra tous nos wagons remplis
    wagon_actuel = []     # Le wagon qu'on est en train de remplir sur le plancher
    
    # Coordonnées du "curseur" sur le plancher du wagon (X = longueur, Y = largeur)
    current_x = 0
    current_y = 0
    largeur_rangee_actuelle = 0
    
    for item in marchandises:
        long_obj = item['longueur']  
        larg_obj = item['largeur']   
        
        # Sécurité : Si l'objet est plus grand que le plancher du wagon, on l'ignore
        if long_obj > LONGUEUR_MAX or larg_obj > LARGEUR_MAX:
            print(f"⚠️ Objet {item['id']} impossible à ranger !")
            continue
            
        # Est-ce qu'on déborde sur la longueur du wagon ? Si oui, on crée une nouvelle rangée.
        if current_x + long_obj > LONGUEUR_MAX:
            current_x = 0                                  # On repart au début de la longueur
            current_y += largeur_rangee_actuelle           # On décale sur la largeur pour la nouvelle rangée
            largeur_rangee_actuelle = 0                    # On remet la largeur de la nouvelle rangée à zéro
            
        # Est-ce qu'on déborde sur la largeur du wagon ? Si oui, le wagon est plein.
        if current_y + larg_obj > LARGEUR_MAX:
            wagons.append(wagon_actuel)                    # On sauvegarde le wagon plein
            wagon_actuel = []                              # On prend un wagon neuf
            current_x = 0
            current_y = 0
            largeur_rangee_actuelle = 0
            
        # C'est bon, on pose l'objet sur le plancher à la position (x, y) !
        objet_place = {
            'id': item['id'],
            'nom': item['nom'],
            'x': current_x,
            'y': current_y,
            'longueur': long_obj,
            'largeur': larg_obj
        }
        wagon_actuel.append(objet_place)
        
        # On décale le curseur sur la longueur pour le prochain objet
        current_x += long_obj
        
        # On met à jour la largeur de la rangée si ce nouvel objet est le plus large
        if larg_obj > largeur_rangee_actuelle:
            largeur_rangee_actuelle = larg_obj
            
    # À la fin, on ajoute le tout dernier wagon (s'il n'est pas vide)
    if wagon_actuel:
        wagons.append(wagon_actuel)
        
    return wagons

if __name__ == "__main__":
    print("\n--- Démarrage Bin Packing 2D (Online First-Fit Shelf) ---")
    
    items = load_marchandises()
    print(f"Nombre de marchandises chargées depuis le CSV : {len(items)}")
    
    if items:
        # Dimensions du plancher du wagon (comme demandé par la prof)
        LONGUEUR_WAGON = 11.583 
        LARGEUR_WAGON = 2.294   
        
        start_time = time.time()
        resultat = first_fit_2d_shelf(items, LONGUEUR_MAX=LONGUEUR_WAGON, LARGEUR_MAX=LARGEUR_WAGON)
        temps_calcul = time.time() - start_time
        
        nb_wagons = len(resultat)
        
        # Mathématiques de surface
        surface_totale_dispo = nb_wagons * (LONGUEUR_WAGON * LARGEUR_WAGON)
        surface_objets = sum(obj['longueur'] * obj['largeur'] for obj in items)
        total_unused_area = surface_totale_dispo - surface_objets
        
        print_results(dimension_label="d=2", mode_label="Online First-fit Shelf", nb_wagons=nb_wagons, total_unused=total_unused_area, execution_time=temps_calcul)
        
        print("Détails du remplissage des premiers wagons (Vue de dessus) :")
        for i in range(min(5, nb_wagons)):
            print(f"\n--- WAGON {i+1} ---")
            for obj in resultat[i]:
                print(f"  - [{obj['nom']}] placé en X:{obj['x']:.2f}, Y:{obj['y']:.2f} (Taille: {obj['longueur']}x{obj['largeur']})")