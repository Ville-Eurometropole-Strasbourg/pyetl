# -*- coding: utf-8 -*-
"""
Created on Fri Dec 11 14:34:04 2015

@author: 89965
fonctions traitement xml
"""
import logging
import os
import io
import time
import re
from xml.etree.ElementTree import ParseError
import xml.etree.cElementTree as ET

# def importer():
#     global ET, ParseError
#     from xml.etree.ElementTree import ParseError
#     import xml.etree.cElementTree as ET


# from lxml import etree as ET

LOGGER = logging.getLogger(__name__)


def h_xmlextract(regle):
    """extraction d'element xml"""
    # importer()

    regle.cadre = regle.params.cmp2.val
    regle.recherche = regle.params.cmp1.val
    regle.partiel = None
    if "*" in regle.params.cmp1.val:
        regle.recherche = None
        regle.partiel = regle.params.cmp1.val.replace("*", "")
    regle.item = regle.params.cmp1.definition[0] if regle.params.cmp1.definition else ""
    regle.keepdata = regle.istrue("xml_keepdata")
    regle.keeptree = regle.istrue("xml_keeptree")
    regle.noprefix = regle.istrue("xml_noprefix")


def getcadre(regle, obj):
    """gestion de la persistance de structure xml"""
    tree = obj.attributs_speciaux.pop("__xmltree", None)
    cadres = ()

    if not tree:
        if regle.noprefix:
            xml = re.sub("(</?)[A-Za-z0-9]*:", "\g<1>", regle.entree)
        else:
            xml = regle.entree
        if xml:
            try:
                tree = ET.fromstring(xml)
            except ParseError as err:
                # print("erreur xml mal formé", err, regle.entree)
                LOGGER.error("erreur xml mal formé %s : %s", repr(err), xml)
                return None, ()
        else:
            return None, ()
    cadres = tree.iter(regle.cadre) if regle.cadre else [tree]
    return tree, cadres


def writeback(regle, obj, tree, nomxml, changed=False):
    changed = changed or obj.attributs_speciaux.pop("__xmlchanged", None)
    if regle.keeptree:
        obj.attributs_speciaux["__xmltree"] = tree
        obj.attributs_speciaux["__xmlchanged"] = changed
        return

    if changed:
        if not tree:
            tree = obj.attributs_speciaux.get("__xmltree")
        obj.attributs[nomxml] = ET.tostring(tree, encoding="unicode") if tree else ""


def f_xmlextract(regle, obj):
    """#aide||extraction de valeurs d un xml
      #aide_spec||retourne le premier element trouve qui correspond aux criteres
      #aide_spec1||sort tous les parametres sous forme d'un hstore
      #aide_spec2||sort tous les parametres sous forme d'un dictionnaire
      #aide_spec1||sort le parametre sezlectionne sous forme d'un attribut
       #pattern1||H;?C;A;xmlextract;C;?C||sortie
       #pattern2||D;?C;A;xmlextract;C;?C||sortie
       #pattern3||S;?C;A;xmlextract;A.C;?C||sortie
    #parametres1||attribut sortie(hstore);defaut;attribut xml;;tag a extraire;groupe de recherche
    #parametres2||attribut sortie(dictionnaire);defaut;attribut xml;;tag a extraire;groupe de recherche
    #parametres3||attribut sortie;defaut;attribut xml;;element a extraire sous forme tag.attribut ou tag.#text;groupe de recherche
          #test1||obj||^V4;<g><pp p1="toto" p2="titi"/></g>;;set||^H:XX;;V4;xmlextract;pp;||ath;XX;p2;titi
          #test2||obj||^V4;<g><pp p1="toto" p2="titi"/></g>;;set||^*;;V4;xmlextract;pp;||atv;p2;titi
          #test3||obj||^V4;<g><pp p1="toto" p2="titi"/></g>;;set||^XX;;V4;xmlextract;pp.p1;||atv;XX;toto
          #test3||obj||^V4;<g><pp p1="toto" p2="titi">text</pp></g>;;set||^XX;;V4;xmlextract;pp.#text;||atv;XX;text
    """
    trouve = False
    tree, cadres = getcadre(regle, obj)
    for cadre in cadres:
        for elem in cadre.iter(regle.recherche):
            if (
                regle.recherche is None
                and regle.partiel
                and not regle.partiel in elem.tag
            ):
                continue
            if regle.item == "#text":
                contenu = elem.text
            else:
                contenu = elem.get(regle.item, "") if regle.item else dict(elem.items())
            regle.setval_sortie(obj, contenu)
            writeback(regle, obj, tree, regle.params.att_entree.val, changed=False)
            return True
    writeback(regle, obj, tree, regle.params.att_entree.val, changed=False)
    return trouve


