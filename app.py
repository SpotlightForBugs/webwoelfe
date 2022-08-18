from traceback import print_tb  # skipcq: PY-W2000
from flask import (  # skipcq: PY-W2000
    Flask,
    request,
    url_for,
    render_template,
    session,
    make_response,
    redirect,
    Response,
    escape,
)

import werwolf
import datetime
import re
from inspect import currentframe, getframeinfo
from datetime import datetime


app = Flask(__name__)

# index page


@app.route("/", methods=["GET", "POST"])  # Homepage
def index():
    return render_template("index.html")  # Render index.html


# einstellungen


@app.route("/einstellungen", methods=["GET", "POST"])  # Einstellungen
def einstellungen():
    return render_template("einstellungen.html")  # Render einstellungen.html


# wie viele Spieler sollen vorhanden sein?

# Spieleranzahl
@app.route("/einstellungen/spieleranzahl", methods=["GET", "POST"])
def setPlayerNumber():  # set the number of players
    # get the number of players from the form
    spieleranzahl = request.form.get("num")
    try:
        # eingabe ist wirklich ein integer
        spieleranzahl_int = int(spieleranzahl)
        if (
            spieleranzahl_int < 8 or spieleranzahl_int > 18
        ):  # Spieleranzahl ist zwischen 8 und 18
            spieleranzahl = 8  # auf 8 defaulten
    except ValueError:
        spieleranzahl = 8  # auf 8 defaulten

    # speichern der spieleranzahl in einer textdatei
    with open("spieler_anzahl.txt", "w+") as file:
        file.write(str(spieleranzahl))
    if bool(request.form.get("cbx")) is True:  # checkbox is checked
        erzaehler_flag = 1  # set erzaehler_flag to 1
    else:
        erzaehler_flag = 0  # set erzaehler_flag to 0
    # speichern des erzaehler_flag in einer textdatei
    with open("erzaehler_ist_zufaellig.txt", "w+") as flag:
        # speichern des erzaehler_flag in einer textdatei
        flag.write(str(erzaehler_flag))
    werwolf.createDict()  # create the dictionary with the names of the players
    with open("rollen_log.txt", "w+") as f:  # leere rollen_log.txt
        f.write("*********************\n")
    # render einstellungen_gespeichert.html
    return render_template(
        "einstellungen_gespeichert.html", spieleranzahl_var=spieleranzahl
    )


# namenseingabe spieler


@app.route("/spieler", methods=["GET", "POST"])  # Spieler
def get_data():  # get the data from the form
    if request.method == "GET":  # if the request is a GET request
        return render_template("fehler.html")  # fehlerseite ausgeben
    if request.method == "POST":  # if the request is a POST request
        name = request.form.get("name")  # get the name from the form

        name = name.replace("/", "_")  # / ist immer ein _
        name = name.replace("=", "-")  # gleich ist immer -
        name = name.replace(":", "_")  # doppelpunkt ist immer _
        name = name.replace("*", "_")  # stern ist immer _
        with open("rollen_log.txt") as players_log:  # open the log file
            players_log = players_log.read()  # read the log file
        if werwolf.validiere_name(name) is True:
            # if the name is already in the log file
            # name doppelt ausgeben
            return render_template("name_doppelt.html", name=name)

        with open("spieler_anzahl.txt") as file:
            num = file.read()  # read the file
        operator = werwolf.deduct()  # get the operator
        try:  # try to get the operator
            if operator == 0:  # if the operator is 0
                code = "code"  # set the code to code
                # render spiel_beginnt.html
                return render_template("spiel_beginnt.html", code=code)
            # append the name to the log file
            with open("rollen_log.txt", "a") as names:
                # write the name and the operator to the log file
                names.write(f"{name} = {operator}")
                # names.write(f'{date}: {name} = {operator}')
                # write a new line to the log file
                names.write("\n")
                names.close()
            # append the name to the log file
            with open("rollen_original.txt", "a") as names:
                # write the name and the operator to the log file
                names.write(f"{name} = {operator}")
                # names.write(f'{date}: {name} = {operator}')
                # write a new line to the log file
                names.write("\n")
                # credits to @joschicraft

                # render rollen_zuweisung.html
                return render_template(
                    "rollen_zuweisung.html",
                    players=num,
                    name=name,
                    operator=operator,
                )
        except:
            # render neu_laden.html
            return render_template("neu_laden.html")


# Pfad des Erzählers, momentan für debugzwecke auf einem ungeschützten pfad


