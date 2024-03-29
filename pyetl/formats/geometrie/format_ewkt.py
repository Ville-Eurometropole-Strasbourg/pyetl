# -*- coding: utf-8 -*-
# formats d'entree sortie
"""gestion des formats d'entree et de sortie. graphiques
"""


import re
import json

try:
    from shapely import wkb, wkt
except ImportError:
    print("==========================attention shapely non disponible")
    wkb = None
try:
    from osgeo import ogr
except ImportError:
    print("==========================attention ogr non disponible")
    wkb = None
# from numba import jit

TOKEN_SPECIFICATION = [
    ("N", r"-?\d+(\.\d*)?"),  # Integer or decimal number
    ("E", r"\)|;"),  # Statement terminator
    ("C", r"[A-Z]* *\("),  # Identifiers
    ("S", r","),
    ("P", r"SRID="),
    ("K", r"[ \t]+|\n"),  # Skip over spaces and tabs
    ("M", r"."),
]  # Any other character
TOK_REGEX = re.compile("|".join("(?P<%s>%s)" % pair for pair in TOKEN_SPECIFICATION))
KEYWORDS = {
    "MULTISURFACE(": "3",
    "MULTIPOLYGON(": "3",
    "POLYGON(": "3",
    "CURVEPOLYGON(": "3",
    "MULTILINESTRING(": "2",
    "MULTICURVE(": "2",
    "COMPOUNDCURVE(": "2",
    "CIRCULARSTRING(": "2",
    "LINESTRING(": "2",
    "POINT(": "1",
    "MULTIPOINT(": "1",
    "(": "0",
    "EMPTY": "0",
    "TIN(": "4",
    "POLYHEDRALSURFACE(": "5",
}


def decode_ewkt(code):
    """decodage du format ewkt avec expressions regulieres"""
    value = []
    liste = []
    zdef = [0.0]
    entite = ""
    dim = 2
    for token in TOK_REGEX.finditer(code):
        kind = token.lastgroup
        if kind == "N":
            value.append(float(token.group(kind)))
        #        elif kind == 'K':
        #            pass
        elif kind == "M":
            raise RuntimeError("%r unexpected on line %s" % (token.group(kind), code))
        elif kind == "S":
            if value:
                liste.append(value if dim == 3 else value + zdef)
                value = []
        elif kind == "E":
            if value:
                liste.append(value if dim == 3 else value + zdef)
                value = []
            yield ("end", entite, dim, liste)
            entite = ""
            liste = []
        elif kind == "C":
            entite = token.group(kind).replace(" ", "")
            if "Z" in entite:
                entite = entite.replace("Z", "")
                dim = 3
            liste = []
            if entite not in KEYWORDS:
                raise RuntimeError("%r inconnu" % (entite))
            yield ("start", entite, dim, liste)
        elif kind == "P":
            entite = "SRID"


def _parse_start(nature, niveau, poly, ring, nbring):
    """demarre un nouvel element"""
    type_geom = "0"
    try:
        tyg = KEYWORDS[nature]
    except KeyError:
        print("------------type geometrique inconnu", nature)
        return "0", None, None, None
    if tyg == "1":
        return "1", None, None, None
    if nature in {"POLYGON(", "CURVEPOLYGON("}:
        type_geom = "3"
        poly = niveau
    elif nature == "COMPOUNDCURVE(":
        if niveau == 1:
            type_geom = "2"
        elif poly:
            ring = niveau
            nbring += 1
    elif nature == "CIRCULARSTRING(":
        if niveau == 1:
            type_geom = "2"
        elif poly and not ring:
            ring = niveau
            nbring += 1
    elif nature == "(":
        if poly and not ring:
            ring = niveau
    else:
        type_geom = tyg
    return type_geom, poly, ring, nbring


