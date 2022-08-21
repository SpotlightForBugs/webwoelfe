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
        """
        The assignment function is a helper function that is used to assign the
        randomly generated number to the appropriate key in the dictionary. The while loop
        continues until all values are assigned and there are no more keys left in the dictionary.
        The for loop iterates through each key, checks if it has been assigned yet, and assigns it if not.

        :return: The index of a random key in the dictionary

        """
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
    """
    The validiere_rolle function checks if the player is already in the log file.
    If so, it returns True. Otherwise, it returns False.

    :param name:str: Store the name of the player
    :param rolle:str: Check if the name and role combination is already in the log file
    :return: True if the player is already in the log file

    """
    # create a string with the name and the role
    wort = ("'" + name + " = " + rolle + "\n'").encode("unicode_escape").decode("utf-8")
    file = open("rollen_log.txt", "r")  # open the log file
    players_vorhanden = str(file.readlines())  # read the log file
    if wort in players_vorhanden:
        return True
    return False


def validiere_rolle_original(name: str, rolle: str) -> bool:
    """
    The validiere_rolle_original function checks if the given name and role are already in the log file.


    :param name:str: Store the name of the player
    :param rolle:str: Check if the role is already in the log file
    :return: True if the name and role are in the log file

    """
    # create a string with the name and the role
    wort = ("'" + name + " = " + rolle + "\n'").encode("unicode_escape").decode("utf-8")
    file = open("rollen_original.txt", "r")  # open the log file
    players_vorhanden = str(file.readlines())  # read the log file
    if wort in players_vorhanden:
        return True
    return False


def validiere_name(name: str) -> bool:
    """
    The validiere_name function checks if the name of a player is already in use.
    It returns True if the name is already used and False otherwise.

    :param name:str: Set the name of the player
    :return: True if the name is in the log file and false otherwise

    """
    wort = ("'" + name + " = ").encode("unicode_escape").decode("utf-8")
    file = open("rollen_log.txt", "r")  # open the log file
    players_vorhanden = str(file.readlines())  # read the log file
    if wort in players_vorhanden:
        return True
    return False


def hexe_verbraucht(flag: str):
    """
    The hexe_verbraucht function removes the flag from the list of flags that
    the hexe can use. The function takes one argument, a string containing either
    a 't' or an 'h'. If it contains a 't', then it removes flag 2 from the list of
    flags that she can use. If it contains an 'h', then it removes flag 1 from her
    list of flags.

    :param flag:str: Determine the action of the function
    :return: The following:

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
    """
    The hexe_darf_toeten function checks if the hexe can kill.

    :returns: True if the hexe can kill, False otherwise.


    :return: A boolean value

    """
    """ This function checks if the hexe can kill"""
    with open("hexe_kann.txt", "r") as hexe_kann:
        hexe_kann_text = hexe_kann.read()
        if str(2) in hexe_kann_text:
            hexe_kann.close()
            return True
        hexe_kann.close()
        return False


def hexe_darf_heilen() -> bool:
    """
    The hexe_darf_heilen function checks if the hexe can heal.
    It does this by reading from a file called &quot;hexe_kann.txt&quot; which contains either a 1 or 0, depending on whether or not the hexe can heal.

    :return: True if the hexe can heal

    """
    with open("hexe_kann.txt", "r") as hexe_kann:
        hexe_kann_text = hexe_kann.read()
        if "1" in hexe_kann_text:
            hexe_kann.close()
            return True
        hexe_kann.close()
        return False


def armor_darf_auswaehlen() -> bool:

    """
    The armor_darf_auswaehlen function checks if the player has already selected an armor.
    If not, it returns True and the player can select an armor. If yes, it returns False and
    the player cannot select another armor.

    :return: True if the armor_kann

    """
    with open("armor_kann.txt", "r") as armor_kann:
        armor_kann_text = armor_kann.read()
        if "1" in armor_kann_text:
            armor_kann.close()
            return True
        armor_kann.close()
        return False


def jaeger_darf_toeten() -> bool:
    """
    The jaeger_darf_toeten function checks whether the Jaeger can kill

    :returns: True if the Jaeger can kill, False otherwise.


    :return: A boolean value

    """
    with open("jaeger_kann.txt", "r") as jaeger_kann:
        jaeger_kann_text = jaeger_kann.read()
        if "1" in jaeger_kann_text:
            jaeger_kann.close()
            return True
        jaeger_kann.close()
        return False


def jaeger_fertig():
    """
    The jaeger_fertig function is used to set the jaeger_kann.txt file to 0 and the jaeger can not kill somebody anymore
    :return: The string &quot;0&quot;

    """
    # jaeger_kann.txt mit 0 ersetzen
    with open("jaeger_kann.txt", "w") as jaeger_kann:
        jaeger_kann.write("0")
        jaeger_kann.close()


def armor_fertig(player1: str, player2: str):
    """
    The armor_fertig function adds a line to the verliebt.txt file and replaces the armor_kann.txt file with 0.

    :param player1:str: Store the name of the first player
    :param player2:str: Determine the name of the player that is going to be added to the list
    :return: The following:

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
    """
    The ist_verliebt function checks if the player is verliebt

    :param name:str: Define the name of the player
    :return: True if the player is verliebt, otherwise it returns false

    """
    with open("verliebt.txt", "r") as verliebt:
        verliebt_text = verliebt.read()
        if "+" + name in verliebt_text:
            verliebt.close()
            return True
        verliebt.close()
        return False


