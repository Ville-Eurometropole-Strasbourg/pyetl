# -*- coding: utf-8 -*-
"""creation d ihm poweshell a partir d un fichier de definition"""
from encodings import utf_8
import itertools
import os


def usewebservice(ihm, ligne):
    if "@@" in ligne:  # appel serviceweb
        tmp = ligne.split("@@")
        wdef = tmp[1]
        nom_service, *_ = wdef.split("/")
        uri = ihm.weblinks[nom_service] + wdef
        tmp[1] = "(invoke-WebRequest -Uri '" + uri + "'|convertfrom-Json)"
        retour = "".join(tmp)
        return retour
    return ligne


class Ihm(object):
    def __init__(self, nom=None, interpreteur=None):
        self.nom = nom if nom else "ihm"
        self.id = "ihm"
        self.main = None
        self.elements = []
        self.weblinks = dict()
        self.startserver = False
        self.variables = dict()

    @property
    def colonnes(self):
        return self.main.colonnes

    @property
    def lignes(self):
        return self.main.lignes

    def genps(self, variables):
        """genere le code ps pour l´ihm"""
        self.variables = variables
        nbcols = self.colonnes
        nblignes = self.lignes
        self.lcols = int((self.main.largeur - 40) / nbcols)
        self.hlin = 60

        code = [
            "# genere automatiquement par le generateur d ihm de mapper",
            "",
            "",
            "Add-Type -AssemblyName System.Windows.Forms",
            "[System.Windows.Forms.Application]::EnableVisualStyles()",
            "$font=New-Object System.Drawing.Font('Microsoft Sans Serif',10)",
            "$startx=20",
            "$scriptdir=",
        ]
        if self.startserver:
            # on verifie si le serveur existe
            code.append('$jobs=get-job -Command "mapper_web*"')
            code.append("if (!$jobs) {start-job -ScriptBlock {mapper_web}}")
            # on demarre le serveur web

        code.extend(self.main.genps(self))
        for el in self.elements:
            code.extend(el.genps(self))
        return code

    def struct(self):
        """affiche la structure de l ihm avec les imbrications"""
        print("ihm ", self.nom)
        self.main.struct(1)
        for el in self.elements:
            el.struct(1)


class Fenetre(object):
    _ido = itertools.count(1)

    def __init__(self, parent, titre, largeur=None) -> None:
        self.id = "Form" + str(next(self._ido))
        self.parent = parent
        self.largeur = largeur
        self.hauteur = 0
        self.hlines = dict()
        self.messages = None
        self.titre = titre
        self.elements = []
        self.statusbar = None
        self.variables = parent.variables

    def sethline(self, ligne, hauteur):
        self.hlines[ligne] = max(self.hlines.get(ligne, 1), hauteur)
        return self.hlines[ligne]

    @property
    def colonnes(self):
        return max((i.colonne for i in self.elements))

    @property
    def lignes(self):
        maxlin = 0
        cour = 0
        next = 1
        for i in self.elements:
            print(type(i), "ligne", i.ligne)
            if i.ligne == "+":
                cour += next
                i.ligne = cour
                next = self.sethline(cour, i.hauteur)
            elif isinstance(i.ligne, int) or i.ligne.isnumeric():
                cour = int(i.ligne)
                next = self.sethline(cour, i.hauteur)
                i.ligne = cour
            elif i.ligne == "=":
                cour = cour if cour else 1
                i.ligne = cour
        maxlin = max(maxlin, cour)
        next = self.sethline(cour, i.hauteur)
        if self.statusbar:
            maxlin += 1
        maxlin += next - 1
        print("lignes de l ihm", len(self.elements), maxlin)
        return maxlin

    def genps(self, ihm):
        self.lcols = int((self.largeur - 40) / (self.colonnes))
        self.hlin = 40
        vref = "$" + self.id
        code = [
            vref + " = New-Object system.Windows.Forms.Form",
            vref
            + ".ClientSize  = New-Object System.Drawing.Point(%d,%d)"
            % (self.largeur, (self.lignes + 2) * self.hlin),
            vref + '.text  = "%s"' % (self.titre,),
            vref + ".TopMost  = $false",
            "",
        ]

        vlist = []
        for el in self.elements:
            vslist, vbcode = el.genps(ihm)
            code.extend(vbcode)
            vlist.extend(vslist)

        if self.statusbar:
            statusbar = Statusbar(self, self.lignes, 1, "")
            vslist, scode = statusbar.genps(ihm)
            code.extend(scode)
            vlist.extend(vslist)

        code.append(vref + ".controls.AddRange(@(" + ",".join(vlist) + "))")
        code.append(vref + ".ShowDialog()")
        return code

    def struct(self, niveau):
        """affiche la structure de l ihm avec les imbrications"""
        print(
            "    " * niveau, self.id, "fenetre ", self.titre, "(", self.parent.id, ")"
        )
        for el in self.elements:
            el.struct(niveau + 1)


