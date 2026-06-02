import time
from utils import load_marchandises, print_results

def first_fit_3d_level(marchandises, LONGUEUR_MAX, LARGEUR_MAX, HAUTEUR_MAX):
    wagons = []           
    wagon_actuel = []     
    
    # Coordonnées du curseur en 3 dimensions (X, Y, Z)
    current_x = 0  # Position sur la longueur
    current_y = 0  # Position sur la largeur (profondeur)
    current_z = 0  # Position sur la hauteur (étage)
    
    # Traceurs pour savoir de combien on doit décaler quand on crée une rangée ou un niveau
    largeur_rangee_actuelle = 0
    hauteur_niveau_actuel = 0
    
    for item in marchandises:
        long_obj = item['longueur']  
        larg_obj = item['largeur']   
        haut_obj = item['hauteur']
        
        # Sécurité : Si un objet est physiquement plus grand que le wagon vide, on le jette
        if long_obj > LONGUEUR_MAX or larg_obj > LARGEUR_MAX or haut_obj > HAUTEUR_MAX:
            print(f"⚠️ Objet {item['id']} impossible à ranger !")
            continue
            
        # 1. Débordement en LONGUEUR ? -> On crée une nouvelle rangée (On recule en Y)
        if current_x + long_obj > LONGUEUR_MAX:
            current_x = 0                                  
            current_y += largeur_rangee_actuelle           
            largeur_rangee_actuelle = 0                    
            
        # 2. Débordement en LARGEUR ? -> On a fini le plancher, on monte d'un étage (On monte en Z)
        if current_y + larg_obj > LARGEUR_MAX:
            current_x = 0
            current_y = 0
            current_z += hauteur_niveau_actuel
            largeur_rangee_actuelle = 0
            hauteur_niveau_actuel = 0
            
        # 3. Débordement en HAUTEUR ? -> On touche le plafond, le wagon est plein !
        if current_z + haut_obj > HAUTEUR_MAX:
            wagons.append(wagon_actuel)                    
            wagon_actuel = []                              
            current_x = 0
            current_y = 0
            current_z = 0
            largeur_rangee_actuelle = 0
            hauteur_niveau_actuel = 0
            
        # C'est bon, on pose l'objet en 3D !
        objet_place = {
            'id': item['id'],
            'nom': item['nom'],
            'x': current_x,
            'y': current_y,
            'z': current_z,  # On ajoute la coordonnée Z !
            'longueur': long_obj,
            'largeur': larg_obj,
            'hauteur': haut_obj
        }
        wagon_actuel.append(objet_place)
        
        # On décale le curseur sur la longueur pour le prochain objet
        current_x += long_obj
        
        # On met à jour les traceurs (le plus large de la rangée, et le plus haut du niveau)
        if larg_obj > largeur_rangee_actuelle:
            largeur_rangee_actuelle = larg_obj
        if haut_obj > hauteur_niveau_actuel:
            hauteur_niveau_actuel = haut_obj
            
    # On n'oublie pas de sauvegarder le tout dernier wagon
    if wagon_actuel:
        wagons.append(wagon_actuel)
        
    return wagons

if __name__ == "__main__":
    print("\n--- Démarrage Bin Packing 3D (Online First-Fit Level) ---")
    
    items = load_marchandises()
    
    if items:
        # Les vraies constantes physiques du wagon en 3D
        LONGUEUR_WAGON = 11.583 
        LARGEUR_WAGON = 2.294
        HAUTEUR_WAGON = 2.569
        
        start_time = time.time()
        resultat = first_fit_3d_level(items, LONGUEUR_MAX=LONGUEUR_WAGON, LARGEUR_MAX=LARGEUR_WAGON, HAUTEUR_MAX=HAUTEUR_WAGON)
        temps_calcul = time.time() - start_time
        
        nb_wagons = len(resultat)
        
        # Mathématiques de VOLUME (en m3)
        volume_total_dispo = nb_wagons * (LONGUEUR_WAGON * LARGEUR_WAGON * HAUTEUR_WAGON)
        volume_objets = sum(obj['longueur'] * obj['largeur'] * obj['hauteur'] for obj in items)
        total_unused_volume = volume_total_dispo - volume_objets
        
        print_results(dimension_label="d=3", mode_label="Online First-fit Level", nb_wagons=nb_wagons, total_unused=total_unused_volume, execution_time=temps_calcul)
        
        print("\nDétails du remplissage 3D :")
        for i in range(min(3, nb_wagons)):
            print(f"\n--- WAGON {i+1} ---")
            for obj in resultat[i]:
                print(f"  - [{obj['nom']}] placé en X:{obj['x']:.2f}, Y:{obj['y']:.2f}, Z:{obj['z']:.2f}")