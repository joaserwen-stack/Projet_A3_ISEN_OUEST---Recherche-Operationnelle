import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import math
from utils import load_marchandises, print_results, WAGON_L, WAGON_l

LONGUEUR_WAGON = WAGON_L
LARGEUR_WAGON = WAGON_l
EPS = 1e-9


def mettre_a_jour_espaces(wagon, obj_x, obj_y, obj_longueur, obj_largeur):
    nouveaux_espaces = []
    bord_droit_obj = obj_x + obj_longueur
    bord_haut_obj = obj_y + obj_largeur

    for espace_x, espace_y, espace_largeur, espace_hauteur in wagon['espaces_libres']:
        bord_droit_espace = espace_x + espace_largeur
        bord_haut_espace = espace_y + espace_hauteur

        # Si l'espace libre actuel n'intersecte pas l'objet placé, on le conserve intact
        if (obj_x >= bord_droit_espace - EPS or bord_droit_obj <= espace_x + EPS or
                obj_y >= bord_haut_espace - EPS or bord_haut_obj <= espace_y + EPS):
            nouveaux_espaces.append((espace_x, espace_y, espace_largeur, espace_hauteur))
            continue

        # MaxRects
        # Lorsqu'un rectangle libre chevauche le nouvel objet, il est détruit. À sa place, on génère
        # jusqu'à 4 nouveaux sous-rectangles maximaux (gauche, droite, bas, haut) correspondant aux
        # bandes résiduelles restées vides autour de la boîte insérée.
        if obj_x > espace_x + EPS:
            nouveaux_espaces.append((espace_x, espace_y, obj_x - espace_x, espace_hauteur))
        if bord_droit_obj < bord_droit_espace - EPS:
            nouveaux_espaces.append((bord_droit_obj, espace_y, bord_droit_espace - bord_droit_obj, espace_hauteur))
        if obj_y > espace_y + EPS:
            nouveaux_espaces.append((espace_x, espace_y, espace_largeur, obj_y - espace_y))
        if bord_haut_obj < bord_haut_espace - EPS:
            nouveaux_espaces.append((espace_x, bord_haut_obj, espace_largeur, bord_haut_espace - bord_haut_obj))

    wagon['espaces_libres'] = nettoyer_espaces_inutiles(nouveaux_espaces)


def nettoyer_espaces_inutiles(espaces):
    espaces_valides = [(x, y, l, h) for x, y, l, h in espaces if l > EPS and h > EPS]
    espaces_utiles = []

    # Élimination des rectangles inclus
    # La découpe précédente crée de la redondance. On compare chaque rectangle libre à tous les autres :
    # si l'un d'eux est entièrement englobé géométriquement par un rectangle voisin plus grand (ou identique),
    # on le supprime pour ne garder strictement que des espaces vides "maximaux".
    for i, (x1, y1, l1, h1) in enumerate(espaces_valides):
        contenu = False
        for j, (x2, y2, l2, h2) in enumerate(espaces_valides):
            if i != j and (x1 >= x2 - EPS and y1 >= y2 - EPS and
                           x1 + l1 <= x2 + l2 + EPS and y1 + h1 <= y2 + h2 + EPS):
                contenu = True
                break
        if not contenu:
            espaces_utiles.append((x1, y1, l1, h1))
    return espaces_utiles


def remplir_wagons(objets):
    wagons = []

    for objet in objets:
        placer_objet(wagons, objet)

    return wagons