@app.route("/erzaehler", methods=["GET"])  # Erzähler
def erzaehler():
    try:
        with open("rollen_log.txt") as players_log:  # open the log file
            players_log = players_log.readlines()  # read the log file
        # render erzaehler.html
        return render_template("erzaehler.html", names=players_log)
    except:
        return str(404)  # return 404 if the file is not found


# Neues Spiel


# reset der rollen_log.txt
@app.route("/erzaehler/reset", methods=["GET", "POST"])
def reset():
    if request.method == "POST":
        if request.form["reset_button"] == "Neues Spiel":  # wenn neues spiel gewuenscht
            werwolf.leere_dateien()  # leere die dateien

            # zurück zur einstellungen
            return render_template("einstellungen.html")
    elif request.method == "GET":
        return render_template("index.html")  # zurück zur homepage


@app.route("/<name>/<rolle>/toeten/<name_kill>")  # kill a player
def kill_player(name, rolle, name_kill):
    auswahl = name_kill
    if rolle in ("Hexe", "Jaeger"):
        if (
            rolle == "Hexe"
            and werwolf.hexe_darf_toeten() is True
            and werwolf.validiere_rolle(name, rolle) is True
            or rolle == "Jaeger"
            and werwolf.validiere_rolle(name, rolle) is True
        ):

            if rolle == "Jaeger":
                if werwolf.jaeger_darf_toeten() is True:
                    werwolf.toete_spieler(auswahl)
                    werwolf.jaeger_fertig()
                    return render_template(
                        "Dashboards/status/tot.html",
                    )
                return render_template("Dashboards/status/tot.html")

            if rolle == "Hexe":
                werwolf.hexe_verbraucht("toeten")

                return render_template(
                    "Dashboards/Dash_Hexe.html", name=name, rolle=rolle
                )
        else:
            return render_template("fehler.html")

    else:
        return render_template("fehler.html")


@app.route("/<name>/Armor_aktion/<player1>/<player2>")  # player auswahl
def armor_player(player1, player2, name):
    rolle = "Armor"

    if (
        werwolf.validiere_rolle(name, rolle) is True
        and werwolf.armor_darf_auswaehlen() is True
    ):

        werwolf.armor_fertig(player1, player2)
        return render_template("Dashboards/status/aktion_warten.html")

    if (
        werwolf.armor_darf_auswaehlen() is False
        and werwolf.validiere_rolle(name, rolle) is True
    ):

        return render_template("Dashboards/status/aktion_warten.html")

    if werwolf.validiere_rolle(name, rolle) is False:
        # print the error
        print(
            "Spieler oder Rolle falsch, zeige ihm den Klobert und leite Ihn nach 10 sekunden zurück!"
        )
        # render the url_system.html
        return render_template("url_system.html", name=name, rolle=rolle)
    return render_template("fehler.html")


@app.route("/<name>/<rolle>/warten_auf_aktions_ende")
def aktion_warten(name, rolle):
    if werwolf.validiere_rolle(name, rolle) is True:
        return render_template("Dashboards/status/aktion_warten.html")


# Übersicht der Spieler


@app.route("/uebersicht/<ist_unschuldig>")  # Übersicht
def overview_all(ist_unschuldig):  # Übersicht

    try:
        # ist_unschuldig ist wirklich ein integer
        ist_unschuldig = int(ist_unschuldig)
        if ist_unschuldig == 1:  # wenn ist_unschuldig = 1
            with open("rollen_original.txt") as players_log:  # open the log file
                players_log = players_log.readlines()  # read the log file
            # render overview_innocent.html
            return render_template("overview_innocent.html", names=players_log)
        if ist_unschuldig == 0:  # wenn ist_unschuldig = 0
            with open("rollen_oriinal.txt") as players_log:# open the log file
                players_log = players_log.readlines()  # read the log file
            # render overview_guilty.html
            return render_template("overview_guilty.html", names=players_log)
        return render_template("fehler.html")  # render fehler.html
    except:
        return render_template("fehler.html")  # render fehler.html


# Rollen Dashboards