def h_xmlsplit(regle):
    """helper decoupage"""
    h_xmlextract(regle)
    # regle.reader = regle.stock_param.getreader("interne", regle)
    regle.changeschema = False


def f_xmlsplit(regle, obj):
    """#aide||decoupage d'un attribut xml en objets
      #aide_spec||on cree un objet pour chaque element
       #pattern1||S;;A;xmlsplit;C;?C||sortie
       #pattern2||H;;A;xmlsplit;C;?C||sortie
       #pattern3||D;;A;xmlsplit;C;?C||sortie
       #pattern4||M;;A;xmlsplit;C;?C||sortie
       #pattern5||S;;A;xmlsplit;A.C;?C||sortie
    #parametres1||attribut sortie(hstore);defaut;attribut xml;;tag a extraire;groupe de recherche
          #test1||obj||^V4;<g><pp p1="toto"/><pp p1="titi"/></g>;;set||^X;;V4;xmlsplit;pp;;||#xmltag;pp;;;;;;pass-;;;||cnt;2
         #test1b||obj||^V4;<g><pp p1="titi"/></g>;;set||^H:X;;V4;xmlsplit;pp;||#xmltag;pp;;;;;;pass-;;||ath;X;p1;titi
    """
    trouve = False
    tree, cadres = getcadre(regle, obj)
    # groupe, oclasse = obj.ident
    # nat = regle.params.att_entree.val
    # if nat.startswith("#"):
    #     nat = nat[1:]
    # classe = oclasse + "_" + nat
    # regle.reader.prepare_lecture_att(obj, "interne")
    if regle.keepdata:  # on actualise l xml
        writeback(regle, obj, tree, regle.params.att_entree.val, changed=False)
    else:  # on evite du duppliquer des gros xml
        xml = obj.attributs.get(regle.params.att_entree.val, "")
        obj.attributs[regle.params.att_entree.val] = ""
    for cadre in cadres:
        cadretags = dict(cadre.items())
        # print("traitement", cadre, regle.recherche)
        for elem in cadre.iter(regle.recherche):
            if (
                regle.recherche is None
                and regle.partiel
                and not regle.partiel in elem.tag
            ):
                continue
            # obj2 = regle.reader.getobj(niveau=groupe, classe=classe)
            obj2 = obj.dupplique()
            obj2.schema = obj.schema
            obj2.virtuel = False
            if regle.params.pattern == "1":
                contenu = ET.tostring(elem, encoding="unicode")
                # print("creation ", contenu)
            elif regle.params.pattern in "234":
                contenu = dict(elem.items())
                # print ("trouve elem", contenu)

            elif regle.item:
                contenu = elem.get(regle.item, "")
                if contenu is None:
                    contenu = ""
            else:
                contenu = ""
            regle.setval_sortie(obj2, contenu)
            if obj2.schema and regle.action_schema:
                regle.action_schema(regle, obj2)
            obj2.attributs["#xmltag"] = regle.recherche or regle.partiel or elem.tag
            obj2.attributs["#xmlgroup"] = regle.cadre
            obj2.sethtext(nom="#xmlgrouptags", dic=cadretags, upd=False)
            # obj2.attributs["#xmlgrouptags"] = cadretags
            # print("xmlsplit traitement", obj2)
            regle.stock_param.moteur.traite_objet(obj2, regle.branchements.brch["gen"])
            trouve = True
    if not regle.keepdata:
        obj.attributs[regle.params.att_entree.val] = xml
    writeback(regle, obj, tree, regle.params.att_entree.val, changed=False)
    return trouve