def leere_dateien():
    """
    The leere_dateien function clears the following files:
        - rollen_log.txt
        - abstimmung.txt
        - rollen_original.txt
        - hat_gewaehlt.txt


    :return: Nothing

    """
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
    """
    The momentane_rolle function returns the current role of a player.



    :param player:str: Get the name of the player whose role is to be returned
    :return: The current role of the player

    """
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
    """
    The fruehere_rolle function returns the previous role of a player, before dying.



    :param player:str: Pass the name of the player to the function
    :return: The previous role of the player, before dying

    """
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
    """
    The war_oder_ist_rolle function checks whether a player is currently or was previously in the given role.
    It returns True if they are, False otherwise.

    :param player:str: Specify the player whose role is to be checked
    :param rolle:str: Check if the player is in the specified role
    :return: True if the player is in the role or was in that role before

    """
    if momentane_rolle(player) == rolle or fruehere_rolle(player) == rolle:
        return True
    return False


def aktion_verfuegbar_ist_tot(player: str) -> bool:
    """
    The aktion_verfuegbar_ist_tot function checks if the player can do an action.
    It checks if the player is a witch, and if she can kill someone. If not, it checks
    if the player is a hunter and he can kill someone.

    :param player:str: Check if the player is a hunter or witch
    :return: True if the player can do an action

    """
    """ This function checks if the player can do an action"""

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
    """
    The zufallszahl function returns a random integer between the specified minimum and maximum values.
       The function takes two arguments, both integers: minimum and maximum.
       It returns an integer.

    :param minimum:int: Set the lowest possible number and the maximum:int parameter is used to set the highest possible number
    :param maximum:int: Set the upper limit of the random number
    :return: A random integer between the minimum and maximum value

    """
    return random.randint(minimum, maximum)


def verliebte_toeten() -> str:
    """
    The verliebte_toeten function takes the names of two players and writes them to a file.
    The function then reads the file and checks if either player is in it. If so, it replaces their name with &quot;Tot&quot;.
    Finally, the function returns a string containing both names.

    :return: The names of the two players who are dead

    """
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
    """
    The schreibe_zuletzt_gestorben function writes the last dead player to the logfile

    :param player:str: Write the name of the player who died last to a file
    :return: None

    """
    with open("letzter_tot.txt", "r+") as letzter_tot_w:
        letzter_tot_w.write(player)


# Tötet den gewählten Spieler


def toete_spieler(player):
    """
    The toete_spieler function takes a player as an argument and changes the role of that player to &quot;Tot&quot; in the rollen_log.txt file.
    It also writes down when that player was killed.

    :param player: Identify the player who is to be killed
    :return: The following:

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
    """
    The in_log_schreiben function writes a string to the logfile.txt file.

    :param a:str: Pass the string to be written into the logfile
    :return: The string &quot;true&quot;

    """
    with open("logfile.txt", "a", encoding="UTF8") as logfile:
        now = datetime.now().strftime("%H:%M:%S")

        logfile.write(str(now) + str(" >> " + a) + "\n")
        logfile.close()


def spieler_gestorben(player: str) -> str:
    """
    The spieler_gestorben function performs actions if the player is dead.



    :param player:str: Identify the player that is dead
    :return: A string

    """
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