@app.route("/<name>/<rolle>/Dashboard")  # Dashboard
def Dashboard(name, rolle):  # Dashboard

    # create a string with the name and the role
    with open("rollen_log.txt", "r") as file:  # open the log file
        players_vorhanden = file.read()  # read the log file

    rolleAusLog = players_vorhanden.split(" = ")  # split the log file into a list
    rolleAusLog = rolleAusLog[1]

    if rolleAusLog == "Tot":
        return render_template("tot.html", name=name)  # render tot.html

    # if the name and the role are in the log file
    if werwolf.validiere_rolle(name, rolle) is True:
        try:  # try to get the role
            with open("rollen_log.txt") as players_log:  # open the log file
                players_log = players_log.readlines()  # read the log file

            nurNamen = []  # create a list with the names

            try:
                for line in players_log:  # for every line in the log file

                    if "*" in line:  # if the line contains a *
                        pass  # do nothing
                    else:  # if the line does not contain a *
                        line = line.split(" = ")  # split the line at the =
                        name_line = line[0]
                        # set the role to the second part of the line
                        auswahlRolle = line[1]

                        # if the role is not Tot or the role is not the Erzähler
                        if auswahlRolle not in ("Tot", "Erzaehler"):
                            # append the name to the list
                            nurNamen.append(name_line)

            except:
                print(
                    "[Debug] Fehler beim Auslesen des rollen_logs in app.py line "
                    + str(getframeinfo(currentframe()).lineno - 1)
                )  # print the error

            # render Dash_rolle.html
            return render_template(
                "Dashboards/Dash_Dorfbewohner.html",
                name=name,
                rolle=rolle,
                names=players_log,
                nurNamen=nurNamen,
            )

        except:
            return render_template("fehler.html")  # render fehler.html

    else:
        # print the error
        print(
            "Spieler oder Rolle falsch, zeige ihm den Klobert und leite Ihn nach 10 sekunden zurück!"
        )
        # render url_system.html
        return render_template("url_system.html", name=name, rolle=rolle)


@app.route("/<name>/<rolle>/Dashboard_sp")
def spezielles_Dashboard(name, rolle):
    if rolle == "Tot":
        return render_template("fehler.html")
    # create a string with the name and the role
    with open("rollen_log.txt", "r") as file:# open the log file
        players_vorhanden = file.read()  # read the log file


    rolleAusLog = players_vorhanden.split(" = ")  # split the log file into a list
    rolleAusLog = rolleAusLog[1]

    if rolleAusLog == "Tot":
        return render_template("tot.html", name=name)  # render tot.html
    # if the name and the role are in the log file
    if werwolf.validiere_rolle(name, rolle) is True:

        nurNamen = []  # create a list with the names

        if rolle == "Hexe":
            print("Hexe")
            with open("hexe_kann.txt", "r") as file:
                hexe_kann = file.read()
                hexe_kann = str(hexe_kann)
                file.close()

    with open("rollen_log.txt") as players_log:  # open the log file
        players_log = players_log.readlines()  # read the log file

    for line in players_log:  # for every line in the log file

        if (
            "*" in line or "Tot" in line or "Erzaehler" in line
        ):  # if the line contains a *
            pass  # do nothing
        else:  # if the line does not contain a *
            line = line.split(" = ")  # split the line at the =
            name_line = line[0]
            # set the role to the second part of the line

            nurNamen.append(name_line)  # append the name to the list

    if rolle == "Hexe":

        # render Dash_rolle.html
        return render_template(
            "Dashboards/Dash_" + rolle + ".html",
            name=name,
            rolle=rolle,
            names=players_log,
            nurNamen=nurNamen,
            hexe_kann=hexe_kann,
        )

    if rolle == "Armor":
        return render_template(
            "Dashboards/Dash_" + rolle + ".html",
            name=name,
            rolle=rolle,
            names=players_log,
            nurNamen=nurNamen,
            armor_kann=werwolf.armor_darf_auswaehlen(),
        )
    # render Dash_rolle.html
    return render_template(
        "Dashboards/Dash_" + rolle + ".html",
        name=name,
        rolle=rolle,
        names=players_log,
        nurNamen=nurNamen,
    )


@app.route("/<name>/<rolle>/spiel_ende")
def spiel_ende(name, rolle):

    with open("rollen_original.txt", "r") as file:
        players_vorhanden = file.read()
        file.close()

        if werwolf.validiere_rolle_original(name, rolle) is True:
            if (
                "Werwolf" in  players_vorhanden
                and "Dorfbewohner" in players_vorhanden
                or "Hexe" in players_vorhanden
                and "Werwolf" in players_vorhanden
                or "Seherin" in players_vorhanden
                and "Werwolf" in players_vorhanden
                or "Jaeger" in players_vorhanden
                and "Werwolf" in players_vorhanden
                or "Armor" in players_vorhanden
                and "Werwolf" in players_vorhanden
            ):
                return "Hallo " + escape(name) + ", das Spiel ist noch nicht beendet!"

            print("Spiel ist beendet!")

            if rolle == "Werwolf":
                if "Werwolf" in players_vorhanden:
                    return render_template(
                        "gewonnen.html", name=name, rolle=rolle, unschuldig=0
                    )
                return render_template(
                    "verloren.html", name=name, rolle=rolle, unschuldig=0
                )
            if "Werwolf" in players_vorhanden:
                return render_template(
                    "verloren.html", name=name, rolle=rolle, unschuldig=1
                )
            return render_template(
                "gewonnen.html", name=name, rolle=rolle, unschuldig=1
            )


