from datetime import datetime
import random
import ast


liste_tot_mit_aktion = ["Jaeger", "Hexe", "PLATZHALTER"]
liste_tot_ohne_aktion = ["Dorfbewohner", "Werwolf", "Seherin"]


def createDict():
    """Erstellt ein Dictionary mit den Rollen und deren Anzahl"""

    with open("spieler_anzahl.txt", "r") as f:
        spieleranzahl = f.read()
    try:
        spieleranzahl = int(spieleranzahl)
    except:
        spieleranzahl = 8  # auf 8 defaulten
    with open("erzaehler_ist_zufaellig.txt", "r") as fl:
        erzaehler_flag = int(fl.read())

    werwolf = spieleranzahl // 4
    hexe = spieleranzahl // 12
    seherin = spieleranzahl // 12
    armor = 1
    if hexe == 0:
        hexe = 1
    if seherin == 0:
        seherin = 1
    jaeger = 0
    if spieleranzahl >= 10:
        jaeger = 1

    if erzaehler_flag == 1:
        if jaeger > 0:
            assign = {
                "Erzaehler": 1,
                "Werwolf": werwolf,
                "Armor": armor,
                "Hexe": hexe,
                "Seherin": seherin,
                "Jaeger": jaeger,
                "Dorfbewohner": (
                    spieleranzahl - armor - werwolf - seherin - hexe - jaeger - 1
                ),
            }
        else:
            assign = {
                "Erzaehler": 1,
                "Werwolf": werwolf,
                "Armor": armor,
                "Hexe": hexe,
                "Seherin": seherin,
                "Dorfbewohner": (spieleranzahl - werwolf - seherin - hexe - armor - 1),
            }
    elif erzaehler_flag == 0:
        if jaeger > 0:
            assign = {
                "Werwolf": werwolf,
                "Hexe": hexe,
                "Armor": armor,
                "Seherin": seherin,
                "Jaeger": jaeger,
                "Dorfbewohner": (
                    spieleranzahl - werwolf - seherin - hexe - jaeger - armor
                ),
            }
        else:
            assign = {
                "Werwolf": werwolf,
                "Hexe": hexe,
                "Armor": armor,
                "Seherin": seherin,
                "Dorfbewohner": (spieleranzahl - werwolf - seherin - hexe - armor),
            }

    with open("rollen_zuweisung.txt", "w+") as a:
        a.write(str(assign))


def deduct():
    """
    1. We open the file "rollen_zuweisung.txt" and read the content.
    2. We convert the content to a dictionary.
    3. We convert the dictionary to a list of keys.
    4. We check if the sum of the values of the dictionary is 0. If it is, we return 0."""
    with open("rollen_zuweisung.txt", "r+") as a:
        assign = a.read()
        # print(assign)
        assign = ast.literal_eval(assign)
        keys = list(assign)

    if sum(assign.values()) == 0:
        return 0

    def assignment():
        """Here is the explanation for the code above:
        1. We create a dictionary called assign that has the keys of the list keys and the values of the list values.
        2. We create a while loop that will continue to run as long as the sum of the values of assign is greater than or equal to 0.
        3. We create a random number generator that will generate a random number between 0 and the length of assign minus 1.
        4. If the value of the key of assign at the random number is greater than 0, we subtract 1 from the value of the key of assign.
        5. If the value of the key of assign at the random number is equal to 0, we delete the key of assign at the random number.
        6. We return the random number."""
        while sum(assign.values()) >= 0:
            num = random.randint(0, len(assign) - 1)
            if assign[keys[num]] > 0:
                assign[keys[num]] -= 1
                if assign[keys[num]] == 0:
                    del assign[keys[num]]
                return num

            assignment()

    ind = assignment()
    print(assign)
    with open("rollen_zuweisung.txt", "w+") as b:
        b.write(str(assign))
    result = keys[ind]
    return result


