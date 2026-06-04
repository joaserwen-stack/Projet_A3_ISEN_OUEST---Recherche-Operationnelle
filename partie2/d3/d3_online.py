import os
import time
import math
from utils import load_marchandises, print_results

# =====================================================================
# Écrit par : Joas
# =====================================================================

# --- CONSTANTES GÉOMÉTRIQUES DU PROBLÈME ---
# Dimensions réglementaires du wagon SNCF données dans l'énoncé
L_WAG, l_WAG, H_WAG = 11.583, 2.294, 2.569
VOL_WAG = L_WAG * l_WAG * H_WAG
EPS = 1e-4  # Seuil de tolérance numérique pour la comparaison de nombres flottants (évite les bugs d'arrondi)


class Marchandise:
    """
    Représente un objet à charger. Gère le calcul des différentes rotations 3D 
    admissibles en fonction des restrictions physiques de l'objet.
    """
    __slots__ = ['id', 'rotations']

    def __init__(self, data: dict):
        self.id = data['id']
        L, l, H = data['longueur'], data['largeur'], data['hauteur']

        # Si l'objet n'est pas retournable (ex: tête en haut obligatoire), 
        # on ne s'autorise que les rotations sur le plan horizontal (pivot Z)
        if data.get('retournable', 1) == 0:
            rot = [(L, l, H), (l, L, H)]
        else:
            # Sinon, génération des 6 orientations spatiales possibles en 3D
            rot = [(L, l, H), (L, H, l), (l, L, H), (l, H, L), (H, L, l), (H, l, L)]

        # Tri par hauteur croissante (r[2]) : astuce pour favoriser la stabilité 
        # en plaçant les objets avec un centre de gravité bas en priorité
        self.rotations = sorted(set(rot), key=lambda r: r[2])