def placer_objet(wagons, objet):
    obj_longueur = objet['longueur']
    obj_largeur = objet['largeur']

    ok_normal = obj_longueur <= LONGUEUR_WAGON and obj_largeur <= LARGEUR_WAGON
    ok_pivote = obj_longueur != obj_largeur and obj_largeur <= LONGUEUR_WAGON and obj_longueur <= LARGEUR_WAGON

    if not ok_normal and not ok_pivote:
        return

    meilleur_score = None
    meilleur_choix = None

    for index_wagon, wagon in enumerate(wagons):
        for espace_x, espace_y, espace_largeur, espace_hauteur in wagon['espaces_libres']:

            #  Best Long Side Fit
            # Pour chaque espace libre capable d'accueillir l'objet, on évalue la dimension libre maximale
            # restante après insertion (via max(largeur_restante, hauteur_restante)).
            # En minimisant ce score, on choisit l'espace qui encastre l'objet le plus étroitement le long
            # de son grand côté, ce qui évite de casser les grandes zones vides homogènes du wagon.

            if ok_normal and obj_longueur <= espace_largeur + EPS and obj_largeur <= espace_hauteur + EPS:
                score = max(espace_largeur - obj_longueur, espace_hauteur - obj_largeur)
                if meilleur_score is None or score < meilleur_score:
                    meilleur_score = score
                    meilleur_choix = (index_wagon, espace_x, espace_y, obj_longueur, obj_largeur, False)

            if ok_pivote and obj_largeur <= espace_largeur + EPS and obj_longueur <= espace_hauteur + EPS:
                score = max(espace_largeur - obj_largeur, espace_hauteur - obj_longueur)
                if meilleur_score is None or score < meilleur_score:
                    meilleur_score = score
                    meilleur_choix = (index_wagon, espace_x, espace_y, obj_largeur, obj_longueur, True)

    if meilleur_choix is not None:
        index_wagon, x_choisi, y_choisi, longueur_placee, largeur_placee, a_ete_pivote = meilleur_choix
        mettre_a_jour_espaces(wagons[index_wagon], x_choisi, y_choisi, longueur_placee, largeur_placee)
        wagons[index_wagon]['objets'].append(
            {**objet, 'rotation': a_ete_pivote, 'placed_l': longueur_placee, 'placed_w': largeur_placee, 'x': x_choisi, 'y': y_choisi}
        )
    else:
        # Initialisation d'un nouveau wagon vide avec l'intégralité de sa surface déclarée comme espace libre
        nouveau_wagon = {
            'espaces_libres': [(0, 0, LONGUEUR_WAGON, LARGEUR_WAGON)],
            'objets': []
        }
        longueur_placee, largeur_placee, a_ete_pivote = (obj_longueur, obj_largeur, False) if ok_normal else (obj_largeur, obj_longueur, True)
        mettre_a_jour_espaces(nouveau_wagon, 0, 0, longueur_placee, largeur_placee)
        nouveau_wagon['objets'].append(
            {**objet, 'rotation': a_ete_pivote, 'placed_l': longueur_placee, 'placed_w': largeur_placee, 'x': 0, 'y': 0}
        )
        wagons.append(nouveau_wagon)


# ─── Lancement du programme ────────────────────────────────────

if __name__ == "__main__":
    print("=" * 65)
    print("  Bin-Packing 2D Online — MaxRects BLSF")
    print("=" * 65)

    objets_a_placer = load_marchandises()
    print(f"Nombre d'objets a charger : {len(objets_a_placer)}")

    if len(objets_a_placer) == 0:
        print("Il n'y a rien a charger.")
        exit(0)

    debut_chrono = time.time()
    wagons_remplis = remplir_wagons(objets_a_placer)
    temps_ecoule = time.time() - debut_chrono

    nb_wagons_utilises        = len(wagons_remplis)
    surface_dun_wagon         = LONGUEUR_WAGON * LARGEUR_WAGON
    surface_totale_disponible = nb_wagons_utilises * surface_dun_wagon
    surface_totale_objets     = sum(obj['longueur'] * obj['largeur'] for obj in objets_a_placer)
    surface_vide_perdue       = surface_totale_disponible - surface_totale_objets

    borne_inferieure_theorique = math.ceil(surface_totale_objets / surface_dun_wagon)

    print("\n" + "=" * 65 + "\n  RÉSULTAT\n" + "=" * 65)
    print_results(
        dimension_label="d=2",
        mode_label="Online (MaxRects BLSF)",
        nb_wagons=nb_wagons_utilises,
        total_unused=surface_vide_perdue,
        execution_time=temps_ecoule
    )

    print(f"  Borne inférieure théorique (les objets sont de l'eau) : {borne_inferieure_theorique} wagons")
    print(f"  Taux d'occupation moyen : {(surface_totale_objets / surface_totale_disponible) * 100:.1f}%")
    print(f"  Ratio par rapport à la perfection : {nb_wagons_utilises}/{borne_inferieure_theorique} ({nb_wagons_utilises / borne_inferieure_theorique:.2f}x plus grand)\n")

    print("Contenu des 5 premiers wagons :")
    for i, wagon in enumerate(wagons_remplis[:5]):
        print(f"\n  Wagon {i + 1} ({len(wagon['objets'])} objets) :")
        for obj in sorted(wagon['objets'], key=lambda o: (o['y'], o['x'])):
            symbole_rotation = " (pivote)" if obj['rotation'] else ""
            print(f"    . ID {obj['id']:<2} | Pos: X={obj['x']:05.2f}, Y={obj['y']:05.2f} | "
                  f"Espace occupé: {obj['placed_l']}m x {obj['placed_w']}m{symbole_rotation}")