@app.route("/waehlen/<name>/<rolle>/<auswahl>")
def wahl(name, rolle, auswahl):

    if rolle == "Tot":
        return render_template("warten.html")

    wort2 = name + " : "

    if werwolf.validiere_rolle(name, rolle) is True:

        with open("hat_gewaehlt.txt", "r+") as text:
            contents = text.read()

            if wort2 in contents:
                return render_template("wahl_doppelt.html")
            text.write(name + " : " + "\n")
            text.close()
            with open("abstimmung.txt", "a") as abstimmung:
                abstimmung.write(auswahl + "" + "\n")

                abstimmung.close()
                return render_template("Dashboards/status/warten.html")


# schlafen function


@app.route("/<name>/<rolle>/schlafen")  # route for the sleep function
def schlafen(name, rolle):  # function for the sleep function

    if rolle == "Tot":
        return render_template("tot.html", name=name)

    # if the string is in the log file
    if werwolf.validiere_rolle(name, rolle) is True:
        try:
            with open("rollen_log.txt") as players_log:  # open the log file
                players_log = players_log.readlines()  # read the log file
            # render the sleep.html
            return render_template(
                "Dashboards/status/schlafen.html",
                name=name,
                rolle=rolle,
                names=players_log,
            )
        except:
            return render_template("fehler.html")  # render the fehler.html

    else:
        # print the error
        print(
            "Spieler oder Rolle falsch, zeige ihm den Klobert und leite Ihn nach 10 sekunden zurück!"
        )
        # render the url_system.html
        return render_template("url_system.html", name=name, rolle=rolle)


# warten funktion


@app.route("/warten")  # route for the wait function
def warten():  # function for the wait function
    i = 0  # set i to 0

    try:

        with open("rollen_log.txt", "r") as text:
            for line in text:
                if not "Tot" in line and not "Erzaehler" in line and not "*" in line:
                    i = i + 1
            text.close()
        with open("abstimmung.txt", "r") as text:
            # empty lines are not counted
            anzahl_stimmen = sum(1 for line in text if line.rstrip())

        text.close()
        print(anzahl_stimmen)
        print(i)
        if i == anzahl_stimmen:
            print("Alle Spieler haben gewaehlt")
            count = 0
            name_tot = ""
            maxCount = 0
            words = []

            file = open("abstimmung.txt", "r")

            for line in file:

                string = line.lower().replace(",", "").replace(".", "").split(" ")
                for s in string:
                    words.append(s)

            for i in range(0, len(words)):
                count = 1
                for j in range(i + 1, len(words)):
                    if words[i] == words[j]:
                        count = count + 1

                if count > maxCount:
                    maxCount = count
                    name_tot = words[i]

            with open("rollen_log.txt", "r+") as fileTot:

                file_list = []
                counter_tot = 0

                for line in fileTot:
                    file_list.append(line)

                # print(file_list)

                name_tot = name_tot.strip("\n")
                name_tot = name_tot.replace("\n", "")

                while counter_tot < len(file_list):

                    print("Name Tot: " + name_tot + " =")

                    if name_tot in file_list[counter_tot]:
                        dffd = file_list[counter_tot].split(" = ")
                        new_line = dffd[0] + " = Tot \n"
                        # print(new_line)
                        file_list[counter_tot] = new_line
                        # print(file_list)

                    counter_tot = counter_tot + 1

            fileTot.close()
            with open("rollen_log.txt", "w") as fileFinal:
                fileFinal.writelines(file_list)
            fileFinal.close()
            werwolf.schreibe_zuletzt_gestorben(name_tot)

            return render_template("Dashboards/status/ergebnis.html", name_tot=name_tot)
        return render_template("Dashboards/status/warten.html")

    except:
        return render_template("fehler.html")  # render the fehler.html


# tot function