def validiere_rolle(name: str, rolle: str) -> bool:
    """This function checks if the role is valid:
    1. Creates a string with the name and the role.
    2. Opens the log file.
    3. Reads the log file.
    4. Checks if the string is in the log file.
    5. Returns true if the string is in the log file, false otherwise."""
    # create a string with the name and the role
    wort = ("'" + name + " = " + rolle + "\n'").encode("unicode_escape").decode("utf-8")
    file = open("rollen_log.txt", "r")  # open the log file
    players_vorhanden = str(file.readlines())  # read the log file
    if wort in players_vorhanden:
        return True
    return False


def validiere_rolle_original(name: str, rolle: str) -> bool:
    """
    1. Creates a string with the name and the role.
    2. Encodes the string to a format that can be read by the log file.
    3. Reads the log file.
    4. If the string is in the log file, the function returns True.
    5. If the string is not in the log file, the function returns False."""

    # create a string with the name and the role
    wort = ("'" + name + " = " + rolle + "\n'").encode("unicode_escape").decode("utf-8")
    file = open("rollen_original.txt", "r")  # open the log file
    players_vorhanden = str(file.readlines())  # read the log file
    if wort in players_vorhanden:
        return True
    return False


def validiere_name(name: str) -> bool:
    """This function checks if the name is valid:

    Keyword arguments:
    argument -- the name to be checked
    Return: True if the name is valid, False otherwise.
    """

    wort = ("'" + name + " = ").encode("unicode_escape").decode("utf-8")
    file = open("rollen_log.txt", "r")  # open the log file
    players_vorhanden = str(file.readlines())  # read the log file
    if wort in players_vorhanden:
        return True
    return False


def hexe_verbraucht(flag: str):
    """This function uses up the potion of the hexe:

    Keyword arguments:
    flag -- will be either "heal" or "kill", depending on the potion used.

    """

    if "t" in flag or "T" in flag:
        flag = str(2)
    elif "h" in flag or "H" in flag:
        flag = str(1)

        if str(flag) == "1" or str(flag) == "2":
            with open("hexe_kann.txt", "r") as hexe_kann:
                hexe_kann_text = hexe_kann.read()
                hexe_kann_text = hexe_kann_text.replace(str(flag), "")
                hexe_kann.close()
            with open("hexe_kann.txt", "w") as hexe_kann_schreiben:
                hexe_kann_schreiben.write(hexe_kann_text)
                hexe_kann_schreiben.close()
        else:
            raise ValueError("Die Hexe kann nur über die flags 1 oder 2 verfügen")

    # heilen --> 1
    # toeten --> 2


def hexe_darf_toeten() -> bool:
    """This function checks if the hexe can kill"""
    with open("hexe_kann.txt", "r") as hexe_kann:
        hexe_kann_text = hexe_kann.read()
        if str(2) in hexe_kann_text:
            hexe_kann.close()
            return True
        hexe_kann.close()
        return False


def hexe_darf_heilen() -> bool:
    """This function checks if the hexe can heal"""
    with open("hexe_kann.txt", "r") as hexe_kann:
        hexe_kann_text = hexe_kann.read()
        if "1" in hexe_kann_text:
            hexe_kann.close()
            return True
        hexe_kann.close()
        return False


def armor_darf_auswaehlen() -> bool:
    """This function checks if the armor can select"""
    with open("armor_kann.txt", "r") as armor_kann:
        armor_kann_text = armor_kann.read()
        if "1" in armor_kann_text:
            armor_kann.close()
            return True
        armor_kann.close()
        return False


def jaeger_darf_toeten() -> bool:
    """This function checks if the jaeger can kill"""
    with open("jaeger_kann.txt", "r") as jaeger_kann:
        jaeger_kann_text = jaeger_kann.read()
        if "1" in jaeger_kann_text:
            jaeger_kann.close()
            return True
        jaeger_kann.close()
        return False


def jaeger_fertig():
    """This function sets the jaeger to be finished"""

    # jaeger_kann.txt mit 0 ersetzen
    with open("jaeger_kann.txt", "w") as jaeger_kann:
        jaeger_kann.write("0")
        jaeger_kann.close()


