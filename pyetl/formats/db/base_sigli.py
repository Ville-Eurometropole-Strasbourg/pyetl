# -*- coding: utf-8 -*-
"""
Created on Mon Feb 22 11:49:29 2016

@author: 89965
acces a la base de donnees
"""

from time import strftime
from .base_postgis import PgsConnect, PgsGenSql

# from .init_sigli import requetes_sigli as REQS
# from . import database

SCHEMA_ADM = "admin_sigli"
TABLE_MONITORING = SCHEMA_ADM+'.stat_upload'

class SglConnect(PgsConnect):
    """connecteur de la base de donnees postgres"""
    fallback = PgsConnect.requetes


    def __init__(self, serveur, base, user, passwd, debug=0, system=False, params=None, code=None):
        super().__init__(serveur, base, user, passwd, debug, system, params, code)
        self.sys_cre = "date_creation"
        self.sys_mod = "date_maj"
        self.dialecte = "sigli"
        self.type_base = "sigli"
        self.schema_conf = SCHEMA_ADM
        # print ('init sigli', self.requetes)


    def spec_def_vues(self):
        """recupere des informations sur la structure des vues
           (pour la reproduction des schemas en sql"""
        requete = """SELECT nomschema,nomtable,definition,materialise
                     from """+SCHEMA_ADM+""".info_vues_utilisateur
                     """
        vues = dict()
        vues_mat = dict()
        for i in self.request(requete, ()):
            ident = (i[0], i[1])
            if i[3]:
                vues_mat[ident] = i[2]
            else:
                vues[ident] = i[2]

        #        print('sigli --------- selection info vues ', len(vues), len(vues_mat))
        return vues, vues_mat


class SglGenSql(PgsGenSql):
    """classe de generation des structures sql"""

    def __init__(self, connection=None, basic=False):
        super().__init__(connection=connection, basic=basic)
        self.geom = True
        self.courbes = False
        self.schemas = True

        self.dialecte = "sigli"
        self.defaut_schema = SCHEMA_ADM
        self.schema_conf = SCHEMA_ADM

    # scripts de creation de tables

    def db_cree_table(self, schema, ident):
        """creation d' une tables en direct """
        req = self.cree_tables(schema, ident)
        if self.connection:
            return self.connection.request(req, ())

    def db_cree_tables(self, schema, liste):
        """creation d'une liste de tables en direct"""
        if not liste:
            liste = [i for i in self.schema.classes if self.schema.classes[i].a_sortir]
        for ident in liste:
            self.db_cree_table(schema, ident)

    # structures specifiques pour stocker les scrips en base
    # cree 4 tables: Macros scripts batchs logs

    def init_pyetl_script(self, nom_schema):
        """ cree les structures standard"""
        pass

    @staticmethod
    def _commande_reinit(niveau, classe, delete):
        """commande de reinitialisation de la table"""
        #        prefix = 'TRUNCATE TABLE "'+niveau.lower()+'"."'+classe.lower()+'";\n'

        if delete:
            return 'DELETE FROM "' + niveau.lower() + '"."' + classe.lower() + '";\n'
        return (
            "SELECT "+SCHEMA_ADM+".truncate_table('"
            + niveau.lower()
            + "','"
            + classe.lower()
            + "');\n"
        )

    @staticmethod
    def _commande_sequence(niveau, classe):
        """ cree une commande de reinitialisation des sequences"""
        return (
            "SELECT "+SCHEMA_ADM+".ajuste_sequence('"
            + niveau.lower()
            + "','"
            + classe.lower()
            + "');\n"
        )

    @staticmethod
    def _commande_trigger(niveau, classe, valide):
        """ cree une commande de reinitialisation des sequences"""
        if valide:
            return (
                "SELECT "+SCHEMA_ADM+".valide_triggers('"
                + niveau.lower()
                + "','"
                + classe.lower()
                + "');\n"
            )
        return (
            "SELECT "+SCHEMA_ADM+".devalide_triggers('"
            + niveau.lower()
            + "','"
            + classe.lower()
            + "');\n"
        )

    @staticmethod
    def _commande_monitoring(niveau, classe, schema, mode):
        """ insere une ligne dans une table de stats"""
        return ('INSERT INTO '+TABLE_MONITORING+ " (nomschema, nomtable, nbvals, mode, nom_script, date_export)"+
                "VALUES('%s','%s','%s','%s','%s',%s)"%
            ( niveau.lower(),
            classe.lower(),
            str(schema.getinfo('objcnt')) if schema else '0',
            mode,
            schema.getinfo('script_ref') if schema else '',
            strftime('%Y-%m-%d %H:%M:%S'),
            ))



    def cree_triggers(self, classe, groupe, nom):
        """ cree les triggers """
        evs = {"B": "BEFORE ", "A": "AFTER ", "I": "INSTEAD OF"}
        evs2 = {"I": "INSERT ", "D": "DELETE ", "U": "UPDATE ", "T": "TRUNCATE"}
        ttype = {"T": "TRIGGER","C": "CONSTRAINT"}
        decl = {'R': "ROW", 'S':"STATEMENT"}
        table = groupe + "." + nom
        if self.basic:
            return []
        trig = ["-- ###### definition des triggers ####"]
        if self.maj:
            atts = {i.lower() for i in classe.get_liste_attributs()}
            trig_std = "auteur" in atts and "date_maj" in atts
            #       for i in atts:
            #           if i.defaut[0:1]=='A:': # definition d'un trigger
            #               liste_triggers[i.nom]=i.defaut[2:]
            if trig_std:
                trig.append("CREATE TRIGGER tr_auteur")
                trig.append("\tBEFORE UPDATE")
                trig.append("\tON " + table)
                trig.append("\tFOR EACH ROW")
                trig.append("\tEXECUTE PROCEDURE "+SCHEMA_ADM+".auteur();")
        liste_triggers = classe.triggers
        for i in liste_triggers:
            type_trigger, action, declencheur, timing, event,colonnes,condition,sql = liste_triggers[i].split(',')
            trigdef=(ttype[type_trigger],action,decl[declencheur],evs[timing], evs2[event], colonnes,condition,sql)
            idfonc,trigsql = self.cree_sql_trigger(i, table, trigdef)
            trig.extend(trigsql)
        return trig



DBDEF = {"sigli": (SglConnect, SglGenSql, "server", "", "#ewkt", "base postgis avec "+SCHEMA_ADM)}