def _parse_end(nature, valeurs, dim, nbring, niveau, geometrie):
    """finalise l'element"""
    if nature == "POINT(":
        geometrie.setpoint(valeurs[0], None, dim)
    #                    print ('detecte point ',valeurs[0], 0, dim)
    elif nature == "MULTIPOINT(":
        geometrie.setpoint(valeurs[0], None, dim)
        if len(valeurs) > 1:
            for i in valeurs[1:]:
                geometrie.addpoint(i, None, dim)
    elif nature == "(":
        geometrie.cree_section(valeurs, dim, 1, 0, interieur=nbring > 1)
    elif nature == "LINESTRING(":
        geometrie.cree_section(valeurs, dim, 1, 0, interieur=nbring > 1)
    elif nature == "CIRCULARSTRING(":
        geometrie.cree_section(valeurs, dim, 1, 1, interieur=nbring > 1)
    elif nature == "SRID":
        niveau += 1  # on compense
        geometrie.setsrid(valeurs[0][0])


def _parse_ewkt(geometrie, texte):
    """convertit une geometrie ewkt en geometrie interne"""
    dim = 2
    niveau = 0
    poly = 0
    ring = 0
    nbring = 0
    type_lu = None
    geometrie.type = "0"
    if not isinstance(texte, str):
        print("geometrie non decodable", texte)
        return
    if not texte:
        print("geometrie vide", texte)
        return
    try:
        for oper, nature, dim, valeurs in decode_ewkt(texte.upper()):
            # print ('decodage ewkt', oper, nature, dim, valeurs)
            if oper == "end":
                if poly == niveau:
                    poly = 0
                    nbring = 0
                elif ring == niveau:
                    ring = 0
                niveau -= 1

                _parse_end(nature, valeurs, dim, nbring, niveau, geometrie)

            elif oper == "start":
                dim = valeurs
                niveau += 1
                type_lu, poly, ring, nbring = _parse_start(
                    nature, niveau, poly, ring, nbring
                )
                geometrie.type = max(type_lu, geometrie.type)
    #                if not type_geom:
    #                    print ('erreur decodage', texte, oper, nature, valeurs)
    except RuntimeError as err:
        if "EMPTY" in texte:
            geometrie.type = "0"
            print("geometrie nulle", texte)
        else:
            geometrie.erreurs.ajout_erreur(err.args)
            print("erreur decodage geometrie", texte)


def geom_from_ewkt(obj):
    """convertit une geometrie ewkt en geometrie interne"""
    geom = obj.attributs["#geom"]
    if geom:
        # print ("conversion ewkt",geom)

        if geom.startswith("0"):  # c est de l'ewkb
            # print("detection ewkb")
            geom_from_ewkb(obj)
        else:
            _parse_ewkt(obj.geom_v, geom)
        if obj.schema:
            geom_demandee = obj.schema.info["type_geom"]
        else:
            geom_demandee = str(obj.geom_v.type)
        # print("decodage geometrie ewkt/ewkb ",obj.ident, obj.schema, "->", geom_demandee )
        try:
            obj.geom_v.angle = float(obj.attributs.get("#angle", 0))
        except ValueError:
            print("conversion angle impossible", obj.attributs.get("#angle"))
            obj.geom_v.angle = 0

        obj.finalise_geom(type_geom=str(geom_demandee))
    else:
        obj.finalise_geom(type_geom="0")
    if not obj.geom_v.valide:
        print("erreur geometrie", geom, geom_demandee)
    return obj.geom_v.valide


def _ecrire_coord_ewkt2d(pnt):
    """ecrit un point en 2D"""
    return "%f %f" % (pnt[0], pnt[1])


def _ecrire_coord_ewkt3d(pnt):
    """ecrit un point en 3D"""
    return "%f %f %f" % (pnt[0], pnt[1], pnt[2])


def ecrire_coord_ewkt(dim):
    """retourne la fonction d'ecriture adequate"""
    return _ecrire_coord_ewkt2d if dim == 2 else _ecrire_coord_ewkt3d