def armor_fertig(player1: str, player2: str):
    """This function sets the two lovers and the armor to be finished

    Keyword arguments:
    player1 -- the name of the first player
    player2 -- the name of the second player

    """

    if (
        player1 != player2
        and validiere_name(player1) is True
        and validiere_name(player2) is True
    ):
        with open("verliebt.txt", "r+") as verliebt:
            verliebt_text = verliebt.read()
            # wenn nicht in der Liste, dann hinzufügen.
            if not "+" + player1 + "+" + player2 + "\n" in verliebt_text:
                verliebt.seek(0)
                verliebt.write("+" + player1 + "+" + player2 + "\n")
                verliebt.truncate()
                verliebt.close()
            # datei armor_kann.txt mit 0 ersetzen
            with open("armor_kann.txt", "w") as armor_kann:
                armor_kann.write("0")
                armor_kann.close()


def ist_verliebt(name: str) -> bool:
    """This function checks if the player is verliebt"""
    with open("verliebt.txt", "r") as verliebt:
        verliebt_text = verliebt.read()
        if "+" + name in verliebt_text:
            verliebt.close()
            return True
        verliebt.close()
        return False


def leere_dateien():
    """ " This function empties the files of the game"""

    with open("rollen_log.txt", "w+") as f:  # leere rollen_log.txt
        f.write("*********************\n")
    file = open("abstimmung.txt", "r+")
    file.truncate(0)
    file.close()
    file2 = open("rollen_original.txt", "r+")
    file2.truncate(0)
    file2.close()
    file3 = open("hat_gewaehlt.txt", "r+")
    file3.truncate(0)
    file3.close()
    file4 = open("hexe_kann.txt", "w")
    file4.write(str(12))
    file4.close()
    file5 = open("armor_kann.txt", "w")
    file5.write(str(1))
    file5.close()
    file6 = open("verliebt.txt", "w")
    file6.write(str(""))
    file6.close()
    file7 = open("jaeger_kann.txt", "w")
    file7.write(str(1))
    file7.close()
    file8 = open("logfile.txt", "w")
    file8.truncate(0)
    file8.close()


def momentane_rolle(player: str) -> str:
    """This function returns the current role of the player"""

    lines = []
    for line in open("rollen_log.txt"):
        lines.append("+" + line)
    for line in lines:
        if "+" + player in line:
            return (line.split("=")[1].split("\n")[0]).replace(" ", "")
    return (
        "Ein Fehler ist aufgetreten, die Rolle von "
        + player
        + " konnte nicht ermittelt werden."
    )


def fruehere_rolle(player: str) -> str:
    """This function returns the previous role of the player, before dying"""
    lines = []
    for line in open("rollen_original.txt"):
        lines.append("+" + line)  # damit die Zeilen mit + beginnen
    for line in lines:
        if "+" + player in line:  # damit ganze Zeilen durchsucht werden können
            return (line.split("=")[1].split("\n")[0]).replace(" ", "")
            # remove whitespaces from result

    return (
        "Ein Fehler ist aufgetreten, die ursprüngliche Rolle von "
        + player
        + " konnte nicht ermittelt werden."
    )


def war_oder_ist_rolle(player: str, rolle: str) -> bool:
    """This function checks if the player has been or is the role"""
    if momentane_rolle(player) == rolle or fruehere_rolle(player) == rolle:
        return True
    return False


def aktion_verfuegbar_ist_tot(player: str) -> bool:
    """This function checks if the player can do an action"""

    if war_oder_ist_rolle(player, "Hexe") is True:
        if hexe_darf_toeten() is True:
            return True
        return False
    if war_oder_ist_rolle(player, "Jaeger") is True:
        if jaeger_darf_toeten() is True:
            return True
    else:
        return False


def zufallszahl(minimum: int, maximum: int) -> int:
    """This function returns a random number between minimum and maximum"""
    return random.randint(minimum, maximum)