class Wagon:
    """
    Modélise l'espace intérieur d'un wagon. Reçoit les boîtes intégrées, 
    gère l'intersection géométrique, calcule la surface de support et génère 
    les Extreme Points (EP) pour optimiser le maillage de l'espace libre.
    """
    __slots__ = ['boites', 'coins', 'vol_used']

    def __init__(self):
        # Chaque boîte stockée est modélisée par le tuple : (cx, cy, cz, rL, rl, rH, item_id)
        self.boites: list[tuple] = []
        self.coins: set[tuple] = {(0.0, 0.0, 0.0)}  # Liste dynamique des points d'ancrage libres (Extreme Points)
        self.vol_used: float = 0.0                  # Cumul du volume des objets présents

    def intersecte(self, b1: tuple) -> bool:
        """
        Détection de collision 3D par chevauchement AABB (Axis-Aligned Bounding Boxes).
        Ajout du seuil EPS pour éviter les faux positifs dus aux approximations des flottants.
        Chaque ligne vérifie s'il y a un recouvrement sur les axes X, Y et Z simultanément.
        """
        for b2 in self.boites:
            if (b1[0] < b2[0] + b2[3] - EPS and b1[0] + b1[3] > b2[0] + EPS and
                    b1[1] < b2[1] + b2[4] - EPS and b1[1] + b1[4] > b2[1] + EPS and
                    b1[2] < b2[2] + b2[5] - EPS and b1[2] + b1[5] > b2[2] + EPS):
                return True
        return False

    def est_supportee(self, xmin: float, xmax: float, ymin: float, ymax: float,
                      zmin: float, seuil: float = 0.55) -> bool:
        """
        Vérification de la gravité/stabilité : une boîte posée en hauteur (zmin > 0) 
        doit obligatoirement reposer sur le toit d'autres boîtes sur au moins 'seuil' % de sa base.
        """
        if zmin <= EPS:  # Posé directement sur le plancher du wagon -> Toujours stable
            return True

        aire_base = (xmax - xmin) * (ymax - ymin)  # Aire totale sous la boîte courante
        aire_support = 0.0

        # On parcourt les boîtes déjà placées pour voir si leur sommet touche le bas de notre boîte
        for bx, by, bz, bL, bl, bH, *_ in self.boites:
            # Vérification de coïncidence sur l'axe Z (sommet de la boîte existante == base de la nouvelle)
            if abs(bz + bH - zmin) <= EPS:
                # Calcul de la zone d'intersection (recouvrement X/Y) entre les deux bases
                ox = min(xmax, bx + bL) - max(xmin, bx)
                oy = min(ymax, by + bl) - max(ymin, by)

                # Si l'intersection existe en 2D, on ajoute sa surface à l'aire de support cumulée
                if ox > 0 and oy > 0:
                    aire_support += ox * oy

        # True si le pourcentage de surface en contact direct est supérieur ou égal au seuil demandé
        return (aire_support / aire_base) >= seuil

    def _ajouter_coin(self, x: float, y: float, z: float) -> None:
        """Ajoute un point à la liste des coins admissibles s'il respecte le gabarit du wagon."""
        if x <= L_WAG and y <= l_WAG and z <= H_WAG:
            self.coins.add((x, y, z))

    def placer(self, coin: tuple, rL: float, rl: float, rH: float, item_id: int = 0) -> None:
        """
        Positionne définitivement un objet dans le wagon et met à jour le maillage 
        de l'espace par la méthode avancée des Extreme Points (EP).
        """
        cx, cy, cz = coin
        n_avant = len(self.boites) # Nombre de boîtes avant l'ajout (sert de borne pour le parcours)

        # Enregistrement de la nouvelle boîte et mise à jour du volume utilisé
        self.boites.append((cx, cy, cz, rL, rl, rH, item_id))
        self.vol_used += rL * rl * rH
        self.coins.discard(coin)   # Le point d'ancrage utilisé est consommé et retiré

        # Coordonnées des extrémités supérieures de la boîte insérée
        xf, yf, zf = cx + rL, cy + rl, cz + rH

        # 1. GÉNÉRATION DES CORNERS STANDARDS : 
        # Ajout des 3 coins immédiats générés sur les arêtes de la nouvelle boîte
        self._ajouter_coin(xf, cy, cz)
        self._ajouter_coin(cx, yf, cz)
        self._ajouter_coin(cx, cy, zf)

        # 2. EXTENSION EXTREME POINTS (Génération par projection croisée) :
        # Pour maximiser le remplissage et éviter les espaces perdus, on projette les arêtes 
        # de la nouvelle boîte sur les frontières des boîtes déjà existantes dans le wagon.
        for bx, by, bz, bL, bl, bH, *_ in self.boites[:n_avant]:
            bxf, byf, bzf = bx + bL, by + bl, bz + bH

            # Projection axe X de la nouvelle boîte combinée aux axes Y et Z de l'existante
            for nx in (cx, xf):
                for ey in (by, byf):
                    for ez in (bz, bzf):
                        self._ajouter_coin(nx, ey, ez)

            # Projection axe Y de la nouvelle boîte combinée aux axes X et Z de l'existante
            for ny in (cy, yf):
                for ex in (bx, bxf):
                    for ez in (bz, bzf):
                        self._ajouter_coin(ex, ny, ez)

            # Projection axe Z de la nouvelle boîte combinée aux axes X et Y de l'existante
            for nz in (cz, zf):
                for ex in (bx, bxf):
                    for ey in (by, byf):
                        self._ajouter_coin(ex, ey, nz)

        # 3. ÉLAGAGE DES COINS INTERNES (Pruning) :
        # Nettoyage critique de la liste : si des Extreme Points libres créés précédemment 
        # se retrouvent désormais emprisonnés à l'intérieur du volume de la boîte qu'on 
        # vient de poser, ils deviennent inaccessibles. On les supprime définitivement.
        self.coins -= {
            (px, py, pz) for px, py, pz in self.coins
            if cx + EPS < px < xf - EPS
               and cy + EPS < py < yf - EPS
               and cz + EPS < pz < zf - EPS
        }