def f_xmlstruct(regle, obj):
    """#aide||affiche la structure de tags d un xml
       #pattern1||;?C;A;xmlstruct;?C;?C
       #helper||xmlsplit
    #parametres1||;defaut;attribut xml;;tag a extraire;groupe de recherche
    """
    trouve = False
    tree, cadres = getcadre(regle, obj)
    if regle.keepdata:  # on actualise l xml
        writeback(regle, obj, tree, regle.params.att_entree.val, changed=False)
    for cadre in cadres:
        for elem in cadre.iter(None):
            if (
                regle.recherche is None
                and regle.partiel
                and not regle.partiel in elem.tag
            ):
                continue
            print("trouve elem", elem.tag)
            trouve = True
    return True


def h_xmledit(regle):
    """helper edition"""
    h_xmlextract(regle)
    if regle.params.pattern == 1:
        regle.reselect = re.compile(regle.params.att_sortie.val)
    # regle.reader = regle.stock_param.getreader("interne", regle)
    regle.changeschema = False


def f_xmledit(regle, obj):
    """#aide||modification en place d elements xml
       #pattern1||re;re;A;xmledit;C;?C||sortie
       #pattern2||;C;A;xmledit;A.C;?C||cmp1
       #!pattern3||;[A];A;xmledit;A.C;?C||cmp1
       #pattern4||?=\\*;H;A;xmledit;C;?C||defaut
       #pattern5||;;A;xmledit;A.C;?C||defaut
     #aide_spec1||remplacement de texte
    #parametres1||expression de sortie;selection;attribut xml;xmledit;tag a modifier;groupe de recherche
     #aide_spec2||remplacement ou ajout d un tag
    #parametres2||;valeur;attribut xml;xmledit;tag a modifier.parametre;groupe de recherche
     #!aide_spec3||remplacement ou ajout d un tags
    #!parametres3||;attribut contenant la valeur;attribut xml;xmledit;tag a modifier.parametre;groupe de recherche
     #aide_spec4||remplacement ou ajout d un en: remplacement total;attribut hstore contenant clefs/valeurs;attribut xml;xmledit;tag a modifier;groupe de recherche
     #aide_spec5||suppression d un ensemble de tags
    #parametres5||;liste de clefs a supprimer;attribut xml;xmledit;tag a modifier;groupe de recherche
          #test1||obj||^V4;<g><pp p1="toto" p2="titi">essai</pp></g>;;set||^xx;ss;V4;xmledit;pp;||^XX;;V4;xmlextract;pp.#text;||atv;XX;exxai
          #test2||obj||^V4;<g><pp p1="toto" p2="titi"/></g>;;set||^;tutu;V4;xmledit;pp.p1;||^XX;;V4;xmlextract;pp.p1;||atv;XX;tutu
          #test5||obj||^V4;<g><pp p1="toto" p2="titi"/></g>;;set||^;;V4;xmledit;pp.p1;||^XX;;V4;xmlextract;pp.p1;||atv;XX;
    """
    tree, cadres = getcadre(regle, obj)
    groupe, oclasse = obj.ident
    nat = regle.params.att_entree.val
    if nat.startswith("#"):
        nat = nat[1:]
    classe = oclasse + "_" + nat
    # regle.reader.prepare_lecture_att(obj, "interne")
    # print("xmledit", regle.params.pattern)
    trouve = 0
    for cadre in cadres:
        # print("traitement", cadre)
        for elem in cadre.iter(regle.recherche):
            if (
                regle.recherche is None
                and regle.partiel
                and not regle.partiel in elem.tag
            ):
                continue
            trouve = 1
            if regle.params.pattern == "1":  # regex sur texte
                contenu = elem.text
                # print("xmledit avant", contenu)
                contenu = re.sub(
                    regle.params.val_entree.val, regle.params.att_sortie.val, contenu
                )
                # print("xmledit apres", contenu)
                elem.text = contenu
            elif regle.params.pattern == "2":
                # print("set tag", regle.item, regle.params.val_entree.val)
                elem.set(regle.item, regle.params.val_entree.val)
            # elif regle.params.pattern == "3":
            #     # print("set tag", regle.item, regle.params.val_entree.val)
            #     elem.set(regle.item, obj.attributs[regle.params.val_entree.val])
            elif regle.params.pattern == "4":
                vals = obj.gethdict(regle.params.val_entree.val)
                for i, j in vals.items():
                    elem.set(i, j)
            elif regle.params.pattern == "5":
                elem.attrib.pop(regle.item, None)
    writeback(regle, obj, tree, regle.params.att_entree.val, changed=True)
    return trouve