def verliebte_toeten() -> str:
    """This function kills the lovers"""
    log_liste = []
    with open("verliebt.txt", "r") as verliebt:
        read = verliebt.read()
        player1 = (
            str(read.split("+"))
            .encode("utf-8")
            .decode("utf-8")
            .replace("\\n", "")
            .replace("'", "")
            .replace("[", "")
            .replace("]", "")
            .replace("'", "")
            .replace(" ", "")
            .split(",")[1]
        )
        player2 = (
            str(read.split("+"))
            .encode("utf-8")
            .decode("utf-8")
            .replace("\\n", "")
            .replace("'", "")
            .replace("[", "")
            .replace("]", "")
            .replace("'", "")
            .replace(" ", "")
            .split(",")[2]
        )
        verliebt.close()
    with open("rollen_log.txt", "r") as rollen_log:
        for line in rollen_log:
            if line == (player1 + " = " + momentane_rolle(player1) + "\n"):
                log_liste.append("+" + player1 + " = " + "Tot" + "\n")
            elif line == (player2 + " = " + momentane_rolle(player2) + "\n"):
                log_liste.append("+" + player2 + " = " + "Tot" + "\n")
            else:
                log_liste.append(line)

    with open("rollen_log.txt", "w") as rollen_log_write:
        for line in log_liste:
            rollen_log_write.write((line).replace("+", ""))
        rollen_log_write.close()
        rollen_log.close()

    return player1 + " und " + player2


def schreibe_zuletzt_gestorben(player: str) -> None:
    """This function writes the last dead player to the logfile"""
    with open("letzter_tot.txt", "r+") as letzter_tot_w:
        letzter_tot_w.write(player)


# Tötet den gewählten Spieler


def toete_spieler(player):
    """kills the player

    Args:
        player (str): the player to kill


    """
    player = str(player)
    rolle = momentane_rolle(player)
    list_for_the_log = []
    statement = None  # warum ist das nötig?
    with open("rollen_log.txt", "r") as rollen_log:
        for line in rollen_log:
            if line == (player + " = " + rolle + "\n"):
                list_for_the_log.append(player + " = " + "Tot" + "\n")
                statement = player + " wurde getötet."
            else:
                if statement is None:
                    statement = "Der Spieler " + player + " ist unbekannt."
                list_for_the_log.append(line)

        rollen_log.close()
        with open("rollen_log.txt", "w+") as rollen_log_write:
            for line in list_for_the_log:
                rollen_log_write.write(line)
            rollen_log_write.close()
            schreibe_zuletzt_gestorben(player)

        return statement


def in_log_schreiben(a: str):
    """This function writes a line to the logfile

    Args:
        a (str): what to write to the logfile
    """
    with open("logfile.txt", "a", encoding="UTF8") as logfile:
        now = datetime.now().strftime("%H:%M:%S")

        logfile.write(str(now) + str(" >> " + a) + "\n")
        logfile.close()


def spieler_gestorben(player: str) -> str:
    """This function performs actions if the player is dead"""

    rolle = momentane_rolle(player)
    if rolle == "Tot":
        return "err"

    if rolle in liste_tot_mit_aktion and aktion_verfuegbar_ist_tot(player) is True:

        # TODO: #33 Aktionen für Hexe und Jaeger während des Todes

        if rolle == "Hexe":
            toete_spieler(player)
            return "h"  # hexe_aktion()

        if rolle == "Jaeger":
            toete_spieler(player)
            return "j"  # jaeger_aktion()

    elif ist_verliebt(player) is True:
        verliebte_toeten()
        return "v"  # verliebte_sind_tot

    elif rolle in liste_tot_ohne_aktion:
        toete_spieler(player)
        return str(0)  # keine Aktion, player ist jetzt tot


def spieler_ist_tot(player: str) -> bool:
    """This function checks if the player is dead"""
    if momentane_rolle(player) == "Tot":
        return True
    return False
