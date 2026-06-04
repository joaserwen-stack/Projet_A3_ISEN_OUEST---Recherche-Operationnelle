import time
from data.objets import objets

# =====================================================================
# Écrit par : Joas
# =====================================================================

def sac_a_dos_exact(capacite_max):
    n = len(objets)
    meilleure_utilite = 0
    meilleur_sac = []

    # Calcul du nombre total de combinaisons possibles (2 puissance n)
    total_combinaisons = 2 ** n

    # Boucle d'exploration complète de l'espace des solutions
    for i in range(total_combinaisons):

        # Conversion de l'entier en sa représentation binaire textuelle (ex: '01011')
        # Le slice [2:] retire le préfixe '0b' généré par Python
        # zfill(n) comble avec des zéros à gauche pour s'assurer d'avoir un bit par objet
        combinaison_binaire = bin(i)[2:].zfill(n)

        masse_courante = 0
        utilite_courante = 0
        sac_courant = []

        # Lecture de la combinaison bit par bit pour construire le sac correspondant
        for j in range(n):
            if combinaison_binaire[j] == '1': # Si le bit vaut 1, l'objet est sélectionné
                masse_courante += objets[j]["masse"]
                utilite_courante += objets[j]["utilite"]
                sac_courant.append(objets[j]["nom"])

        # Vérification des contraintes et mise à jour de la meilleure solution globale
        # On arrondit la masse pour éviter les approximations de calcul sur les flottants
        if round(masse_courante, 3) <= capacite_max and utilite_courante > meilleure_utilite:
            meilleure_utilite = utilite_courante
            meilleur_sac = sac_courant

    return meilleur_sac, round(meilleure_utilite, 2)


if __name__ == "__main__":
    # Évaluation de l'algorithme exact sur différentes capacités maximales
    for C in [0.6, 2, 3, 4, 5]:
        debut = time.time()
        sac_optimal, score = sac_a_dos_exact(C)
        temps_calcul = time.time() - debut

        print(f"\n--- Résultat pour C = {C} ---")

        # Calcul a posteriori de la masse totale du sac optimal pour l'affichage
        poids_total = sum(o["masse"] for o in objets if o["nom"] in sac_optimal)

        print(f"Composition du sac : {sac_optimal}")
        print(f"Poids total embarqué : {round(poids_total, 3)} kg")
        print(f"Utilité totale : {score}")
        print(f"Temps de calcul : {temps_calcul:.6f} secondes")