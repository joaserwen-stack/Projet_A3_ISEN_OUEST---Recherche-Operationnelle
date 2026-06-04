from data.objets import objets
import time

# =====================================================================
# Écrit par : Thomas
# =====================================================================

def glouton(objets, n, C):
    # On initialise le poids actuel du sac à 0 et on prépare la liste qui va contenir les objets choisis
    masse_totale = 0
    sac = []

    # On fait une copie de la liste pour pouvoir retirer les objets au fur et à mesure sans modifier la liste d'origine
    objets_restants = objets.copy()

    # On lance une boucle pour analyser et classer les 'n' premiers objets de la liste
    for i in range(1, n + 1):
        # On réinitialise la recherche du meilleur ratio pour cette itération
        meilleur_ratio = -1
        meilleur_objet = None

        # On parcourt tous les objets restants pour trouver celui qui offre le meilleur rendement (utilité / masse)
        for j in range(len(objets_restants)):
            ratio = objets_restants[j]["utilite"] / objets_restants[j]["masse"]
            if ratio > meilleur_ratio:
                meilleur_ratio = ratio
                meilleur_objet = objets_restants[j]

        # Vérification de la contrainte de poids
        # Une fois le meilleur objet identifié, on regarde si sa masse ne fait pas déborder le sac.
        # Si ça passe, on l'embarque officiellement et on met à jour la masse cumulée.
        if masse_totale + meilleur_objet["masse"] <= C:
            sac.append(meilleur_objet)
            masse_totale += meilleur_objet["masse"]

        # Qu'on ait pu le mettre dans le sac ou non, on l'enlève des objets disponibles pour ne pas le réanalyser au prochain tour
        objets_restants.remove(meilleur_objet)

    return sac

if __name__ == "__main__":
    # Détermination du nombre total d'objets disponibles dans le dataset importé
    n = len(objets)

    # On teste l'algorithme sur plusieurs capacités maximales (C) pour analyser son comportement
    for C in [0.6, 2, 3, 4, 5]:
        debut = time.time()
        sac_optimal = glouton(objets, n, C)
        temps_calcul = time.time() - debut

        print(f"\n--- Résultat pour C = {C} ---")

        # Extraction des données pour l'affichage du rapport
        composition = [o["nom"] for o in sac_optimal]
        poids_total = sum(o["masse"] for o in sac_optimal)
        utilite_totale = sum(o["utilite"] for o in sac_optimal)

        # Affichage propre des performances et de la composition finale du sac
        print(f"Composition du sac : {composition}")
        print(f"Poids total embarqué : {round(poids_total, 3)} kg")
        print(f"Utilité totale : {round(utilite_totale, 2)}")
        print(f"Temps de calcul : {temps_calcul:.6f} secondes")