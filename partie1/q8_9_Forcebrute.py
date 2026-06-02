import time
from data.objets import objets

# Joas

def sac_a_dos_exact(capacite_max):
    n = len(objets)
    meilleure_utilite = 0
    meilleur_sac = []
    
    # Étape 1 : Calculer le nombre total de combinaisons (2 puissance n)
    total_combinaisons = 2 ** n
    
    # Étape 2 : Boucler sur tous les nombres possibles
    for i in range(total_combinaisons):
        
        # On convertit notre nombre 'i' en texte binaire (ex: '01011')
        # [2:] permet d'enlever le '0b' que Python rajoute toujours devant.
        # zfill(n) permet de rajouter des zéros devant pour avoir exactement 'n' caractères.
        combinaison_binaire = bin(i)[2:].zfill(n)
    
        masse_courante = 0
        utilite_courante = 0
        sac_courant = []
        
        # Étape 3 : On lit la combinaison binaire chiffre par chiffre
        for j in range(n):
            if combinaison_binaire[j] == '1': # Si on voit un 1, on met l'objet dans le sac
                masse_courante += objets[j]["masse"]
                utilite_courante += objets[j]["utilite"]
                sac_courant.append(objets[j]["nom"])
                
        # Étape 4 : L'épreuve du juge
        if round(masse_courante, 3) <= capacite_max and utilite_courante > meilleure_utilite:
            meilleure_utilite = utilite_courante
            meilleur_sac = sac_courant
            
    return meilleur_sac, round(meilleure_utilite, 2)


if __name__ == "__main__":
    capacites_a_tester = [2, 3, 4, 5]
    print("Brute Force")
    for C in capacites_a_tester:
        debut = time.time()
        sac_optimal, utilite_max = sac_a_dos_exact(C)
        fin = time.time()
        
        temps_execution = round(fin - debut, 2)
        print(f"\n Résultat pour C = {C} kg")
        print(f"Utilité maximale : {utilite_max}")
        print(f"Temps de calcul  : {temps_execution} secondes")