def _ecrire_point_ewkt(geom):
    """ecrit un point"""
    if geom.points:
        return (
            "POINT(" + _ecrire_coord_ewkt2d(geom.points[0]) + ")"
            if geom.dimension == 2
            else "POINT(" + _ecrire_coord_ewkt3d(geom.points[0]) + ")"
        )
    return ""


def _ecrire_multipoint_ewkt(geom):
    """ecrit un multipoint"""
    print("dans ecrire_multipoint", len(geom.points))
    if geom.points:
        return (
            "MULTIPOINT(("
            + "),(".join(_ecrire_coord_ewkt2d(point) for point in geom.points)
            + "))"
            if geom.dimension == 2
            else "MULTIPOINT(("
            + "),(".join(_ecrire_coord_ewkt3d(point) for point in geom.points)
            + "))"
        )
    return ""


def _ecrire_section_simple_ewkt(section):
    """ecrit une section"""
    ecrire = ecrire_coord_ewkt(section.dimension)
    return "(" + ",".join([ecrire(i) for i in section.coords]) + ")"


def _ecrire_section_ewkt(section, poly):
    """ecrit une section"""
    if section.courbe:
        prefix = "CIRCULARSTRING("
    elif poly:
        prefix = "("
    else:
        prefix = "LINESTRING("
    ecrire = ecrire_coord_ewkt(section.dimension)
    #    print('coords objet ')
    #    for i,j in enumerate(section.coords):
    #        print(i,j)
    #    print([i  for i in section.coords])
    return prefix + ",".join([ecrire(i) for i in section.coords]) + ")"


def _ecrire_ligne_ewkt(ligne, poly, erreurs, multiline=False):
    """ecrit une ligne en ewkt"""
    if poly and not ligne.ferme:
        if erreurs is not None:
            erreurs.ajout_erreur("ligne non fermee")
        return ""
    if not ligne.sections:
        if erreurs is not None:
            erreurs.ajout_erreur("ligne vide")
        return ""
    sec2 = [ligne.sections[0]]
    if sec2[0].courbe == 3:
        # print ("cercle")
        sec2[0].conversion_diametre()  # c' est un cercle# on modifie la description
    else:
        # print ('fusion sections',len(ligne.sections))
        for sect_courante in ligne.sections[1:]:  # on fusionne ce qui doit l'etre
            if sect_courante.courbe == sec2[-1].courbe:
                #                print ('fusion ',sect_courante.courbe,sec2[-1].courbe)
                sec2[-1].fusion(sect_courante)
            else:
                #                print ('ajout ',sect_courante.courbe,sec2[-1].courbe)
                sec2.append(sect_courante)
    if len(sec2) > 1:
        return (
            "COMPOUNDCURVE("
            + ",".join((_ecrire_section_ewkt(i, False) for i in sec2))
            + ")"
        )
    return _ecrire_section_ewkt(sec2[0], poly or multiline)


def _ecrire_multiligne_ewkt(lignes, courbe, erreurs, force_courbe=False):
    """ecrit une multiligne en ewkt"""
    # courbe=True # test courbes
    code = "MULTICURVE(" if courbe or force_courbe else "MULTILINESTRING("
    return (
        code
        + ",".join((_ecrire_ligne_ewkt(i, False, erreurs, True) for i in lignes))
        + ")"
    )


def _ecrire_polygone_ewkt(polygone, courbe, erreurs, multi=False, force_courbe=False):
    """ecrit un polygone en ewkt"""
    if courbe or force_courbe:
        code = "CURVEPOLYGON("
    elif multi:
        code = "("
    else:
        code = "POLYGON("
    return (
        code
        + ",".join(
            (_ecrire_ligne_ewkt(i, True, erreurs, False) for i in polygone.lignes)
        )
        + ")"
    )


