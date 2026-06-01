import time # chronometre pour mesurer le temps d'exécution
import itertools # pour générer toutes les combinaisons possibles de 0 et de 1 (sac à dos)
import sys # creer un chemin pour que Python trouve le dossier 'data'
import os # creer un chemin pour que Python trouve le dossier 'data'

#  L'astuce pour que Python trouve le dossier 'data' de Thomas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# impotation de la liste d'objets depuis le fichier 'data/objets.py'
from data.objets import objets

def sac_a_dos_exact(capacite_max): # pour tester les differents sacs
    n = len(objets) # liste le nombre d'objets disponibles
    meilleure_utilite = 0
    meilleur_sac = [] # au début le sac est vide 
    
    # Étape 1 : itertools crée toutes les combinaisons possibles de 0 et de 1
    for combinaison in itertools.product([0, 1], repeat=n) :
        
        masse_courante = 0
        utilite_courante = 0
        sac_courant = []
        
        # Étape 2 : On lit la combinaison (Adapté pour les dictionnaires de Thomas !)
        for j in range(n):
            if combinaison[j] == 1:  # Si la case est à 1, on embarque l'objet
                masse_courante += objets[j]["masse"] # on ajoute la masse de l'objet au poids total du sac
                utilite_courante += objets[j]["utilite"] # on ajoute l'utilité de l'objet à l'utilité totale du sac
                sac_courant.append(objets[j]["nom"]) # on ajoute le nom de l'objet au sac courant
                
        # Étape 3 : On vérifie si ce sac respecte le poids ET bat le record
        if round(masse_courante, 3) <= capacite_max and utilite_courante > meilleure_utilite:
            meilleure_utilite = utilite_courante
            meilleur_sac = sac_courant
            
    return meilleur_sac, round(meilleure_utilite, 2)


# EXÉCUTION DU CODE (POUR L'AFFICHAGE) II. question 9 
capacites_a_tester = [2, 3, 4, 5]
print("Démarrage de la Force Brute (cela peut prendre quelques secondes par test)...")

for C in capacites_a_tester:
    debut = time.time() # on démarre le chronomètre
    sac_optimal, utilite_max = sac_a_dos_exact(C) # on appelle la fonction pour trouver le sac optimal et son utilité maximale pour la capacité C
    fin = time.time() # on arrête le chronomètre
    
    temps_execution = round(fin - debut, 2)
    
    print(f"\n--- Résultat pour C = {C} kg ---")
    print(f"Utilité maximale : {utilite_max}")
    print(f"Temps de calcul  : {temps_execution} secondes")