# route for the death function
@app.route("/<name>/<rolle>/<todesgrund>/tot")
def tot(name, rolle, todesgrund):  # function for the death function
    # if the string is in the log file
    if werwolf.validiere_rolle(name, rolle) is True:
        try:  # try to get the role
            with open("rollen_log.txt") as players_log:  # open the log file
                players_log = players_log.readlines()  # read the log file

            if todesgrund in (
                "Werwolf",
                "werwolf",
            ):  # if the death reason is a werewolf
                # set the death reason to a werewolf
                todesgrund = "Du wurdest von einem Werwolf getötet"
            # if the death reason is a abstimulation
            elif todesgrund in ("Abstimung", "abstimmung"):
                # set the death reason to a abstimulation
                todesgrund = "Du wurdest in Folge einer Abstimmung getötet"
            elif todesgrund == "Hexe":  # if the death reason is a witch
                todesgrund = (
                    "Du wurdest von der Hexe getötet"  # set the death reason to a witch
                )
            else:
                todesgrund = (
                    "Du wurdest getötet"  # set the death reason to a normal death
                )
            # rendert die Seite zum Status Tot
            return render_template(
                "Dashboards/status/tot.html",
                name=name,
                todesgrund=todesgrund,
            )

        except:
            # rendert die Seite zum Status Fehler
            return render_template("fehler.html")

    else:
        # print the error
        print(
            "Spieler oder Rolle falsch, zeige ihm den Klobert und leite Ihn nach 10 sekunden zurück!"
        )
        # render the url_system.html
        return render_template("url_system.html", name=name, rolle=rolle)


# kick function


@app.route("/<name>/<rolle>/kick/")  # route for the kick function
def rausschmeissen(name, rolle):  # function for the kick function
    if werwolf.validiere_rolle(name, rolle) is True:
        print("Spieler vorhanden")  # print the string
        try:
            with open("rollen_log.txt") as players_log:  # open the log file
                players_log = players_log.readlines()  # read the log file
            # render the rausschmeissen.html

            werwolf.toete_spieler(name)
            return render_template(
                "rausschmeissen.html", name=name, rolle=rolle, names=players_log
            )
        except:

            return render_template("fehler.html")  # render the fehler.html

    else:
        # print the error
        print(
            "Spieler oder Rolle falsch, zeige ihm den Klobert und leite Ihn nach 10 sekunden zurück!"
        )
        # render the url_system.html
        return render_template("url_system.html", name=name, rolle=rolle)


# wahlbalken


@app.route("/wahlbalken/")  # route for the wahlbalken function
def wahlbalken():
    with open("rollen_log.txt") as players_log:  # open the log file
        players_log = players_log.readlines()  # read the log file

    print(players_log)

    print("Test")

    nurNamen = []  # create a list for the names

    try:
        for line in players_log:  # for every line in the log file

            if "*" in line:  # if the line contains a *
                pass  # do nothing
            else:  # if the line does not contain a *
                line = line.split(" = ")  # split the line at the =
                name = line[0]  # get the name
                auswahlRolle = line[1]  # get the role

                # if the role is not dead or the narrator
                if auswahlRolle not in ("Tot", "Erzaehler"):
                    nurNamen.append(name)  # append the name to the list

        # render the wahlbalken.html
        return render_template("wahlbalken.html", names=nurNamen)

    except:
        return render_template("fehler.html")  # render the fehler.html


@app.route("/wahlstatus")  # route for the wahlstatus function
def wahl_stats():

    anzahl = 0
    name_tot = ""
    maxCount = 0
    words = []

    file = open("abstimmung.txt", "r")

    for line in file:

        string = line.lower().replace(",", "").replace(".", "").split(" ")
        for s in string:
            words.append(s)

    for i in range(0, len(words)):
        anzahl = 1
        for j in range(i + 1, len(words)):
            if words[i] == words[j]:
                anzahl = anzahl + 1

        if anzahl > maxCount:
            maxCount = anzahl
            name_tot = words[i]

            werwolf.schreibe_zuletzt_gestorben(name_tot)

    return render_template("wahlstatus.html", name_tot=name_tot)


@app.route("/sehen/<name>/<rolle>/<auswahl>")
def sehen(name, rolle, auswahl):
    if werwolf.validiere_rolle(name, rolle) is True:
        with open("rollen_log.txt") as players_log:  # open the log file
            players_log = players_log.readlines()  # read the log file
        for line in players_log:
            if auswahl in line:
                ergebnis = line
                ergebnis = ergebnis.replace("=", "hat die Rolle")
                return render_template(
                    "Dashboards/status/sehen.html", ergebnis=ergebnis
                )

    else:
        # print the error
        print(
            "Spieler oder Rolle falsch, zeige ihm den Klobert und leite Ihn nach 10 sekunden zurück!"
        )
        return render_template("url_system.html", name=name, rolle=rolle)