def _ecrire_poly_tin(polygones, tin, _):
    """ecrit un tin en ewkt ne gere pas les erreurs"""
    if tin:
        code = "TIN("
    else:
        code = "POLYHEDRALSURFACE("

    return (
        code
        + ",".join(
            (_ecrire_section_simple_ewkt(i.lignes[0].sections[0]) for i in polygones)
        )
        + ")"
    )


def _ecrire_multipolygone_ewkt(polygones, courbe, erreurs, force_courbe):
    """ecrit un multipolygone en ewkt"""
    # print 'dans ecrire_polygone',len(polygones)
    # courbe=True # test courbes
    code = "MULTISURFACE(" if courbe or force_courbe else "MULTIPOLYGON("
    return (
        code
        + ",".join((_ecrire_polygone_ewkt(i, courbe, erreurs, True) for i in polygones))
        + ")"
    )


def _erreurs_type_geom(type_geom, geometrie_demandee, erreurs):
    if geometrie_demandee != type_geom:
        if not isinstance(geometrie_demandee, str) or not isinstance(type_geom, str):
            print("attention type incorrect", type_geom, "<->", geometrie_demandee)
            raise TypeError
        if type_geom == "1" or geometrie_demandee == "1":
            if erreurs is not None:
                erreurs.ajout_erreur(
                    "fmt:geometrie incompatible: demande "
                    + geometrie_demandee
                    + " existante: "
                    + type_geom
                )
            return 1
        if type_geom == "2":
            if erreurs is not None:
                erreurs.ajout_erreur(
                    "fmt:la geometrie n'est pas un polygone demande "
                    + geometrie_demandee
                    + " existante: "
                    + type_geom
                )
                #            raise
            return 1
    else:
        return 0


def init_ewk():
    global wkb, wkt, inited
    try:
        from shapely import wkb, wkt
    except ImportError:
        print("==========================attention shapely non disponible")
        wkb = None
    inited = True


def decode_ewkb(code):
    shapelygeom = wkb.loads(code)


def geom_from_shapely(obj):
    pass


def ecrire_geom_ewkb(
    geom, geometrie_demandee="-1", multiple=0, erreurs=None, force_courbe=False
):
    return hex(wkb.dumps(geom)) if wkb else ""


def geom_from_ewkb(obj, code=None):
    if code is None:
        code = obj.attributs.get("#geom")
    sgeom = wkb.loads(bytes.fromhex(code))
    # print("detecte wkb", sgeom.wkt)
    obj.geom_v.setsgeom(sgeom)
    obj.geom_v.shapesync()


def ecrire_geom_ewkt(
    geom,
    geometrie_demandee="-1",
    multiple=None,
    erreurs=None,
    force_courbe=False,
    epsg=True,
):
    """ecrit une geometrie en ewkt"""
    # print(" ecrire ewkt", geom)
    if geometrie_demandee == "0" or geom.type == "0" or geom.null:
        return None
    if geom.unsync == -1:  # c est du shapely
        geom.shapesync()
    geomt = ""
    type_geom = geom.type
    geometrie_demandee = geometrie_demandee if geometrie_demandee != "-1" else geom.type
    multiple = multiple if multiple is not None else geom.multi

    if _erreurs_type_geom(type_geom, geometrie_demandee, erreurs):
        return None
    courbe = geom.courbe
    if geometrie_demandee == "1":
        if multiple:
            geomt = _ecrire_multipoint_ewkt(geom)
        else:
            geomt = _ecrire_point_ewkt(geom)
    elif geometrie_demandee == "2":
        if geom.lignes:
            geomt = (
                _ecrire_multiligne_ewkt(geom.lignes, courbe, erreurs)
                if multiple
                else _ecrire_ligne_ewkt(geom.lignes[0], False, erreurs)
            )
        else:
            if erreurs is not None:
                erreurs.ajout_erreur("pas de geometrie ligne")
            return None
    elif geometrie_demandee == "3":
        if geom.polygones:
            geomt = (
                _ecrire_multipolygone_ewkt(
                    geom.polygones, courbe, erreurs, force_courbe
                )
                if multiple
                else _ecrire_polygone_ewkt(
                    geom.polygones[0], courbe, erreurs, False, force_courbe
                )
            )
        else:
            if erreurs is not None:
                erreurs.ajout_erreur("polygone non ferme")
            return None

    elif geometrie_demandee > "3":  # 4: tin  5: polyhedralsurface
        geomt = _ecrire_poly_tin(geom.polygones, geometrie_demandee == "4", erreurs)

    else:
        print("ecrire ewkt geometrie inconnue", geometrie_demandee)

    # print(" ecrire ewkt", geom)

    # print(" ecrire ewkt", geom.epsg, geometrie_demandee, multiple, geomt)
    if epsg:
        return (geom.epsg + geomt) if geomt else None
    else:
        return geomt if geomt else None

    # nom:(multiwriter,           streamer,         tmpgeomwriter,


