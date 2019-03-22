# -*- coding: utf-8 -*-
"""
Created on Fri Mar  1 10:14:31 2019

@author: 89965

gestionaire de formats de traitements
les formats sont enregistres en les mettant dans des fichiers python qui
commencent par format_

"""
from types import MethodType

# from functools import partial
from .db import DATABASES
from .fichiers import READERS, WRITERS
from .geometrie import GEOMDEF
from .interne.objet import Objet

#
# geomdef = namedtuple("geomdef", ("writer", "converter"))
#
# rdef = namedtuple("reader", ("reader", "geom", "has_schema", "auxfiles", "converter"))
# wdef = namedtuple("writer", ("writer", "streamer",  "force_schema", "casse",
#                                 "attlen", "driver", "fanout", "geom", "tmp_geom",
#                                 "geomwriter"))
# "database", ("acces", "gensql", "svtyp", "fileext", 'description', "geom", 'converter',
#             "geomwriter"))
#
# assemblage avec les geometries
for nom in WRITERS:
    tmp = WRITERS[nom]
    if tmp.geom:
        WRITERS[nom] = tmp._replace(geomwriter=GEOMDEF[tmp.geom].writer)
#    print ('writer', nom , 'geom', WRITERS[nom].geom, WRITERS[nom].geomwriter)

for nom in READERS:
    tmp = READERS[nom]
    if tmp.geom:
        READERS[nom] = tmp._replace(converter=GEOMDEF[tmp.geom].converter)

for nom in DATABASES:
    tmp = DATABASES[nom]
    if tmp.geom:
        DATABASES[nom] = tmp._replace(
            converter=GEOMDEF[tmp.geom].converter, geomwriter=GEOMDEF[tmp.geom].writer
        )


class Reader(object):
    """wrappers d'entree génériques"""

    databases = DATABASES
    lecteurs = READERS
    geomdef = GEOMDEF

    @staticmethod
    def get_formats():
        """retourne la liste des formata connus"""
        return Reader.lecteurs

    #    auxiliaires = AUXILIAIRES
    #    auxiliaires = {a:AUXILIAIRES.get(a) for a in LECTEURS}

    def __init__(self, nom, regle, regle_start, debug=0):
        self.nom_format = nom
        self.debug = debug
        self.regle = regle  # on separe la regle de lecture de la regle de demarrage
        self.regle_start = regle_start
        self.regle_ref = self.regle if regle is not None else self.regle_start
        stock_param = regle_start.stock_param
        self.traite_objets = stock_param.moteur.traite_objet
        self.set_format_entree(nom)
        self.nb_lus = 0
        #        self.lire_objets = None
        self.groupe = ""
        self.classe = ""
        self.schema_entree = None
        if self.debug:
            print("debug:format: instance de reader ", nom, self)

    def set_format_entree(self, nom):
        """#positionne un format d'entree"""
        nom = nom.replace(".", "").lower()
        if nom in self.lecteurs:
            #            lire, converter, cree_schema, auxiliaires = self.lecteurs[nom]
            description = self.lecteurs[nom]
            self.description = description
            self.format_natif = description.geom
            self.lire_objets = MethodType(description.reader, self)
            self.nom_format = nom
            self.cree_schema = description.has_schema
            self.auxiliaires = description.auxfiles
            self.converter = description.converter
            self.schema_entree = self.regle_ref.getvar("schema_entree")
            if self.debug:
                print(
                    "debug:format: lecture format " + nom,
                    self.converter,
                    self.lire_objets,
                )
        else:
            print("error:format: format entree inconnu", nom)
            raise KeyError

    def get_info(self):
        """ affichage du format courant : debug """
        print("info :format: format courant :", self.nom_format)

    def get_converter(self, format_natif=None):
        """retourne la fonction de conversion geometrique"""
        if format_natif is None:
            return self.converter
        fgeom = Reader.lecteurs.get(format_natif, Reader.lecteurs["interne"]).geom
        return Reader.geomdef[fgeom].converter

    def setident(self, groupe, classe):
        """positionne les identifiants"""
        self.groupe = groupe
        self.classe = classe

    def getobj(self, niveau=None, classe=None):  # cree un objet
        """retourne un objet neuf a envoyer dans le circuit"""
        self.nb_lus += 1
        return Objet(
            niveau or self.groupe,
            classe or self.classe,
            format_natif=self.format_natif,
            conversion=self.converter,
        )


class Writer(object):
    """wrappers de sortie génériques"""

    databases = DATABASES
    sorties = WRITERS
    geomdef = GEOMDEF

    def __init__(self, nom, regle, debug=0):
        #        print ('dans writer', nom)

        self.dialecte = None
        destination = ""
        dialecte = ""
        if ":" in nom:
            defs = nom.split(":")
            #            print ('decoupage writer', nom, defs,nom.split(':'))
            nom = defs[0]
            dialecte = defs[1]
            destination = defs[2] if len(defs) > 2 else ""
            fich = defs[3] if len(defs) > 3 else ""
        self.nom_format = nom
        #        self.destination = destination
        self.regle = regle
        self.debug = debug
        self.writerparms = dict()  # parametres specifique au format
        """#positionne un format de sortie"""
        nom = nom.replace(".", "").lower()
        if nom in self.sorties:
            self.def_sortie = self.sorties[nom]
        #            ecrire, stream, tmpgeo, schema, casse, taille, driver, fanoutmax,\
        #            nom_format = self.sorties[nom]
        else:
            print("format sortie inconnu '" + nom + "'", self.sorties.keys())
            self.def_sortie = self.sorties["#poubelle"]

        #            ecrire, stream, tmpgeo, schema, casse, taille, driver, fanoutmax, nom_format =\
        #                    self.sorties['#poubelle']
        if nom == "sql":

            if dialecte == "":
                dialecte = "natif"
            else:
                dialecte = dialecte if dialecte in self.databases else "sql"
                self.writerparms["dialecte"] = self.databases[dialecte]
                self.writerparms["base_dest"] = destination
                self.writerparms["destination"] = fich
        else:
            self.writerparms["destination"] = destination
        self.dialecte = dialecte
        #        self.conv_geom = self.geomdef[self.def_sortie.geom].converter
        self.ecrire_objets = MethodType(self.def_sortie.writer, self)
        #        self.ecrire_objets = self.def_sortie.writer
        self.ecrire_objets_stream = MethodType(self.def_sortie.streamer, self)
        #        self.ecrire_objets_stream = self.def_sortie.streamer
        self.tmp_geom = self.def_sortie.tmp_geom
        self.nom_fgeo = self.def_sortie.geom
        self.geomwriter = self.def_sortie.geomwriter
        self.calcule_schema = self.def_sortie.force_schema
        self.minmaj = (
            self.def_sortie.casse
        )  # determine si les attributs passent en min ou en maj
        self.driver = self.def_sortie.driver
        self.nom = nom
        self.l_max = self.def_sortie.attlen
        self.ext = "." + nom
        self.multiclasse = self.def_sortie.fanout != "classe"
        self.fanoutmax = self.def_sortie.fanout
        self.schema_sortie = self.regle.getvar("schema_entree")

    #        print('writer : positionnement dialecte',nom, self.nom_format, self.writerparms)

    def get_info(self):
        """ affichage du format courant : debug """
        print("error:format: format courant :", self.nom_format)

    def get_geomwriter(self, format_natif=None):
        """retourne la fonction de conversion geometrique"""
        if format_natif is None:
            return self.geomdef[self.nom].writer
        fgeom = self.sorties.get(format_natif, Writer.sorties["interne"]).geom
        return self.geomdef[fgeom].writer
