from data.objets import objets
import time

# Thomas

def glouton(objets, n, C):
    masse_totale = 0
    sac = []
    objets_restants = objets.copy()

    for i in range(1, n + 1):
        meilleur_ratio = -1
        meilleur_objet = None

        for j in range(len(objets_restants)):
            ratio = objets_restants[j]["utilite"] / objets_restants[j]["masse"]
            if ratio > meilleur_ratio:
                meilleur_ratio = ratio
                meilleur_objet = objets_restants[j]

        if masse_totale + meilleur_objet["masse"] <= C:
            sac.append(meilleur_objet)
            masse_totale += meilleur_objet["masse"]

        objets_restants.remove(meilleur_objet)

    return sac

if __name__ == "__main__":
    n = len(objets)

    for C in [0.6, 2, 3, 4, 5]:
        debut = time.time()
        sac_optimal = glouton(objets, n, C)

        temps_calcul = time.time() - debut

        print(f"\n--- Résultat pour C = {C} ---")

        composition = [o["nom"] for o in sac_optimal]
        poids_total = sum(o["masse"] for o in sac_optimal)
        utilite_totale = sum(o["utilite"] for o in sac_optimal)

        print(f"Composition du sac : {composition}")
        print(f"Poids total embarqué : {round(poids_total, 3)} kg")
        print(f"Utilité totale : {round(utilite_totale, 2)}")
        print(f"Temps de calcul : {temps_calcul:.6f} secondes")