class Element(object):
    """element generique d ihm"""

    def __init__(self, parent, lin, col, titre):
        self.parent = parent
        self.ligne = lin
        self.colonne = int(col)
        self.titre = titre
        self.hauteur = 1
        self.elements = []
        self.nature = "Element"
        self.variables = parent.variables
        self.wsroot = None

    def mkheader(self):
        return ["", "#============" + self.nature + "=============", ""]

    @property
    def px(self):
        return (self.colonne - 1) * self.parent.lcols + 20

    @property
    def py(self):
        return (self.ligne - 1) * self.parent.hlin + 30

    def position(self, dx=0, dy=0):
        return "New-Object System.Drawing.Point(%d,%d)" % (self.px + dx, self.py + dy)

    def mklab(self, lab, titre, dx=0, dy=0):
        return [
            lab + " = New-Object system.Windows.Forms.Label",
            lab + '.text = "%s"' % (titre,),
            lab + ".AutoSize = $true",
            lab + ".Font = $font",
            lab + ".location = " + self.position(dx, dy),
            "",
        ]

    def struct(self, niveau):
        """affiche la structure de l ihm avec les imbrications"""
        print(
            "    " * niveau,
            self.id,
            self.nature,
            self.titre,
            "(",
            self.parent.id,
            ")",
        )
        for el in self.elements:
            el.struct(niveau + 1)


class Fileselect(Element):

    _ido = itertools.count(1)

    def __init__(self, parent, lin, col, titre, selecteur, variable):
        super().__init__(parent, lin, col, titre)
        self.id = "Fsel" + str(next(self._ido))
        self.nature = "Fileselect"
        self.selecteur = selecteur
        self.variable = variable
        self.hauteur = 2
        self.ref = self.id + "TB.Text"
        self.variables = parent.variables

    def genps(self, ihm):
        lab = "$" + self.id + "L"
        tb = "$" + self.id + "TB"
        fbr = "$" + self.id + "FBR"
        fbt = "$" + self.id + "FBT"
        code = (
            self.mkheader()
            + self.mklab(lab, self.titre)
            + [
                "",
                tb + " = New-Object system.Windows.Forms.TextBox",
                tb + ".multiline = $false",
                tb + ".width = 300",
                tb + ".height = 20",
                tb + ".location = " + self.position(dy=30),
                tb + ".Font = $font",
                tb + ".AllowDrop = $true",
                "",
                tb + ".add_DragDrop(",
                "   {",
                "       $files = [string[]]$_.Data.GetData([Windows.Forms.DataFormats]::FileDrop)",
                "       if ($files){" + tb + ".Text = $files[0]}",
                "   }",
                ")",
                tb + ".add_DragOver(",
                "   {",
                "       if ($_.Data.GetDataPresent([Windows.Forms.DataFormats]::FileDrop))",
                "       {$_.Effect = 'Copy'} else {$_.Effect = 'None'}",
                "   }",
                ")",
                "",
                fbr + " = New-Object System.Windows.Forms.OpenFileDialog",
                fbr + '.Title = "%s"' % (self.titre,),
                fbr + '.Filter = "%s"' % (self.selecteur,),
                "",
                "",
                fbt + " = New-Object system.Windows.Forms.Button",
                fbt + '.text = "..."',
                fbt + ".width = 24",
                fbt + ".height = 24",
                fbt + ".location = " + self.position(dx=300, dy=30),
                fbt + ".Font = $font",
                "#===onclick====",
                fbt + ".Add_Click(",
                "   {",
                '       $sd="."',
                "       if (%s.Text -ne '') { $sd=Split-Path -Path %s.Text }"
                % (tb, tb),
                "       %s.InitialDirectory=$sd" % (fbr,),
                "       $null = %s.ShowDialog()" % (fbr,),
                "       %s.Text = %s.FileName" % (tb, fbr),
                "       %s.Update()" % (tb,),
                "   }",
                "   )",
            ]
        )
        return [lab, tb, fbt], code


class Droplist(Element):
    _ido = itertools.count(1)

    def __init__(self, parent, lin, col, titre, selecteur, variable):
        super().__init__(parent, lin, col, titre)
        self.id = "Dlist" + str(next(self._ido))
        self.selecteur = selecteur
        self.variable = variable
        self.nature = "Droplist"
        self.hauteur = 2
        self.ref = self.id + ".Text"

    def genps(self, ihm):
        dl = "$" + self.id
        dlb = dl + "L"
        if self.selecteur.startswith("@@"):  # appel serviceweb
            seldef = usewebservice(ihm, self.selecteur)
        else:
            seldef = '"' + '","'.join(self.selecteur.split(",")) + '"'
        code = (
            self.mkheader()
            + self.mklab(dlb, self.titre)
            + [
                dl + " = New-Object system.Windows.Forms.ComboBox",
                dl + ".Items.AddRange(@(%s))" % (seldef,),
                dl + ".location =" + self.position(dy=30),
                dl + ".width = 100",
                dl + ".height = 40",
                dl + ".Font = $font",
            ]
        )
        return [dl, dlb], code


