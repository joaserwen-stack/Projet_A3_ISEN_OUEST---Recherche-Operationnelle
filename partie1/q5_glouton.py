from data.objets import objets

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
    C = 0.6
    sac = glouton(objets, n, C)
    masse_tot = 0
    for objet in sac:
        print(objet["nom"], objet["masse"], objet["utilite"])
        masse_tot += objet["masse"]
    print("Masse total :", masse_tot)