def placer_item(item: Marchandise, wagons: list[Wagon]) -> None:
    """
    Algorithme de placement de la marchandise courante (Logique Online).
    - Parcourt les wagons dans leur ordre d'ouverture (First-Fit).
    - Pour chaque wagon, teste tous les Extreme Points disponibles et toutes les rotations.
    - Sélectionne la position locale qui minimise le volume restant (Best-Fit Local).
    """
    for w in wagons:
        best_local = None  # Structure : (espace_restant, coin_cible, rotation_choisie)

        # Tri topologique des points d'ancrage : bas (Z), puis fond (X), puis côté (Y)
        for coin in sorted(w.coins, key=lambda c: (c[2], c[0], c[1])):
            cx, cy, cz = coin
            for rL, rl, rH in item.rotations:
                # 1. Vérification stricte de l'encombrement par rapport au gabarit du wagon
                if cx + rL <= L_WAG + EPS and cy + rl <= l_WAG + EPS and cz + rH <= H_WAG + EPS:
                    # 2. Vérification géométrique de non-collision
                    if not w.intersecte((cx, cy, cz, rL, rl, rH)):
                        # 3. Vérification de la stabilité de la base (portance mécanique)
                        if w.est_supportee(cx, cx + rL, cy, cy + rl, cz):
                            # Évaluation de la performance locale (Best-Fit)
                            remaining = VOL_WAG - w.vol_used - rL * rl * rH
                            if best_local is None or remaining < best_local[0]:
                                best_local = (remaining, coin, (rL, rl, rH))

        # Si le wagon courant possède au moins un Extreme Point valide pour cet objet
        if best_local is not None:
            _, coin, (rL, rl, rH) = best_local
            w.placer(coin, rL, rl, rH, item.id) # Intégration physique de l'objet
            return                              # Fin de traitement de l'objet, on passe au suivant

    # CAS CONCRET ONLINE : Si aucun wagon existant ne peut accueillir l'objet dans l'état actuel,
    # on n'a pas le droit d'attendre ou de trier. On ouvre instantanément un nouveau wagon.
    nw = Wagon()
    chosen = None
    # Sélection de la première orientation de l'objet qui rentre dans un wagon vide
    for rL, rl, rH in item.rotations:
        if rL <= L_WAG + EPS and rl <= l_WAG + EPS and rH <= H_WAG + EPS:
            chosen = (rL, rl, rH)
            break
    if chosen is None:
        chosen = item.rotations[0]

    rL, rl, rH = chosen
    # Positionnement par défaut à l'origine absolue (0,0,0) du nouveau conteneur
    nw.boites.append((0.0, 0.0, 0.0, rL, rl, rH, item.id))
    nw.vol_used = rL * rl * rH
    # Génération du trièdre de coins initial le long de cette première boîte
    nw.coins = {(rL, 0.0, 0.0), (0.0, rl, 0.0), (0.0, 0.0, rH)}
    wagons.append(nw) # Ajout du nouveau wagon à la flotte


def wagons_vers_boites(wagons: list[Wagon]) -> list[list[tuple]]:
    """
    Fonction de conversion utilitaire. Transforme la liste d'objets complexes 'Wagon' 
    en listes de tuples purs, structure brute attendue par le module graphique 3D.
    """
    return [list(w.boites) for w in wagons]


# --- SCRIPT D'EXÉCUTION PRINCIPAL ---

if __name__ == "__main__":
    print("=" * 65)
    print("  D3 ONLINE - EXTREME POINTS BEST-FIT LOCAL")
    print("=" * 65)

    # Récupération de la base de données via le loader de l'énoncé sous Moodle
    marchandises = load_marchandises()
    if not marchandises:
        raise SystemExit("Erreur : Impossible de charger les données.")

    # Calcul de la borne inférieure théorique (somme des volumes des objets / volume d'un wagon)
    vol_total = sum(m['longueur'] * m['largeur'] * m['hauteur'] for m in marchandises)
    borne_inf = math.ceil(vol_total / VOL_WAG)

    print(f"Chargement : {len(marchandises)} marchandises chargées.")
    print(f"Volume total : {vol_total:.2f} m³ | Borne inférieure théorique : {borne_inf} wagons")
    print("-" * 65)

    # Instanciation séquentielle des objets métiers (L'ordre original du fichier de données est strictement conservé - Mode Online)
    items = [Marchandise(m) for m in marchandises]
    wagons: list[Wagon] = []

    # Enclenchement du chronomètre de calcul (Début de l'évaluation de la complexité temporelle)
    t_debut = time.time()
    for item in items:
        placer_item(item, wagons) # Traitement au fil de l'eau de chaque marchandise
    temps_total = time.time() - t_debut

    # Calcul des indicateurs de performance logistique pour le rapport et la soutenance
    nb_wagons = len(wagons)
    volume_perdu = nb_wagons * VOL_WAG - vol_total

    # Affichage normalisé des résultats dans la console
    print_results("d=3", "Online Extreme-Points Best-Fit Local", nb_wagons, volume_perdu, temps_total)

    # RECONSTRUCTION GÉOMÉTRIQUE POUR LE MODULE GRAPHIQUE :
    wagons_boites = wagons_vers_boites(wagons)
    try:
        from d3_visualisation import visualiser_wagons
        # Création dynamique du dossier de rendu s'il n'existe pas sur la machine
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rendus")
        os.makedirs(output_dir, exist_ok=True)
        # Génération des images 3D avec un préfixe spécifique pour ne pas écraser les résultats du mode Offline
        visualiser_wagons(wagons_boites, output_dir=output_dir, prefix="online_wagon")
        print(f"Images sauvegardées dans : {output_dir}")
    except ImportError:
        print("d3_visualisation non disponible — visualisation ignorée.")