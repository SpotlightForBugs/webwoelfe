<!-- markdownlint-disable -->

<a href="../werwolf.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `werwolf.py`




**Global Variables**
---------------
- **liste_tot_mit_aktion**
- **liste_tot_ohne_aktion**

---

<a href="../werwolf.py#L11"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `createDict`

```python
createDict()
```

The createDict function creates a dictionary that assigns the number of players to each role. It takes no arguments and returns a dictionary with the keys: Werwolf, Hexe, Seherin, Armor, Jaeger and Dorfbewohner. The values are integers representing how many players have that role. 

:return: A dictionary that assigns the number of players to each role 


---

<a href="../werwolf.py#L88"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `deduct`

```python
deduct()
```

The deduct function is used to deduct a random key from the dictionary. It is called by the main function and returns a value that is then assigned to the variable 'rollen_zuweisung'. The function iterates through each key in the dictionary, checks if it has been assigned yet, and assigns it if not. If all values are 0 or less, then no keys remain in the dictionary and an empty string is returned. 

:return: The index of a random key in the dictionary 


---

<a href="../werwolf.py#L136"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `validiere_rolle`

```python
validiere_rolle(name: str, rolle: str) → bool
```

The validiere_rolle function checks if the player is already in the log file. If so, it returns True. Otherwise, it returns False. 

:param name:str: Store the name of the player :param rolle:str: Check if the name and role combination is already in the log file :return: True if the player is already in the log file 


---

<a href="../werwolf.py#L155"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `validiere_rolle_original`

```python
validiere_rolle_original(name: str, rolle: str) → bool
```

The validiere_rolle_original function checks if the given name and role are already in the log file. 



:param name:str: Store the name of the player :param rolle:str: Check if the role is already in the log file :return: True if the name and role are in the log file 


---

<a href="../werwolf.py#L174"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `validiere_name`

```python
validiere_name(name: str) → bool
```

The validiere_name function checks if the name of a player is already in use. It returns True if the name is already used and False otherwise. 

:param name:str: Set the name of the player :return: True if the name is in the log file and false otherwise 


---

<a href="../werwolf.py#L191"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `hexe_verbraucht`

```python
hexe_verbraucht(flag: str)
```

The hexe_verbraucht function removes the flag from the list of flags that the hexe can use. The function takes one argument, a string containing either a 't' or an 'h'. If it contains a 't', then it removes flag 2 from the list of flags that she can use. If it contains an 'h', then it removes flag 1 from her list of flags. 

:param flag:str: Determine the action of the function :return: The following: 


---

<a href="../werwolf.py#L223"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `hexe_darf_toeten`

```python
hexe_darf_toeten() → bool
```

The hexe_darf_toeten function checks if the hexe can kill. 

:returns: True if the hexe can kill, False otherwise. 



:return: A boolean value 


---

<a href="../werwolf.py#L242"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `hexe_darf_heilen`

```python
hexe_darf_heilen() → bool
```

The hexe_darf_heilen function checks if the hexe can heal. It does this by reading from a file called &quot;hexe_kann.txt&quot; which contains either a 1 or 0, depending on whether or not the hexe can heal. 

:return: True if the hexe can heal 


---

<a href="../werwolf.py#L259"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `armor_darf_auswaehlen`

```python
armor_darf_auswaehlen() → bool
```

The armor_darf_auswaehlen function checks if the armor has already selected the lovers. If not, it returns True. Otherwise, it returns False. 

:return: True if the armor can be selected and false otherwise 


---

<a href="../werwolf.py#L276"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `jaeger_darf_toeten`

```python
jaeger_darf_toeten() → bool
```

The jaeger_darf_toeten function checks whether the Jaeger can kill 

:returns: True if the Jaeger can kill, False otherwise. 



:return: A boolean value 


---

<a href="../werwolf.py#L295"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `jaeger_fertig`

```python
jaeger_fertig()
```