class ListView(Element):
    """liste de cases a cocher"""

    _ido = itertools.count(1)

    def __init__(self, parent, lin, col, titre, selecteur, variable):
        super().__init__(parent, lin, col, titre)
        self.id = "Clist" + str(next(self._ido))
        self.selecteur = selecteur
        self.variable = variable
        self.nature = "Checklist"
        self.hauteur = 2
        self.ref = self.id + ".Text"

    def genps(self, ihm):
        dl = "$" + self.id
        dlb = dl + "Cl"
        if self.selecteur.startswith("@@"):  # appel serviceweb
            seldef = usewebservice(ihm, self.selecteur)
        else:
            seldef = '"' + '","'.join(self.selecteur.split(",")) + '"'
        code = (
            self.mkheader()
            + self.mklab(dlb, self.titre)
            + [
                dl + " = New-Object system.Windows.Forms.ListView",
                dl + ".Items.AddRange(@(%s))" % (seldef,),
                dl + ".location =" + self.position(dy=30),
                dl + ".width = 200",
                dl + ".height = 100",
                dl + ".Font = $font",
            ]
        )
        return [dl, dlb], code


class Checkbox(Element):
    _ido = itertools.count(1)

    def __init__(self, parent, lin, col, titre, etat, variable):
        super().__init__(parent, lin, col, titre)
        self.id = "Cbox" + str(next(self._ido))
        self.etat = etat
        self.variable = variable
        self.nature = "Checkbox"
        self.hauteur = 1
        self.ref = self.id + ".Checked"

    def genps(self, ihm):
        cb = "$" + self.id
        code = self.mkheader() + [
            cb + "= New-Object system.Windows.Forms.CheckBox",
            cb + '.text = "%s"' % (self.titre,),
            cb + ".AutoSize = $true",
            cb + ".Checked = %s" % (self.etat,),
            cb + ".location =" + self.position(),
            cb + ".Font = $font",
        ]
        return [cb], code


class Bouton(Element):

    _ido = itertools.count(1)

    def __init__(self, parent, lin, col, titre):
        super().__init__(parent, lin, col, titre)
        self.id = "Btn" + str(next(self._ido))
        self.nature = "Bouton"

    def genps(self, ihm):
        bt = "$" + self.id
        lcols = self.parent.lcols
        code = self.mkheader() + [
            bt + " = New-Object system.Windows.Forms.Button",
            bt + '.text = "%s"' % ((self.titre,)),
            bt + ".width =" + str(lcols),
            bt + ".height = 40",
            bt + ".location = " + self.position(),
            bt + ".Font = $font",
            "#---------onclick----------",
            bt + ".Add_Click(",
            "   {",
            "[System.Windows.Forms.Cursor]::Current=[System.Windows.Forms.Cursors]::WaitCursor",
        ]
        for el in self.elements:
            se, sc = el.genps(ihm)
            code.extend(sc)
        code.extend(
            [
                "[System.Windows.Forms.Cursor]::Current=[System.Windows.Forms.Cursors]::Default",
                "   }",
                ")",
            ]
        )
        return [bt], code

    @property
    def lcols(self):
        return self.parent.lcols


class Label(Element):
    _ido = itertools.count(1)

    def __init__(self, parent, lin, col, titre):
        super().__init__(parent, lin, col, titre)
        self.id = "Lbl" + str(next(self._ido))
        self.nature = "label"

    def genps(self, ihm):
        lab = "$" + self.id
        code = self.mkheader() + self.mklab(lab, self.titre)
        return [lab], code


class Statusbar(Label):
    def __init__(self, parent, lin, col, titre):
        super().__init__(parent, lin, col, titre)
        self.id = "statusbar"
        self.nature = "statusbar"


class Commande(Element):
    def __init__(self, parent, texte):
        super().__init__(parent, "=", 1, "")
        self.commande = texte
        self.nature = "commande"
        self.ligne = "="
        self.colonne = 1

    def genps(self, ihm):
        commande = self.commande
        commande = usewebservice(ihm, commande)
        # if "#" in commande:
        #     # on gere les # que powershell n aime pas
        #     tmp = commande.split(" ")
        #     commande = " ".join(["'" + i + "'" if "#" in i else i for i in tmp])
        while "$[" in commande:
            variable = commande.split("$[")[1].split("]$")[0]
            if variable in self.variables:
                commande = commande.replace(
                    "$[" + variable + "]$", "$($" + self.variables[variable].ref + ")"
                )
            else:
                print("variable introuvable", variable, self.variables)
                break
        code = [commande]
        return [], code

    def struct(self, niveau):
        """affiche la structure de l ihm avec les imbrications"""
        print("    " * niveau, "commande ", self.commande)