@app.route("/weiterleitung/<target>")
def weiterleitung(target):

    return render_template("weiterleitung.html", target=target)


@app.route("/<name>/<rolle>/<auswahl>/wer_tot")
def wer_tot(name, rolle, auswahl):

    with open("rollen_log.txt", "r") as file:  # open the log file
        players_vorhanden = file.read()  # read the log file
    if werwolf.validiere_rolle(name, rolle) is True:
        with open("hat_gewaehlt.txt", "r") as f:
            if name + " : " in f.read():
                return render_template("wahl_doppelt.html")
            auswahl = auswahl.strip()  # erase the whitespace %20
            if auswahl in players_vorhanden:
                print("Eine legetime Auswahl wurde getroffen!")
                with open("abstimmung.txt", "a") as abstimmung:
                    abstimmung.write(auswahl + "\n")
                abstimmung.close()
                with open("hat_gewaehlt.txt", "a") as hat_gewaehlt:
                    hat_gewaehlt.write(name + " : " + "\n")
                    return render_template("Dashboards/status/wer_wahl_warten.html")


@app.route("/wer_wahl_warten")
def wer_wahl_warten():

    with open("hat_gewaehlt.txt", "r+") as hat_gewaehlt:
        wer_anzahl_stimmen = sum(1 for line in hat_gewaehlt if line.rstrip())
        if wer_anzahl_stimmen == 4:

            count = 0
            name_tot = ""
            maxCount = 0
            words = []

            file = open("abstimmung.txt", "r")

            for line in file:

                string = line.lower().replace(",", "").replace(".", "").split(" ")
                for s in string:
                    words.append(s)

            for i in range(0, len(words)):
                count = 1
                for j in range(i + 1, len(words)):
                    if words[i] == words[j]:
                        count = count + 1

                if count > maxCount:
                    maxCount = count
                    name_tot = words[i]

            with open("rollen_log.txt", "r+") as fileTot:

                file_list = []
                counter_tot = 0

                for line in fileTot:
                    file_list.append(line)

                # print(file_list)

                name_tot = name_tot.strip("\n")
                name_tot = name_tot.replace("\n", "")

                while counter_tot < len(file_list):

                    print("Name Tot: " + name_tot + " =")

                    if name_tot in file_list[counter_tot]:
                        dffd = file_list[counter_tot].split(" = ")
                        new_line = dffd[0] + " = Tot \n"
                        # print(new_line)
                        file_list[counter_tot] = new_line
                        # print(file_list)

                    counter_tot = counter_tot + 1

            fileTot.close()
            with open("rollen_log.txt", "w") as fileFinal:
                fileFinal.writelines(file_list)
            fileFinal.close()

            werwolf.schreibe_zuletzt_gestorben(name_tot)

            return render_template(
                "Dashboards/status/wer_wahl_ergebnis.html", name_tot=name_tot
            )
        return render_template("Dashboards/status/wer_wahl_warten.html")


@app.route("/<name>/<rolle>/heilen/<auswahl>")
def heilen(name, rolle, auswahl):
    if (
        werwolf.validiere_rolle(name, rolle) is True
        and werwolf.hexe_darf_heilen() is True
    ):
        counter = 1
        with open("rollen_original.txt", "r") as file:
            file_list = ["*********************\n"]

            for line in file:
                file_list.append(line)

        while counter < len(file_list):
            if auswahl in file_list[counter]:
                file_list[counter] = file_list[counter].replace(name, auswahl)
                counter = counter + 1
            else:
                counter = counter + 1
        file = open("rollen_log.txt", "w")

        file.writelines(file_list)

        werwolf.hexe_verbraucht("heilen")
        return render_template("Dashboards/Dash_Dorfbewohner.html")
    return render_template("fehler.html")


@app.route("/noscript")
def noscript():
    return render_template("noscript.html")


# context processor


@app.context_processor
def inject_now():
    return {"now": datetime.utcnow()}


# inject a variable called 'now' into the template context for use in templates (templates can then access it as {{now}})
# https://stackoverflow.com/questions/41231290/how-to-display-current-year-in-flask-template   #the source of this code
if __name__ == "__main__":
    app.run(debug=True)