#                 schema, casse, taille, driver, fanoutmax, format geom)


def noconversion(obj):
    """conversion geometrique par defaut"""
    return obj.geom_v.type == "0"


def nowrite(obj):
    """sans sortie"""
    return ""


def ecrire_geom_geojson(
    geom, geometrie_demandee="-1", multiple=0, erreurs=None, force_courbe=False
):
    return geom.__flatjson_if__


def geom_from_geojson(obj, code=None):
    geomdef = obj.attributs["#geom"]
    if isinstance(geomdef, list):
        geomdef = "\n".join(geomdef)
    # print("decodage geojson", geomdef)
    geom = json.loads(geomdef) if geomdef else None
    geom_demandee = obj.schema.info["type_geom"] if obj.schema else "0"
    if geom:
        #        print ('decodage geometrie ewkt ',obj.geom)
        obj.geom_v.from_geo_interface(geom)
        obj.geom_v.angle = float(obj.attributs.get("#angle", 0))
        obj.finalise_geom(type_geom=str(geom_demandee))
    else:
        obj.geom_v.finalise_geom(type_geom="0")
    return obj.geom_v.valide


def init_ogr():
    global ogr, ogr_inited
    try:
        from osgeo import ogr
    except ImportError:
        print("==========================attention ogr non disponible")
        ogr = None
    ogr_inited = True


def decode_ewkb(code):
    ogr_geom = ogr.CreateGeometryFromWkb(code)
    wkt_text = ogr_geom.ExportToWkt()
    geom = geom_from_ewkt(wkt_text)
    return geom


def geom_from_shapely(obj):
    pass


def ogr_ecrire_geom_ewkb(
    geom, geometrie_demandee="-1", multiple=0, erreurs=None, force_courbe=False
):
    wkt_text = ecrire_geom_ewkt(
        geom, geometrie_demandee, multiple, erreurs, force_courbe
    )
    ogr_geom = ogr.CreateGeometryFromWkb(wkt_text)
    return hex(ogr_geom.ExportToWkb()) if ogr_geom else ""


def ogr_geom_from_ewkb(obj, code=None):
    if code is None:
        code = obj.attributs.get("#geom")
    ogr_geom = ogr.CreateGeometryFromWkb(code)
    wkt_text = ogr_geom.ExportToWkt()
    obj.attributs["#geom"] = wkt_text
    geom_from_ewkt(obj)
    obj.attributs["#geom"] = code


GEOMDEF = {
    "#ewkt": (ecrire_geom_ewkt, geom_from_ewkt, init_ewk, str),
    "#ewkb": (ecrire_geom_ewkb, geom_from_ewkb, init_ewk, str),
    "#ogr_ewkb": (ogr_ecrire_geom_ewkb, ogr_geom_from_ewkb, init_ogr, str),
    "#geojson": (ecrire_geom_geojson, geom_from_geojson, None, list),
    None: (nowrite, noconversion, None, None),
}