The jaeger_fertig function is used to set the jaeger_kann.txt file to 0 and the jaeger can not kill somebody anymore :return: The string &quot;0&quot; 


---

<a href="../werwolf.py#L307"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `armor_fertig`

```python
armor_fertig(player1: str, player2: str)
```

The armor_fertig function adds a line to the verliebt.txt file and replaces the armor_kann.txt file with 0. 

:param player1:str: Store the name of the first player :param player2:str: Determine the name of the player that is going to be added to the list :return: The following: 


---

<a href="../werwolf.py#L335"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `verliebte_ausgeben`

```python
verliebte_ausgeben() → str
```

The verliebte_ausgeben function reads the verliebt.txt file and returns its content. 

:return: The content of the verliebt.txt file 


---

<a href="../werwolf.py#L354"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `ist_verliebt`

```python
ist_verliebt(name: str) → bool
```

The ist_verliebt function checks if the player is verliebt 

:param name:str: Define the name of the player :return: True if the player is verliebt, otherwise it returns false 


---

<a href="../werwolf.py#L371"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `leere_dateien`

```python
leere_dateien()
```






---

<a href="../werwolf.py#L403"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `momentane_rolle`

```python
momentane_rolle(player: str) → str
```

The momentane_rolle function returns the current role of a player. 





:param player:str: Get the name of the player whose role is to be returned :return: The current role of the player 


---

<a href="../werwolf.py#L426"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `fruehere_rolle`

```python
fruehere_rolle(player: str) → str
```

The fruehere_rolle function returns the previous role of a player, before dying. 





:param player:str: Pass the name of the player to the function :return: The previous role of the player, before dying 


---

<a href="../werwolf.py#L451"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `war_oder_ist_rolle`

```python
war_oder_ist_rolle(player: str, rolle: str) → bool
```

The war_oder_ist_rolle function checks whether a player is currently or was previously in the given role. It returns True if they are, False otherwise. 

:param player:str: Specify the player whose role is to be checked :param rolle:str: Check if the player is in the specified role :return: True if the player is in the role or was in that role before 


---

<a href="../werwolf.py#L466"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `aktion_verfuegbar_ist_tot`

```python
aktion_verfuegbar_ist_tot(player: str) → bool
```

The aktion_verfuegbar_ist_tot function checks if the player can do an action. It checks if the player is a witch, and if she can kill someone. If not, it checks if the player is a hunter and he can kill someone. 

:param player:str: Check if the player is a hunter or witch :return: True if the player can do an action 


---

<a href="../werwolf.py#L487"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `zufallszahl`

```python
zufallszahl(minimum: int, maximum: int) → int
```

The zufallszahl function returns a random integer between the specified minimum and maximum values.  The function takes two arguments, both integers: minimum and maximum.  It returns an integer. 

:param minimum:int: Set the lowest possible number and the maximum:int parameter is used to set the highest possible number :param maximum:int: Set the upper limit of the random number :return: A random integer between the minimum and maximum value 


---

<a href="../werwolf.py#L501"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `verliebte_toeten`

```python
verliebte_toeten() → str
```

The verliebte_toeten function takes the names of two players and writes them to a file. The function then reads the file and checks if either player is in it. If so, it replaces their name with &quot;Tot&quot;. Finally, the function returns a string containing both names. 

:return: The names of the two players who are dead 


---

<a href="../werwolf.py#L556"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `schreibe_zuletzt_gestorben`

```python
schreibe_zuletzt_gestorben(player: str) → None
```

The schreibe_zuletzt_gestorben function writes the last dead player to the logfile 

:param player:str: Write the name of the player who died last to a file :return: None 


---

<a href="../werwolf.py#L571"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `toete_spieler`

```python
toete_spieler(player)
```

The toete_spieler function takes a player as an argument and changes the role of that player to &quot;Tot&quot; in the rollen_log.txt file. It also writes down when that player was killed. 

:param player: Identify the player who is to be killed :return: The following: 


