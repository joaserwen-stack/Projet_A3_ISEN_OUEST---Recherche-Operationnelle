from data.objets import objets
from partie1.q5_glouton import glouton

n = len(objets)
c = 0.6
sac = glouton(objets, n, c)

for objet in sac:
    print(objet["nom"], objet["masse"], objet["utilite"])