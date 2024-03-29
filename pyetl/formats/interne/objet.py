# -*- coding: utf-8 -*-
""" definition interne des objets
attributs et geometrie """

import copy
import itertools
import collections
import logging
import json

# from pyetl.formats.interne.stats import LOGGER
from .geometrie.geom import Geometrie, Erreurs

LOGGER = logging.getLogger(__name__)
# class AttributsSpeciaux(object):
#     """gere les attibuts speciaux a certains formats """

#     __slots__ = ["typespecial", "valeurs", "special"]

#     def __init__(self):
#         self.typespecial = dict()
#         self.valeurs = dict()
#         self.special = dict()

#     def set_att(self, nom, nature, valeur):
#         """positionne un attribut special"""
#         self.special[nom] = nature
#         self.valeurs[nom] = valeur

#     def get_speciaux(self):
#         """ recupere la lisdte des attributs speciaux"""
#         return self.special, self.valeurs


def noconversion(obj):
    """conversion geometrique par defaut"""
    return obj.attributs["#type_geom"] == "0"


class Objet(object):
    """structure de stockage d'un objet."""

    _ido = itertools.count(1)  # compteur d'instance
    __slots__ = [
        "ido",
        "numobj",
        "copie",
        "geom_v",
        "forcegeom",
        "stored",
        "is_ok",
        "redirect",
        "classe_is_att",
        "liste_attributs",
        "idorig",
        "attributs",
        "hdict",
        "multiples",
        "attributs_speciaux",
        "geomnatif",
        "erreurs",
        "format_natif",
        "virtuel",
        "schema",
        "attributs_geom",
        "casefold",
        "key",
    ]

    def __init__(
        self,
        groupe,
        classe,
        format_natif="asc",
        conversion=None,
        schema=None,
        attributs=None,
        numero=None,
        orig=None,
    ):
        self.geom_v = Geometrie()
        #        self.valide = False
        self.forcegeom = False  # force une geometrie de ligne
        self.ido = next(self._ido)
        self.numobj = self.ido if numero is None else numero
        #        print ("nouveau",self.ido)
        # self.ccx, self.ccy, self.ccz, self.angle = 0, 0, 0, 0
        self.key = None
        self.copie = 0
        self.stored = False
        self.is_ok = True
        self.redirect = None  # pour traitement de sorties calculees
        self.classe_is_att = False
        # self.atg = False
        self.idorig = orig if orig is not None else (groupe, classe)
        groupe_orig, classe_orig = self.idorig
        self.attributs = dict(
            (
                ("#statgroupe", "total"),
                ("#type_geom", "0"),
                ("#groupe", groupe),
                ("#classe", classe),
                ("#groupe_orig", groupe_orig),
                ("#classe_orig", classe_orig),
                ("#geom", ""),
            )
        )
        if attributs is not None:
            self.attributs.update(attributs)
        self.hdict = None
        self.multiples = dict()  # attributs multiples
        self.attributs_speciaux = dict()
        #        self.schema = schema # schema impose
        self.geomnatif = True
        self.erreurs = Erreurs()
        self.format_natif = format_natif
        self.virtuel = False
        self.schema = None
        if conversion == "virtuel":
            self.virtuel = True
            if schema:
                self.schema = schema
                schema.utilise = True
                schema.maxobj += 1
                self.initattr()  # dans un virtuel on initialise les attributs
        if not callable(conversion):
            conversion = noconversion
        if schema is not None:
            self.setschema(schema)
        self.attributs_geom = conversion
        #        self.virtuel = (conversion=='virtuel')
        self.casefold = lambda x: x

    def setorig(self, numero=None):
        """positionne l'identifiant d'origine pour les mappings"""
        self.idorig = self.ident
        if numero is not None:
            self.numobj = numero

    def forceorig(self, ident):
        """modifie l'identifiant d'origine pour les mappings"""
        self.idorig = ident

    def setnogeom(self, tmp=False):
        """annulle la geometrie"""
        self.attributs["#geom"] = ""
        #        erreurs_geom = self.geom_v.erreurs.getvals() if self.geom_v else ""
        self.geom_v = Geometrie()
        if tmp:  # operation temporaire on fait autre chose derriere
            return
        self.infogeom()

    def initgeom(self, force=False):
        """convertit la geometrie du format natif en interne"""
        # print ('initgeom ', self.ido, self.geom_v.valide, self.attributs_geom)
        if force or not self.geom_v.valide:
            if self.geom_v.unsync == -1:
                self.geom_v.shapesync()
            else:
                self.attributs_geom(self)
        # print("initgeom", self.geom_v)
        self.infogeom()
        return self.geom_v.valide

    def geompending(self, dimension=None):
        """invalide la geometrie pour signaler qu elle nest pas calculee"""
        self.geom_v.valide = False
        self.geom_v.sgeom = None
        self.geomnatif = True
        if dimension:
            self.geom_v.dim = dimension
        return True

    def infogeom(self):
        """positionne les attributss dependant de la geometrie"""
        geom_v = self.geom_v
        if geom_v.valide:
            self.attributs.update(
                [
                    ("#points", str(int(geom_v.npt))),
                    ("#type_geom", str(int(geom_v.type))),
                    ("#dimension", str(int(geom_v.dimension))),
                    ("#erreurs_geom", ""),
                ]
            )

        else:
            erreurs_geom = geom_v.erreurs.getvals() if geom_v else "geometrie invalide"
            self.attributs.update(
                [
                    # ("#longueur", ""),
                    ("#points", ""),
                    # ("#xmin", ""),
                    # ("#xmax", ""),
                    # ("#ymin", ""),
                    # ("#ymax", ""),
                    ("#type_geom", "0"),
                    ("#dimension", "0"),
                    ("#erreurs_geom", erreurs_geom),
                ]
            )

    def finalise_geom(
        self, type_geom=None, orientation="L", desordre=False, autocorrect=False
    ):
        """finalise la geometrie et renseigne les attributs"""
        self.geom_v.finalise_geom(
            type_geom=type_geom,
            orientation=orientation,
            desordre=desordre,
            autocorrect=autocorrect,
        )
        if not self.geom_v.valide:
            self.setnogeom(tmp=True)
        self.infogeom()
        return self.geom_v.valide

    def set_liste_att(self, liste_att):
        """positionne la liste des attributs a sortir"""
        self.liste_attributs = liste_att

    @property
    def type_geom(self):
        """recupere le type de geometrie de l'objet"""
        if self.geom_v.valide:
            return self.geom_v.type
        return self.attributs.get("#type_geom", "0")

    @property
    def dimension(self):
        """recupere le type de geometrie de l'objet"""
        if self.geom_v.valide:
            return int(self.geom_v.dimension)
        return int(self.attributs.get("#dimension", 0))

    def __repr__(self):
        """affichage basique de l'objet"""
        virtuel = "_v" if self.virtuel else ""
        return (
            "objet"
            + virtuel
            + str(self.ido)
            + ":clone"
            + str(self.copie)
            + " : "
            + str(sorted(self.attributs.items()))
        )

    @property
    def ident(self):
        """retourne l'identifiant de l'objet ( groupe, classe)."""
        return (self.attributs["#groupe"], self.attributs["#classe"])

    def setidentobj(self, ident, schema2=None):
        """force l'identifiant d'un objet"""
        self.attributs["#groupe"], self.attributs["#classe"] = ident
        if self.schema:
            if schema2 is None:
                schema2 = self.schema.schema
            schema_classe = schema2.get_classe(
                ident, cree=True, modele=self.schema, filiation=True
            )
            self.setschema(schema_classe)

    def __dict_if__(self, liste_attributs=None):
        """interface dictionnaire"""
        liste = (
            liste_attributs
            if liste_attributs
            else [i for i in self.attributs if i[0] != "#" and i != self.key]
        )
        if self.classe_is_att:
            liste.insert(0, "#classe")
        if not self.geom_v.valide:
            self.attributs_geom(self)
        geom = self.geom_v.__as_ewkt__
        attd = {i: self.attributs.get(i, "") for i in liste}
        print("dans dict_if", liste, attd, self.attributs)

        attd["#geom"] = geom
        return attd

    def __json_if__(self, liste_attributs=None):
        """interface geojson texte en sortie"""
        liste = (
            liste_attributs
            if liste_attributs
            else [i for i in self.attributs if i[0] != "#" and i != self.key]
        )
        if self.classe_is_att:
            liste.insert(0, "#classe")
        if not self.geom_v.valide:
            self.attributs_geom(self)
        geom = self.geom_v.__json_if__
        #        print ('jsonio recupere ',geom)
        return (
            '{"type": "Feature",'
            # + ('\n"id": "' + (str(self.attributs.get(self.key, self.ido))) + '",')
            # if self.key
            # else ""
            + '\n"properties": {\n'
            + json.dumps({i: str(self.attributs.get(i, "")) for i in liste})
            # + ",\n".join(
            #     [
            #         '"'
            #         + i
            #         + '": "'
            #         + self.attributs.get(i, "").replace('"', '\\"')
            #         + '"'
            #         for i in liste
            #     ]
            # )
            + "},\n"
            + (geom if geom else "")
            + "}\n"
        )

    def set_multi(self, point=False):
        """forcage multigeom"""
        if self.schema:
            self.schema.setmulti(point)
        self.geom_v.multi = True

    def __geo_interface__(self, liste_attributs):
        """interface geo_interface en sortie"""
        #        print ('demande geoif geom:',self.geom_v.type)
        blist = {
            0: False,
            "0": False,
            "false": False,
            False: False,
            "False": False,
            1: True,
            "1": True,
            "true": True,
            True: True,
            "True": True,
        }
        if not self.geom_v.valide:
            self.attributs_geom(self)
        use_noms_courts = False
        if self.schema:
            liste = self.schema.get_liste_attributs(sys=True)
            use_noms_courts = self.schema.use_noms_courts
            attributs = dict()
            sch = self.schema
            self.geom_v.type = sch.info["type_geom"]
            self.geom_v.multi = sch.multigeom
            # print ('obj:geo_interface',sch.identclasse,self.geom_v.type,self.geom_v.multi, len(self.geom_v.points))
            # print (self)
            for i in liste:
                if i in sch.attributs:
                    if sch.attributs[i].type_att.startswith("D"):
                        attributs[i] = (
                            self.attributs[i].replace("/", "-")
                            if self.attributs.get(i)
                            else None
                        )
                    elif sch.attributs[i].type_att == "B":
                        attributs[i] = blist.get(self.attributs.get(i))
                    else:
                        attributs[i] = self.attributs.get(i, "")
                #                    .replace(' ', 'T')'Z' if self.attributs.get(i) else None
                else:
                    attributs[i] = self.attributs.get(i, "")
        else:
            liste = (
                liste_attributs
                if liste_attributs
                else [i for i in self.attributs if not i.startswith("#")]
            )
            attributs = self.attributs
        if self.classe_is_att:
            liste.insert(0, "#classe")
        geom = self.geom_v.__geo_interface__
        if use_noms_courts:
            goif = {
                "id": attributs.get("#gid", str(self.ido)),
                "properties": {
                    self.casefold(self.schema.attributs[i].nom_court): (
                        attributs[i] if i in self.attributs else None
                    )
                    for i in liste
                },
                "geometry": geom,
            }
        else:
            goif = {
                "id": attributs.get("#gid", str(self.ido)),
                "properties": {
                    self.casefold(i): attributs[i] if i in attributs else None
                    for i in liste
                },
                "geometry": geom,
            }
        return goif

    def from_geo_interface(self, geoif):
        """geo_interface en entree"""
        #        print ('---------geo_interface',geoif)
        props = geoif.get("properties", {})
        if self.schema:
            if self.schema.attmap:
                # self.attributs.update(((self.schema.attmap.get(i,i),v) for i, v in props.items()))

                # print("traitement attmap", self.schema.attmap)
                for i, val in props.items():
                    if val is None:
                        continue
                    nom = self.schema.attmap.get(i, i)
                    try:
                        attdef = self.schema.attributs[nom]
                        # print ('recherche',i, 'trouve' , nom,attdef.format_entree)
                        if attdef.format_entree:
                            self.attributs[nom] = attdef.format_entree.format(
                                attdef.typeconv(val)
                            )
                        else:
                            self.attributs[nom] = str(val)
                    except KeyError:
                        print("recherche", i, " non trouve", nom)
                        self.attributs[nom] = str(val)
            else:
                for nom, val in props.items():
                    if val is None:
                        continue
                    try:
                        attdef = self.schema.attributs[nom]
                        # print ('recherche',i, 'trouve' , nom,attdef.format_entree)
                        if attdef.format_entree:
                            self.attributs[nom] = attdef.format_entree.format(
                                attdef.typeconv(val)
                            )
                        else:
                            self.attributs[nom] = str(val)
                    except KeyError:
                        self.attributs[nom] = str(val)
        else:
            self.attributs.update(
                {i: str(props[i]) for i in props if props[i] is not None}
            )
        self.geom_v.from_geo_interface(geoif.get("geometry", {}))
        self.infogeom()

    def debug(self, code, attlist=None, limit=True):
        """affichage de debug"""
        virtuel = "_v" if self.virtuel else ""
        fleche = (
            "----------------------> obj"
            if code in {"avant", "apres"}
            else "            obj"
        )
        invariant = (
            fleche
            + virtuel
            + " "
            + str(self.ido)
            + ": "
            + code
            + ":clone"
            + str(self.copie)
            + " "
            + str(self.attributs.get("#groupe"))
            + "."
            + str(self.attributs.get("#classe"))
        )
        schema = "\t" + repr(self.schema)
        # print ('attributs',self.attributs)
        aliste = sorted(self.attributs.keys()) if attlist is None else attlist

        attributs = str(
            [
                (
                    i,
                    (
                        (str(self.attributs[i])[:50] + "...")
                        if len(str(self.attributs.get(i, ""))) > 50
                        else self.attributs.get(i, "<non defini>")
                    ),
                )
                for i in aliste
            ]
            if limit
            else [(i, self.attributs.get(i, "<non defini>")) for i in aliste]
        )
        # LOGGER.debug("mode debug")
        LOGGER.debug("%s", invariant)
        if not attlist:
            LOGGER.debug("   schema:%s", schema)
        LOGGER.debug("   obj   :%s", attributs)
        if code == "apres":
            LOGGER.debug(" ==================================================== ")
        # print("schema", schema)
        # print(
        #     invariant + "\n",
        #     (schema + "\n\t") if not attlist else "",
        #     [
        #         (
        #             i,
        #             (str(self.attributs[i])[:50] + "...")
        #             if len(str(self.attributs.get(i, ""))) > 50
        #             else self.attributs.get(i, "<non defini>"),
        #         )
        #         for i in aliste
        #     ]
        #     if limit
        #     else [(i, self.attributs.get(i, "<non defini>")) for i in aliste],
        # )

    @property
    def attdict(self):
        """sort un dictionnaire ordonne des attributs"""
        if self.schema:
            liste = self.schema.get_liste_attributs(sys=True)
        else:
            liste = (
                self.liste_attributs
                if self.liste_attributs
                else [i for i in self.attributs if i[0] != "#"]
            )
        return collections.OrderedDict([(i, self.attributs.get(i, "")) for i in liste])

    def atget(self, nom, defaut=""):
        """conversion au mieux
        tous les attributs sont stockes en texte pour certains calculs
        il faut les convertir
        """
        val = self.attributs.get(nom, defaut)
        try:
            return int(val)
        except (ValueError, TypeError):
            try:
                return float(val)
            except (ValueError, TypeError):
                return str(val)

    def atget_n(self, nom, defaut=0.0):
        """conversion decimale"""
        try:
            return float(self.attributs[nom])
        except (ValueError, KeyError):
            return defaut

    def atget_c(self, nom, defaut=""):
        """conversion alpha"""
        return self.attributs.get(nom, defaut)

    def setschema(self, schemaclasse, remap=False):
        """affecte un schema de classe a l'objet et gere le comptage de references"""

        if self.schema is not None:
            if not self.virtuel:
                self.schema.objcnt -= 1
        self.schema = schemaclasse
        if schemaclasse is not None:
            if not self.virtuel:
                schemaclasse.objcnt += 1
                schemaclasse.maxobj += 1
                if schemaclasse.autopk:
                    schemaclasse.setautopk(self)
            schemaclasse.utilise = True
            self.attributs["#schema"] = schemaclasse.nomschema
        else:
            self.attributs["#schema"] = ""
        if remap:
            if self.schema.attmap is not None:
                self.attributs = {
                    self.schema.attmap.get(i, i): j for i, j in self.attributs.items()
                }
                self.attributs_speciaux = {
                    self.schema.attmap.get(i, i): j
                    for i, j in self.attributs_speciaux.items()
                }

    def mergeschema(self, schemaclasse, prefix=None):
        """ajoute des elements de schema"""
        if self.schema is None:
            self.setschema(schemaclasse)
            return
        for nom, att in list(schemaclasse.attributs.items()):
            nom = prefix + nom if prefix else nom
            self.schema.ajout_attribut_modele(att, nom=nom, force=True)
        # print("merge", self.schema)
        # print("avec", schemaclasse)

    def initattr(self):
        """initialise les attributs a leur valeur de defaut"""
        if not self.schema:
            return False
        for i in self.schema.get_liste_attributs(sys=True):
            self.attributs[i] = (
                self.schema.attributs[i].defaut
                if self.schema.attributs[i].defaut
                else ""
            )

    def setschema_auto(self, schema):
        """affecte un schema a l'objet en trouvant la classe et gere le comptage de references"""
        if schema is None:
            self.setschema(None)
        else:
            self.setschema(schema.setdefault_classe(self.ident))

    def ajuste_schema(self):
        """ajuste le schema de l'objet a la liste d attributs"""
        agarder = [i for i in self.attributs if not i.startswith("#")]
        if self.schema:
            self.schema.garder_attributs(agarder)

    def get_valeur(self, nom, defaut=""):
        """retourne un attribut par son nom"""
        if self.schema and nom in self.schema.attributs:
            conv = self.schema.attributs[nom].typeconv
        try:
            # print  ("conv",nom,self.attributs[nom],conv(self.attributs[nom]),type(conv(self.attributs[nom])))
            return conv(self.attributs[nom]) if nom in self.attributs else conv(defaut)
        except ValueError:
            if conv == int:
                try:
                    return int(float(self.attributs[nom]))
                except ValueError:
                    pass
            return ""

    def get_listeattval(self, liste, noms=False):
        """retourne une liste de valeurs selectionees"""
        if noms:
            return [str(i) + "=" + str(self.attributs.get(i, "")) for i in liste if i]
        return [str(self.attributs.get(i, "")) for i in liste if i]

    def get_dynlisteval(self, noms=False):
        """gestion des attributs en liste dynamique"""
        #        liste_entree = list(self.attributs.keys())
        if noms:
            return [a + "=" + b for a, b in self.attributs.items()]
        return list(self.attributs.values())

    def sethtext(self, nom, dic=None, upd=False):
        """convertit un dict en hstore et le range"""
        if dic is None:
            dic = self.hdict.get(nom) if self.hdict else None
            if not dic and isinstance(self.attributs.get(nom), dict):
                dic = self.attributs[nom]
        if self.hdict:
            if dic:
                if nom in self.hdict and upd:
                    self.hdict[nom].update(dic)
                else:
                    self.hdict[nom] = dict(dic)
        else:
            self.hdict = {nom: dict(dic)}
        res = ""
        if dic:
            res = ", ".join(
                [
                    " => ".join((i, dic[i].replace('"', r"\"")))
                    for i in sorted(dic.keys())
                ]
            )
        self.attributs[nom] = res
        return res

    def gethdict(self, nom, force=False):
        """stocke un hstore en dictionnaire et cree le
        dictionnaires de hstore s'il n'existe pas"""
        #    print("conversion hstore en dict", nom, obj.attributs.get(nom))
        if self.hdict is None:
            self.hdict = dict()
        if nom not in self.hdict or force:
            hstore = self.attributs.get(nom, "")

            if hstore:
                if isinstance(hstore, str):
                    vlist = hstore[1:-1].split('", "')
                    hddef = (i.replace(r"\"", '"').split('" => "', 1) for i in vlist)
                    self.hdict[nom] = dict(hddef)
                elif isinstance(hstore, dict):
                    self.hdict[nom] = dict(hstore)
                elif isinstance(hstore, collections.namedtuple):
                    self.hdict[nom] = hstore._asdict()
            else:
                self.hdict[nom] = dict()

        return self.hdict[nom]

    def setmultiple(self, nom, liste=[]):
        """stocke un attribut multiple"""
        self.multiples[nom] = liste
        self.attributs[nom] = str(liste)

    def resetschema(self):
        """supprime la reference a un schema"""
        if self.schema is not None:
            if not self.virtuel:
                self.schema.objcnt -= 1
        if "#schema" in self.attributs:
            del self.attributs["#schema"]
        self.schema = None

    def dupplique(self, schema=True):
        """retourne une copie de l'objet
        sert dans toutes les fonctions avec dupplication d'objets"""
        #        print ('dupplication objets',self.ident)
        old_sc = self.schema  # on traite le cas des schemas qui doivent rester un lien
        self.schema = None
        self.liste_attributs = None
        ob2 = copy.deepcopy(self)
        ob2.copie += 1
        ob2.ido = next(self._ido)
        self.schema = old_sc
        if schema:
            ob2.setschema(old_sc)
        #        ob2.schema = old_sc
        #        if old_sc is not None:
        #            old_sc.objcnt += 1 # on a un objet de plus dans le schema
        return ob2

    def ajout_erreur(self, nature):
        """strockage des erreurs de traitement"""
        self.erreurs.ajout_erreur(nature)

    def fold(self, classe, alist, geom=True, gsep="|"):
        """retourne un objet compact pour le stockage temporaire en general un namedtuple"""
        gfold = self.geom_v.fold()
        return classe([self.attributs.get(i) for i in alist] + [gfold])


def unfold(groupe, classe, folded, alist, geom=False, gsep="|"):
    """decompacte un objet"""
    obj = Objet(groupe, classe)
    obj.attributs.update(zip(alist, folded))
    return obj