---

<a href="../werwolf.py#L604"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `log`

```python
log(debug: bool)
```

The log function writes a string to the logfile.txt file, which is used by the debug function to determine whether or not debug mode is on. If it's off, then the logfile will be wiped clean so that way it doesn't interfere with any future debugging efforts. 

:param debug:bool: Decide whether or not to write a logfile :return: A none object 


---

<a href="../werwolf.py#L622"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `in_log_schreiben`

```python
in_log_schreiben(a: str)
```

The in_log_schreiben function writes a string to the logfile.txt file. It takes one argument, which is a string. 

:param a:str: Pass the message to be logged :return: The result of the function 


---

<a href="../werwolf.py#L642"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `spieler_gestorben`

```python
spieler_gestorben(player: str) → str
```

The spieler_gestorben function performs actions if the player is dead. 





:param player:str: Identify the player that is dead :return: A string 


---

<a href="../werwolf.py#L679"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `spieler_ist_tot`

```python
spieler_ist_tot(player: str) → bool
```

The spieler_ist_tot function checks if the player is dead 

:param player:str: Identify the player :return: A boolean value 


---

<a href="../werwolf.py#L692"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `name_richtig_schreiben`

```python
name_richtig_schreiben(name: str) → str
```

The name_richtig_schreiben function takes a string and returns the same string with all non-alphanumeric characters replaced by underscores. 



:param name:str: Pass the name of the file to be renamed :return: The name with the correct capitalization 


---

<a href="../werwolf.py#L825"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `suche_spieler`

```python
suche_spieler() → bool
```

The suche_spieler function checks if the number of players is bigger than the number of lines in rollen_original.txt. If this is true, then it returns True, else False. 

:return: True if the number of players is greater than the number of roles 


---

<a href="../werwolf.py#L840"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `generiere_token`

```python
generiere_token(name: str, rolle: str) → str
```

The generiere_token function generates a token for the user. It checks if the role is valid and if it is not already in use. If this condition is met, a new token will be generated and written to tokens.txt 

:param name:str: Specify the name of the user :param rolle:str: Check if the role is valid :return: A token 


---

<a href="../werwolf.py#L860"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `validiere_token`

```python
validiere_token(token: str) → bool
```

The validiere_token function checks if the token is in the file tokens.txt  and returns True if it is, False otherwise. 

:param token:str: Check if the token is in the file :return: True if the token is in the file, otherwise it returns false 


---

<a href="../werwolf.py#L874"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `name_und_rolle_aus_token`

```python
name_und_rolle_aus_token(token: str)
```

The name_und_rolle_aus_token function takes a token as input and returns the name and role of the user who has this token. The function reads the file tokens.txt, checks if the given token is in this file and splits it at every + to return the name and role of that user. 

:param token:str: Check if the token is in the file tokens :return: The name and the role of a token 


---

<a href="../werwolf.py#L892"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `loesche_token`

```python
loesche_token(token)
```

The loesche_token function deletes a token from the file tokens.txt 



:param token: Check if the token is in the file :return: The name and the role of the token 


---

<a href="../werwolf.py#L915"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `rolle_aus_token`

```python
rolle_aus_token(token: str)
```

The rolle_aus_token function takes a token as an argument and returns the role of the user associated with that token. The function reads from a file called tokens.txt, which contains all valid tokens and their corresponding roles. 

:param token:str: Check if the token is in the file :return: The role of the token 


---

<a href="../werwolf.py#L932"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `name_aus_token`

```python
name_aus_token(token: str)
```

The name_aus_token function takes a token and returns the name of the person who has that token.  If no one has that token, it returns None. 

:param token:str: Pass the token of a user to the function :return: The name of the token if it is in tokens 


---

<a href="../werwolf.py#L949"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `status_aus_token`

```python
status_aus_token(token: str)
```

The status_aus_token function checks if the token is in the file tokens.txt and returns the status of the token if it is in the file. 