# def getvariable(code):
#     """extrait la ou les variables de references"""
#     if '['in code:
#         variables=code.strip()[:-1].split('[')[1]
#     return variables


def creihm(nom):
    nbb = 0
    elem = None
    ihm = None
    courant = None
    sniplets = dict()
    if not nom:
        print("usage mapper -genihm nom_fichier_ihm")
        return
    if not os.path.isfile(nom):
        if os.path.isfile(nom + ".csv"):
            nom = nom + ".csv"
        else:
            print("fichier de description introuvable", nom)
            return
    with open(nom, "r") as f:
        for ligne in f:
            if not ligne or ligne.startswith("!#"):
                continue
            try:
                code, position, commande = ligne[:-1].split(";", 2)
            except ValueError:
                print(" ligne mal formee", ligne)
                continue
            if code.startswith("!ihm"):
                if position == "init":
                    tmp = commande.split(",")
                    interpreteur = tmp[0]
                    nom_ihm = os.path.splitext(nom)[0]
                    if ihm:
                        "print erreur redefinition ihm "
                        raise StopIteration
                    ihm = Ihm(nom_ihm, interpreteur)
                    variables = ihm.variables
            elif code == "!weblink":
                nom_service = position
                url, start, *_ = commande.split(",") + ["", ""]
                ihm.weblinks[nom_service] = url
                print("enregistrement weblink", nom_service, url)
                if start:
                    ihm.startserver = True
            elif code == "!fenetre":
                largeur = int(position)
                titre = commande[:-1] if commande.endswith("\n") else commande
                if not ihm:
                    "print erreur cadre ihm non defini"
                    raise StopIteration
                if courant is None:
                    elem = Fenetre(ihm, titre, largeur)
                    ihm.main = elem
                elif isinstance(courant, (Bouton, Fenetre)):
                    courant.elements.append(elem)
                    elem = Fenetre(courant, titre, largeur)
                courant = elem

            elif code == "!fileselect":
                lin, col = position.split(",", 1)
                titre, selecteur, variable = commande.split(";", 2)
                variable = variable.split(";")[0]
                fsel = Fileselect(courant, lin, col, titre, selecteur, variable)
                courant.elements.append(fsel)
                print("fsel:trouve variable", variable)
                if variable:
                    variables[variable] = fsel

            elif code == "!ps":
                if commande and "$[]$" in commande:
                    commande = commande.replace("$[]$", "$($" + elem.ref + ")")
                if position:
                    if commande:
                        if position in sniplets:
                            sniplets[position].append(commande)
                        else:
                            sniplets[position] = [commande]
                    else:
                        courant.elements.extend(sniplets[position])
                else:
                    courant.elements.append(Commande(courant, commande))

            elif code == "!droplist":
                lin, col = position.split(",")
                titre, liste, variable = commande.split(";", 2)
                variable = variable.split(";")[0]
                dlist = Droplist(courant, lin, col, titre, liste, variable)
                courant.elements.append(dlist)
                if variable:
                    variables[variable] = dlist

            elif code == "!checklist":
                lin, col = position.split(",")
                titre, liste, variable = commande.split(";", 2)
                variable = variable.split(";")[0]
                dlist = ListView(courant, lin, col, titre, liste, variable)
                courant.elements.append(dlist)
                if variable:
                    variables[variable] = dlist

            elif code == "!button":
                lin, col = position.split(",")
                titre = commande[:-1] if commande.endswith("\n") else commande

                # print("bouton", type(courant), isinstance(courant, Bouton))
                if isinstance(courant, Bouton):
                    courant = ihm.elements[-1] if ihm.elements else ihm.main
                    # print(" courant apres", type(courant))
                elem = Bouton(courant, lin, col, titre)
                courant.elements.append(elem)
                courant = elem

            elif code == "!case":
                lin, col = position.split(",")
                titre, init, variable = commande.split(";", 2)
                variable = variable.split(";")[0]
                dlist = Checkbox(courant, lin, col, titre, init, variable)
                courant.elements.append(dlist)
                if variable:
                    variables[variable] = dlist

            elif code == "!status":
                courant.parent.statusbar = True
                courant.elements.append(
                    Commande(courant, '$statusbar.text="' + commande + '"')
                )
                courant.elements.append(Commande(courant, "$statusbar.Refresh()"))
            else:
                print("code inconnu", code)
    ihm.struct()

    sortie = ihm.nom + ".ps1"
    with open(sortie, "w", encoding="cp1252") as f:
        f.write("\n".join(ihm.genps(variables)))