def f_xmlload(regle, obj):
    """#aide||lecture d un fichier xml dans un attribut
       #pattern1||A;?;?A;xml_load;;;
    #parametres1||attribut de sortie;defaut;attribut contenant le nom de fichier;
    """
    nom = regle.entree
    # print("xmlload traitement ", nom)
    try:
        obj.attributs[regle.params.att_sortie.val] = "".join(
            open(nom, "r", encoding="utf-8").readlines()
        )
        # print(
        #     " xmlload",
        #     regle.params.att_sortie.val,
        #     len(obj.attributs[regle.params.att_sortie.val]),
        # )
    except (FileNotFoundError, PermissionError):
        obj.attributs[regle.params.att_sortie.val] = ""
        LOGGER.warning("fichier non trouve %s", nom)
        # print("fichier non trouve", nom)
        return False
    return True


def h_xmlsave(regle):
    """helper sauvegarde"""
    regle.keeptree = False


def f_xmlsave(regle, obj):
    """#aide||stockage dans un fichier d un xml contenu dans un attribut
       #pattern1||A;?C;A;xml_save;?C;;
    #parametres1||nom fichier;;attribut contenant le xml;;nom du repertoire
    """
    writeback(regle, obj, None, regle.params.att_entree.val, changed=False)
    sortie = obj.attributs.get(regle.params.att_sortie.val)
    rep = regle.params.cmp1.val
    if rep:
        sortie = os.path.join(rep, sortie)
    os.makedirs(os.path.dirname(sortie), exist_ok=True)
    # print("ecriture xml", sortie)
    try:
        open(sortie, "w", encoding="utf-8").write(regle.entree)
    except (FileNotFoundError, PermissionError):
        LOGGER.error("ecriture impossible %s", sortie)
        # print("ecriture impossible", sortie)
        return False
    return True


def load_templates(regle, templatedir):
    """precharge les templates"""
    from jinja2 import FileSystemLoader, Environment

    if os.path.isdir(templatedir):
        templatename = ""
    elif os.path.isfile(templatedir):
        templatename = os.path.basename(templatedir)
        templatedir = os.path.dirname(templatedir)
    else:
        raise FileNotFoundError

    loader = FileSystemLoader(templatedir)
    variables = regle.context.getvars()
    envir = Environment(loader=loader)
    envir.globals.update(variables)
    regle.envir = envir
    regle.templates = dict()
    regle.templatename = templatename
    if templatename:
        regle.templates[templatename] = envir.get_template(templatename)


def h_formated_save(regle):
    """precharge les templates"""
    templatedef = (
        os.path.join(regle.params.cmp1.val, regle.params.val_entree.val)
        if regle.params.att_entree.val == ""
        else regle.params.cmp1.val
    )
    load_templates(regle, templatedef)
    regle.destdir = ""
    if regle.params.pattern == "2":
        destdir = os.path.join(regle.getvar("_sortie"), regle.params.cmp2.val)
        os.makedirs(destdir, exist_ok=True)
        regle.destdir = destdir


def f_formated_save(regle, obj):
    """#aide||stockage de l objet dans un fichier ou un attribut en utilisant un template jinja2
       #pattern1||A;C?;?A;formated_save;C;;
       #pattern2||[A];C?;?A;formated_save;C;?C;
    #parametres1||attribut;defaut;attribut nom du template;;repertoire de template;
    #parametres2||nom fichier;defaut;attribut nom du template;;repertoire de template;repertoire de sortie
    """

    templatename = regle.templatename or regle.entree
    if templatename not in regle.templates:
        regle.templates[templatename] = regle.envir.get_template(templatename)
    template = regle.templates[templatename]
    sortie = template.render(obj.attributs)
    # print("xml en sortie", sortie)
    if regle.params.pattern == "2":
        destname = obj.attributs.get(regle.params.att_sortie.val)
        subdir = os.path.dirname(destname)
        if subdir:
            destdir = os.path.join(regle.destdir, subdir)
            os.makedirs(destdir, exist_ok=True)
        dest = os.path.join(regle.destdir, destname)
        # print("ecriture sortie xml", dest)
        with open(dest, "w", encoding="utf-8") as fich:
            fich.write(sortie)
        return True
    else:
        obj.attributs[regle.params.att_sortie.val] = sortie