:param token:str: Pass the token of the user that is checked :return: The status of the token 


---

<a href="../werwolf.py#L967"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `token_aus_name_und_rolle`

```python
token_aus_name_und_rolle(name: str, rolle: str) → str
```

The token_aus_name_und_rolle function takes a name and a role as input. It checks if the given name and role are valid, and returns the token of that player if it is. If not, it returns an error message. 

:param name:str: Specify the name of the player :param rolle:str: Check if the rolle is valid :return: The token for the player name and role 


---

<a href="../werwolf.py#L991"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `ist_token_vorhandem`

```python
ist_token_vorhandem(name, rolle)
```

The ist_token_vorhandem function checks if the token is in the file tokens.txt 

:param name: Check if the token is in the file :param rolle: Check if the token is in the file :return: True if the token is in the file, otherwise false 


---

<a href="../werwolf.py#L1009"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `setze_status`

```python
setze_status(token: str, status: str)
```

The setze_status function sets the status of a user to active or inactive. It takes two arguments: token and status. The token is the unique identifier for each user,  and it is used to find the correct line in tokens.txt where their information is stored.  The status argument can be either &quot;active&quot; or &quot;inactive&quot;. If it's set to active, then all lines containing that token will have their last column changed from an inactive string (e.g., 'inactive') to an active string (e.g., 'active'). If it's set to inactive, then all lines containing that token will have their 

:param token:str: Check if the token is in the file :param status:str: Set the status of a user :return: Nothing 


---

<a href="../werwolf.py#L1053"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `setze_status_fuer_rolle`

```python
setze_status_fuer_rolle(rolle: str, status: str)
```

The setze_status_fuer_rolle function sets the status of a role to active or inactive. It takes two arguments: rolle and status. The function reads the file tokens.txt and checks if  the token is in the file, then it splits the line at + signs, returning only name, role and  status from that line. 

:param rolle:str: Specify the role that should be set to a specific status :param status:str: Set the status of a role :return: The status of the specified role 


---

<a href="../werwolf.py#L1097"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `setze_status_fuer_name`

```python
setze_status_fuer_name(name: str, status: str)
```

The setze_status_fuer_name function sets the status of a user to active or inactive. It takes two arguments: name and status. The function reads the file tokens.txt and checks if  the token is in the file, then it splits the line at + and returns name and role. 

:param name:str: Specify the name of the user that should be changed :param status:str: Set the status of a user :return: None 


---

<a href="../werwolf.py#L1140"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `setze_status_fuer_alle`

```python
setze_status_fuer_alle(status: str)
```

The setze_status_fuer_alle function sets the status of all roles to a given value. It reads the file tokens.txt and checks if the token is in the file, then it sets  the status for that role to a given value. 

:param status:str: Set the status for all roles to a given value :return: None 


---

<a href="../werwolf.py#L1175"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `actions`

```python
actions(action: str)
```

The actions function is used to set the status of all players. The following order is used: 0 = dead, 1 = sleep, 2 = action, 3 = vote, 4 = information 

:param action:str: Call the function actions(action:str) :return: The following: 


---

<a href="../werwolf.py#L1248"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `erhalte_ziel`

```python
erhalte_ziel(token: str) → str
```

The erhalte_ziel function returns the URL of the dashboard for a given player. The function takes one argument, which is a token string. 



:param token:str: Get the role of the player :return: The path to the next page of the player 


---

<a href="../werwolf.py#L1282"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `nurNamen`

```python
nurNamen() → list
```

The nurNamen function creates a list of all the names in the log file. It does this by reading every line in the log file and checking if it contains a * or not. If it does contain a *, nothing happens. If it doesn't contain one, then we split at = and take  the first part of that line (which is always the name) and append that to our nurNamen list. 

:return: A list with the names of all players that are not dead or the narrator 




---

_This file was automatically generated via [lazydocs](https://github.com/ml-tooling/lazydocs)._
