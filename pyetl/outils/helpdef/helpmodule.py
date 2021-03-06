# -*- coding: utf-8 -*-
"""
Created on Mon Aug  7 11:44:40 2017
module d'aide
@author: 89965
"""
# def get_help_texts(mapper):
#    '''analyse du code pour sortir les textes d'aide'''
#    return


def decription_pattern(pattern, description):
    """formatte la description des parametres d'entree"""
    patdef = pattern.split(";")
    patdesc = ";".join(description).split(";")
    retour = [
        "%+20s: %s" % (i, j + (" (optionnel)" if "?" in i else ""))
        for i, j in zip([i for i in patdef if i], patdesc)
    ]
    # print ('description',[i for i in patdef if i], patdesc,retour)
    return retour


def print_help(mapper, nom):
    """ affiche l'aide de base"""
    if nom:
        macro = mapper.getmacro(nom)
        debug = mapper.getvar("debug")
        if macro:
            print("%-15s: macro    (%s)" % (nom, macro.file))
            print("                   %s" % (macro.help[:-1]))
            if macro.help_detaillee:
                print()
                for i in macro.help_detaillee:
                    print("%16s   %s" % ("", i[:-1]))
                print()

            if macro.vpos:
                print("parametres: %s" % (";".join(macro.vpos)))
                for i in macro.vpos:
                    if i in macro.parametres_pos:
                        print("%-15s :%s" % (i, macro.parametres_pos[i]))

            if macro.vars_utilisees:
                print("variables utilisees")
                for i in macro.vars_utilisees:
                    print("%16s   %s" % ("", i[:-1]))

        elif nom in mapper.commandes:
            print("aide commande :", nom, debug, "\n")
            commande = mapper.commandes[nom]
            print("  %s" % (commande.description.get("#aide", [""])[0]))
            for i in commande.description.get("#aide_spec", []):
                print("   %s" % (i))
            print("")
            print("------- syntaxes acceptees ----------")
            print("")
            for variante in commande.subfonctions:
                pnum = variante.patternnum
                if variante.description:
                    print(
                        "%-20s: %s"
                        % (
                            variante.pattern,
                            variante.description.get("#aide_spec" + pnum, [""])[0],
                        )
                    )
                    for i in variante.description.get("#aide_spec" + pnum, [""])[1:]:
                        print("%-20s: %s" % ("", i))
                    for i in sorted(variante.description):
                        # if "#aide_spec" + pnum in i and i != "#aide_spec":
                        #     print("%-20s: %s" % ("", variante.description.get(i)[0]))
                        if "#parametres" + pnum in i and i != "#parametres":
                            print(
                                "\n".join(
                                    decription_pattern(
                                        variante.pattern,
                                        variante.description.get("#parametres" + pnum),
                                    )
                                )
                            )
                    if variante.description.get("#parametres"):
                        print(
                            "\n".join(
                                decription_pattern(
                                    variante.pattern,
                                    variante.description.get("#parametres"),
                                )
                            )
                        )
                    if variante.description.get("#variables"):
                        for i in variante.description.get("#variables", [""]):
                            print("%-20s: %s" % ("", i))
                            # print("%s" % "\n".join(variante.description.get("#parametres")))
                    if debug:
                        print("pattern", variante.pattern)
                        print("fonction", variante.work)
                        print("helper", variante.helper)
                        print("shelper", variante.shelper)
                        print("fsorties", tuple(i for i in variante.fonctions_sortie))

        elif nom == "selecteurs":
            print_aide_selecteurs(mapper)
        elif nom == "macros":
            print_aide_macros(mapper)
        elif nom == "commandes":
            print_aide_commandes(mapper)
        elif nom == "formats":
            print_aide_formats(mapper)
        elif nom:
            # essais de noms partiels
            trouve = False
            for n1 in mapper.getmacrolist():
                if nom in n1:
                    trouve = True
                    print_help(mapper, n1)
            for n1 in mapper.commandes:
                if nom in n1:
                    trouve = True
                    print_help(mapper, n1)
            if not trouve:
                print("aide: commande inconnue")
    else:
        print(
            "-------------------mapper version",
            mapper.version,
            "----------------------------",
        )
        print("                    aide générique")
        print("taper help commande pour l'aide détaillée sur une commande")
        print_aide_commandes(mapper)
        print_aide_selecteurs(mapper)
        print_aide_macros(mapper)


#    exit(0)
def print_aide_commandes(mapper):
    """affiche la aide des commandes """
    print("-----------------------------------------------------------------")
    print("---commandes standard--------------------------------------------")
    print("-----------------------------------------------------------------")
    for i in sorted(mapper.commandes):
        commande = mapper.commandes[i]
        print(
            "%-20s: %s"
            % (commande.nom, "\n".join(commande.description.get("#aide", [])))
        )


def print_aide_selecteurs(mapper):
    """affiche l'aide des selecteurs """
    print("-----------------------------------------------------------------")
    print("---selecteurs-----------------------------------------------")
    print("-----------------------------------------------------------------")
    for i in sorted(mapper.selecteurs):
        sel = mapper.selecteurs[i]
        print("%-20s: %s" % (i, "\n".join(sel.description.get("#aide", []))))


def print_aide_macros(mapper):
    """affiche l'aide des macros """
    print("-----------------------------------------------------------------")
    print("---macros internes-----------------------------------------------")
    print("-----------------------------------------------------------------")
    for nom_macro in sorted(mapper.getmacrolist()):
        print(
            "%-20s: %s"
            % (
                nom_macro,
                "\n".join(
                    [
                        i
                        for i in mapper.getmacro(nom_macro).help[:-1].split(";")
                        if i.strip()
                    ]
                ),
            )
        )


def print_aide_formats(mapper):
    """affiche l'aide des formats """
    print("-----------------------------------------------------------------")
    print("---formats connus------------------------------------------------")
    print("-----------------------------------------------------------------")
    print("nom-------------------lecture----ecriture------------------------")
    formats_connus = set(mapper.formats_connus_lecture.keys()) | set(
        mapper.formats_connus_ecriture.keys()
    )
    for nom_format in sorted(formats_connus):
        lect = "oui" if nom_format in mapper.formats_connus_lecture else "non"
        ecrit = "oui" if nom_format in mapper.formats_connus_ecriture else "non"
        print("%-20s:   %s    :   %s" % (nom_format, lect, ecrit))
