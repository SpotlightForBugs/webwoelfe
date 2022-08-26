from datetime import datetime
import json
import random
import ast
import re
import secrets


liste_tot_mit_aktion = ["Jaeger", "Hexe", "PLATZHALTER"]
liste_tot_ohne_aktion = ["Dorfbewohner", "Werwolf", "Seherin"]


def createDict():
    """
    The createDict function creates a dictionary that assigns the number of players to each role.
    It takes no arguments and returns a dictionary with the keys: Werwolf, Hexe, Seherin, Armor, Jaeger and Dorfbewohner.
    The values are integers representing how many players have that role.

    :return: A dictionary that assigns the number of players to each role

    """
    with open("spieler_anzahl.txt", "r") as f:
        spieleranzahl = f.read()
    try:
        spieleranzahl = int(spieleranzahl)
    except ValueError:
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
    The deduct function is used to deduct a random key from the dictionary.
    It is called by the main function and returns a value that is then assigned
    to the variable 'rollen_zuweisung'. The function iterates through each key in
    the dictionary, checks if it has been assigned yet, and assigns it if not. If all values are 0 or less,
    then no keys remain in the dictionary and an empty string is returned.

    :return: The index of a random key in the dictionary

    """
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
    with open("rollen_log.txt", "r") as file:  # open the log file
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
    with open("rollen_original.txt", "r") as file:  # open the log file
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
    with open("rollen_log.txt", "r") as file:  # open the log file
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
    The armor_darf_auswaehlen function checks if the armor has already selected the lovers.
    If not, it returns True. Otherwise, it returns False.

    :return: True if the armor can be selected and false otherwise

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


def verliebte_ausgeben() -> str:
    """
    The verliebte_ausgeben function reads the verliebt.txt file and returns its content.

    :return: The content of the verliebt.txt file

    """
    with open("verliebt.txt", "r") as verliebt:
        verliebt_text = verliebt.read()
        if verliebt_text.count("+") == 2:
            return "+" + verliebt_text.split("+")[1] +"+"+ verliebt_text.split("+")[2] + "+"


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

    with open("rollen_log.txt", "w+", encoding="UTF8") as f:  # leere rollen_log.txt
        f.write("*********************\n")
    with open("abstimmung.txt", "r+", encoding="UTF8") as file:
        file.truncate(0)
    file.close()
    with open("rollen_original.txt", "r+", encoding="UTF8") as file2:
        file2.truncate(0)
    file2.close()
    with open("hat_gewaehlt.txt", "r+", encoding="UTF8") as file3:
        file3.truncate(0)
    file3.close()
    with open("hexe_kann.txt", "w", encoding="UTF8") as file4:
        file4.write(str(12))
    file4.close()
    with open("armor_kann.txt", "w", encoding="UTF8") as file5:
        file5.write(str(1))
    file5.close()
    with open("verliebt.txt", "w", encoding="UTF8") as file6:
        file6.write(str(""))
    file6.close()
    with open("jaeger_kann.txt", "w", encoding="UTF8") as file7:
        file7.write(str(1))
    file7.close()
    with open("logfile.txt", "w", encoding="UTF8") as file8:
        file8.truncate(0)
    file8.close()
    with open("tokens.txt", "w", encoding="UTF8") as file9:
        file9.truncate(0)


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
    if war_oder_ist_rolle(player, "Hexe") is True:
        if hexe_darf_toeten() is True:
            return True
        return False
    if war_oder_ist_rolle(player, "Jaeger") is True:
        if jaeger_darf_toeten() is True:
            return True
        return False
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

        if ist_verliebt(player) is True:
            verliebte_toeten()
            return "v"  # verliebte_sind_tot

        if rolle in liste_tot_ohne_aktion:
            toete_spieler(player)
            return str(0)  # keine Aktion, player ist jetzt tot
        return "err"
    return "err"


def spieler_ist_tot(player: str) -> bool:
    """
    The spieler_ist_tot function checks if the player is dead

    :param player:str: Identify the player
    :return: A boolean value

    """
    if momentane_rolle(player) == "Tot":
        return True
    return False


def name_richtig_schreiben(name: str) -> str:
    """
    The name_richtig_schreiben function takes a string as input and returns the same string with
    the following changes:
    - replaces &quot;/&quot; with &quot;_&quot;
    - replaces &quot;=&quot; with &quot;-&quot;
    - replaces &quot;:&quot; with &quot;_&quot;
    - replaces &quot;*&quot; with &quot;_&quot;

        - replace &quot;&lt;&quot;, &gt;, ?, &quot;, \, |, . , ' , / , : , * ,&quot; in name by _.

    :param name:str: Pass the name of the file to be renamed
    :return: The name with the correct spelling

    """
    name = name.replace("/", "_")
    name = name.replace("=", "-")
    name = name.replace(":", "_")
    name = name.replace("*", "_")

    name = name.replace("<", "_")
    name = name.replace(">", "_")
    name = name.replace("?", "_")
    name = name.replace('"', "_")
    name = name.replace("\\", "_")
    name = name.replace("|", "_")
    name = name.replace(".", "_")
    name = name.replace(" ", "_")
    name = name.replace("\n", "_")
    name = name.replace("\t", "_")
    name = name.replace("\r", "_")
    name = name.replace("\v", "_")
    name = name.replace("\f", "_")
    name = name.replace("\b", "_")
    name = name.replace("\a", "_")
    name = name.replace("\e", "_")
    name = name.replace("\0", "_")
    name = name.replace("\x0b", "_")
    name = name.replace("\x0c", "_")
    name = name.replace("\x0e", "_")
    name = name.replace("\x0f", "_")
    name = name.replace("\x10", "_")
    name = name.replace("\x11", "_")
    name = name.replace("\x12", "_")
    name = name.replace("\x13", "_")
    name = name.replace("\x14", "_")
    name = name.replace("\x15", "_")
    name = name.replace("\x16", "_")
    name = name.replace("\x17", "_")
    name = name.replace("\x18", "_")
    name = name.replace("\x19", "_")
    name = name.replace("\x1a", "_")
    name = name.replace("\x1b", "_")
    name = name.replace("\x1c", "_")
    name = name.replace("\x1d", "_")
    name = name.replace("\x1e", "_")
    name = name.replace("\x1f", "_")

    name = name.replace("ä", "ae")
    name = name.replace("ö", "oe")
    name = name.replace("ü", "ue")
    name = name.replace("Ä", "Ae")
    name = name.replace("Ö", "Oe")
    name = name.replace("Ü", "Ue")
    name = name.replace("ß", "ss")
    name = name.replace("À", "A")
    name = name.replace("Á", "A")
    name = name.replace("Â", "A")
    name = name.replace("Ã", "A")
    name = name.replace("Ä", "A")
    name = name.replace("Å", "A")
    name = name.replace("Æ", "A")
    name = name.replace("Ç", "C")
    name = name.replace("È", "E")
    name = name.replace("É", "E")
    name = name.replace("Ê", "E")
    name = name.replace("Ë", "E")
    name = name.replace("Ì", "I")
    name = name.replace("Í", "I")
    name = name.replace("Î", "I")
    name = name.replace("Ï", "I")
    name = name.replace("Ñ", "N")
    name = name.replace("Ò", "O")
    name = name.replace("Ó", "O")
    name = name.replace("Ô", "O")
    name = name.replace("Õ", "O")
    name = name.replace("Ö", "O")
    name = name.replace("Ø", "O")
    name = name.replace("Ù", "U")
    name = name.replace("Ú", "U")
    name = name.replace("Û", "U")
    name = name.replace("Ü", "U")
    name = name.replace("Ý", "Y")
    name = name.replace("à", "a")
    name = name.replace("á", "a")
    name = name.replace("â", "a")
    name = name.replace("ã", "a")
    name = name.replace("@", "at")
    name = name.replace("€", "EURO")
    name = name.replace("$", "USD")
    name = name.replace("£", "GBP")
    name = name.replace("¥", "JPY")
    name = name.replace("¤", "USD")
    name = name.replace("¦", "B")
    name = name.replace("§", "S")
    name = name.replace("©", "C")
    name = name.replace("ª", "A")
    name = name.replace("«", "<<")
    name = name.replace("¬", "!")
    name = name.replace("­", "-")
    name = name.replace("®", "R")
    name = name.replace("¯", "^")
    name = name.replace("°", "o")
    name = name.replace("±", "+")
    name = name.replace("²", "2")
    name = name.replace("³", "3")
    name = name.replace("´", "'")
    name = name.replace("µ", "u")

    # use regex to replace all non-alphanumeric characters with _
    name = re.sub(r"[^a-zA-Z0-9]", "_", name)
    return name.capitalize()


def suche_spieler() -> bool:
    """
    The suche_spieler function checks if the number of players is bigger than the number of lines in rollen_original.txt.
    If this is true, then it returns True, else False.

    :return: True if the number of players is greater than the number of roles

    """

    with open("spieler_anzahl.txt", "r") as file:
        for line in file:
            if int(line) > len(open("rollen_original.txt", "r").readlines()):
                return True
            else:
                return False


def generiere_token(name: str, rolle: str) -> str:
    """
    The generiere_token function generates a token for the user.
    It checks if the role is valid and if it is not already in use.
    If this condition is met, a new token will be generated and written to tokens.txt

    :param name:str: Specify the name of the user
    :param rolle:str: Check if the role is valid
    :return: A token

    """
    if validiere_rolle_original(name, rolle):
        if not ist_token_vorhandem(name, rolle):

            token = secrets.token_hex(16)
            # write the token and the name and the role to the file tokens.txt
            with open("tokens.txt", "a", encoding="UTF8") as file:
                file.write("+" + token + "+" + name + "+" + rolle + "+1+ \n")
                return token


def validiere_token(token: str) -> bool:
    """
    The validiere_token function checks if the token is in the file tokens.txt
       and returns True if it is, False otherwise.

    :param token:str: Check if the token is in the file
    :return: True if the token is in the file, otherwise it returns false

    """
    # read the file tokens.txt and check if the token is in the file
    with open("tokens.txt", "r") as file:
        for line in file:
            if "+" + token + "+" in line:
                return True

        return False


def name_und_rollen_aus_token(token: str):
    """
    The name_und_rollen_aus_token function takes a token as input and returns the name and role of the user who has this token.
    The function reads the file tokens.txt, checks if the given token is in this file and splits it at every + to return
    the name and role of that user.

    :param token:str: Check if the token is in the file tokens
    :return: The name and the role of a token

    """
    # read the file tokens.txt and check if the token is in the file
    with open("tokens.txt", "r") as file:
        for line in file:
            if "+" + token + "+" in line:
                # split the line at the + and return the name and the role
                return line.split("+")[1], line.split("+")[2]


def loesche_token(token):
    """
    The loesche_token function deletes a token from the file tokens.txt


    :param token: Check if the token is in the file
    :return: The name and the role of the token

    """
    # read the file tokens.txt and check if the token is in the file
    with open("tokens.txt", "r") as file:
        for line in file:
            if "+" + token + "+" in line:
                # split the line at the + and return the name and the role
                file.close()
                with open("tokens.txt", "r") as file:
                    lines = file.readlines()
                with open("tokens.txt", "w") as file:
                    for line in lines:
                        if "+" + token + "+" not in line:
                            file.write(line)


def rolle_aus_token(token: str):
    """
    The rolle_aus_token function takes a token as an argument and returns the role of the user associated with that token.
    The function reads from a file called tokens.txt, which contains all valid tokens and their corresponding roles.

    :param token:str: Check if the token is in the file
    :return: The role of the token

    """
    # read the file tokens.txt and check if the token is in the file
    with open("tokens.txt", "r") as file:
        for line in file:
            if "+" + token + "+" in line:
                # split the line at the + and return the name and the role
                return line.split("+")[3]


def name_aus_token(token: str):
    """
    The name_aus_token function takes a token and returns the name of the person who has that token.
       If no one has that token, it returns None.

    :param token:str: Pass the token of a user to the function
    :return: The name of the token if it is in tokens

    """
    # read the file tokens.txt and check if the token is in the file
    with open("tokens.txt", "r") as file:
        for line in file:
            if "+" + token + "+" in line:
                # split the line at the + and return the name and the role
                return line.split("+")[2]


def status_aus_token(token: str):
    """
    The status_aus_token function checks if the token is in the file tokens.txt and returns
    the status of the token if it is in the file.

    :param token:str: Pass the token of the user that is checked
    :return: The status of the token

    """
    # read the file tokens.txt and check if the token is in the file
    with open("tokens.txt", "r") as file:
        for line in file:
            if line != "\n":
                if "+" + token + "+" in line and line.count("+") == 5:
                    # split the line at the + and return the name and the role
                    return line.split("+")[4]
        return "Fehler"


def token_aus_name_und_rolle(name: str, rolle: str) -> str:
    """
    The token_aus_name_und_rolle function takes a name and a role as input. It checks if the given name and role are valid,
    and returns the token of that player if it is. If not, it returns an error message.

    :param name:str: Specify the name of the player
    :param rolle:str: Check if the rolle is valid
    :return: The token for the player name and role

    """
    if validiere_rolle_original(name, rolle):
        # read the file tokens.txt and check if the token is in the file
        with open("tokens.txt", "r") as file:
            for line in file:
                if "+" + name + "+" + rolle + "+" in line:

                    # split the line at the + and return the name and the role

                    return line.split("+")[1]
    else:
        return "Spieler nicht gefunden"
    return "Kein Token gefunden"


def ist_token_vorhandem(name, rolle):
    """
    The ist_token_vorhandem function checks if the token is in the file tokens.txt

    :param name: Check if the token is in the file
    :param rolle: Check if the token is in the file
    :return: True if the token is in the file, otherwise false

    """
    # read the file tokens.txt and check if the token is in the file
    with open("tokens.txt", "r") as file:
        for line in file:
            if "+" + name + "+" + rolle + "+" in line:
                return True

    return False


def setze_status(token: str, status: str):
    # read the file tokens.txt and check if the token is in the file
    with open("tokens.txt", "r") as file:
        for line in file:
            if "+" + token + "+" in line:
                # split the line at the + and return the name and the role

                with open("tokens.txt", "r") as file:
                    lines = file.readlines()
                with open("tokens.txt", "w") as file:
                    for line in lines:
                        if "+" + token + "+" in line:
                            file.write(
                                line.split("+")[0]
                                + "+"
                                + line.split("+")[1]
                                + "+"
                                + line.split("+")[2]
                                + "+"
                                + line.split("+")[3]
                                + "+"
                                + status
                                + "+"
                                + line.split("+")[5]
                                + "\n"
                            )
                        else:
                            if line != "\n":  # if the line is not empty
                                file.write(line)  # write the line to the file
                            else:
                                file.write("")  # if the line is empty, write nothing


def setze_status_fuer_rolle(rolle: str, status: str):
    # read the file tokens.txt and check if the token is in the file
    with open("tokens.txt", "r") as file:
        for line in file:
            if "+" + rolle + "+" in line:
                # split the line at the + and return the name and the role

                with open("tokens.txt", "r") as file:
                    lines = file.readlines()
                with open("tokens.txt", "w") as file:
                    for line in lines:
                        if "+" + rolle + "+" in line:
                            file.write(
                                line.split("+")[0]
                                + "+"
                                + line.split("+")[1]
                                + "+"
                                + line.split("+")[2]
                                + "+"
                                + line.split("+")[3]
                                + "+"
                                + status
                                + "+"
                                + line.split("+")[5]
                                + "\n"
                            )
                        else:
                            if line != "\n":  # if the line is not empty
                                file.write(line)  # write the line to the file
                            else:
                                file.write("")  # if the line is empty, write nothing


def setze_status_fuer_name(name: str, status: str):
    # read the file tokens.txt and check if the token is in the file
    with open("tokens.txt", "r") as file:
        for line in file:
            if "+" + name + "+" in line:
                # split the line at the + and return the name and the role

                with open("tokens.txt", "r") as file:
                    lines = file.readlines()
                with open("tokens.txt", "w") as file:
                    for line in lines:
                        if "+" + name + "+" in line:
                            file.write(
                                line.split("+")[0]
                                + "+"
                                + line.split("+")[1]
                                + "+"
                                + line.split("+")[2]
                                + "+"
                                + line.split("+")[3]
                                + "+"
                                + status
                                + "+"
                                + line.split("+")[5]
                                + "\n"
                            )
                        else:
                            if line != "\n":  # if the line is not empty
                                file.write(line)  # write the line to the file
                            else:
                                file.write("")  # if the line is empty, write nothing


def setze_status_fuer_alle(status: str):
    # read the file tokens.txt and check if the token is in the file
    with open("tokens.txt", "r") as file:
        for line in file:
            # split the line at the + and return the name and the role

            with open("tokens.txt", "r") as file:
                lines = file.readlines()
            with open("tokens.txt", "w") as file:
                for line in lines:
                    file.write(
                        line.split("+")[0]
                        + "+"
                        + line.split("+")[1]
                        + "+"
                        + line.split("+")[2]
                        + "+"
                        + line.split("+")[3]
                        + "+"
                        + status
                        + "+"
                        + line.split("+")[5]
                        + "\n"
                    )


def actions(action: str):
    # es gibt verschiedene Stadien in denen sich ein Spieler befinden kann. Er kann schlafen, tot sein,eine information bekommen, eine Aktion haben oder Abstimmung haben.
    # Die Funktionen setze_status_fuer_rolle, setze_status_fuer_name und setze_status setzen den Status eines Spielers auf einen der oben genannten Stadien.
    # The following order is used: 0 = dead, 1 = sleep, 2 = action, 3 = vote, 4 = information

    if action == "alle_schlafen":
        setze_status_fuer_alle("1")
    # STARTUP On startup, the status of all players is set to sleeping

    # ARMOR After this, the status of the player with the role of the Armor is set to action
    elif action == "armor_aktion":
        setze_status_fuer_rolle("Armor", "2")
        
    elif action =="armor_schlafen":
        setze_status_fuer_rolle("Armor", "1")

    elif action == "verliebte_informieren":
        verliebte_ausgeben() # the function verliebte_ausgeben() returns the names in the following format: +lover1+lover2+
        lover1 = verliebte_ausgeben().split("+")[1]
        lover2 = verliebte_ausgeben().split("+")[2]
        setze_status_fuer_name(lover1, "4")
        setze_status_fuer_name(lover2, "4")


# After this, all players are set to sleep.

# SEHERIN The seherin is set to action
    elif action == "seherin_aktion":
        setze_status_fuer_rolle("Seherin", "2")

    elif action == "seherin_schlafen":
        setze_status_fuer_rolle("Seherin", "1")

    elif action == "werwolf_abstimmung":
        setze_status_fuer_rolle("Werwolf", "2")
# WERWOLF All werewolves are set to  vote

# All werewolves are set to sleep
    elif action == "werwolf_schlafen":
        setze_status_fuer_rolle("Werwolf", "1")

# The witch is set to action
    elif action == "hexe_aktion":
        setze_status_fuer_rolle("Hexe", "2")
# The witch is set to sleep
    elif action == "hexe_schlafen":
        setze_status_fuer_rolle("Hexe", "1")

# Everyone is set to vote
    elif action == "alle_abstimmen":
        setze_status_fuer_alle("3")



def erhalte_ziel(token: str):
    #1. get the role of the player
    rolle = rolle_aus_token(token)
    
    #2. get the name of the player
    name = name_aus_token(token)
    #3. get the status of the token
    status = status_aus_token(token)
    
    
    #  0 = dead, 1 = sleep, 2 = action, 3 = vote, 4 = information
    
    if status == "0":
        return (f'"/{name}/{rolle}/_/tot"')
    elif status == "1":
        return (f'/{name}/{rolle}/schlafen')
    elif status == "2":
        return (f'/{name}/{rolle}/Dashboard_sp')
    elif status == "3":
        return (f'/{name}/{rolle}/Dashboard')
    elif status == "4":
        return (f'/{name}/{rolle}/info')
        
    
    
        
