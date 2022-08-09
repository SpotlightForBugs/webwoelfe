import random, ast

def createDict():
    with open('spieler_anzahl.txt','r') as f:
         spieleranzahl = f.read()
    try:
            spieleranzahl = int(spieleranzahl)
    except:
            spieleranzahl = 8      #auf 8 defaulten
    with open('erzaehler_ist_zufaellig.txt','r') as fl:
        erzaehler_flag = int(fl.read())

    werwolf = spieleranzahl // 4
    hexe = spieleranzahl // 12
    seherin = spieleranzahl // 12
    armor = 1
    if hexe == 0 :
        hexe = 1
    if seherin == 0 :
        seherin = 1
    jaeger = 0
    if spieleranzahl >= 10:
        jaeger = 1

    if erzaehler_flag == 1:  
      #  print("erzaehler ist zufaellig")
        if jaeger > 0:
            assign = {'Erzaehler' : 1, 'Werwolf' : werwolf, 'Armor' : armor,  'Hexe' : hexe, 'Seherin' : seherin, 'Jaeger' : jaeger, 'Dorfbewohner' : (spieleranzahl-armor-werwolf-seherin-hexe-jaeger-1)} 
        else:
            assign = {'Erzaehler' : 1, 'Werwolf' : werwolf, 'Armor' : armor, 'Hexe' : hexe, 'Seherin' : seherin, 'Dorfbewohner' : (spieleranzahl-werwolf-seherin-hexe-armor-1)}
    elif erzaehler_flag == 0:
      #  print("erzaehler ist nicht vorhanden")
        if jaeger > 0:
            assign = {'Werwolf' : werwolf, 'Hexe' : hexe,'Armor' : armor, 'Seherin' : seherin, 'Jaeger' : jaeger, 'Dorfbewohner' : (spieleranzahl-werwolf-seherin-hexe-jaeger-armor)}
        else:
            assign = {'Werwolf' : werwolf, 'Hexe' : hexe, 'Armor' : armor, 'Seherin' : seherin, 'Dorfbewohner' : (spieleranzahl-werwolf-seherin-hexe-armor)}
    keys = [ key for key in assign]

    with open('rollen_zuweisung.txt', 'w+') as a:
        a.write(str(assign))

def deduct():
    with open('rollen_zuweisung.txt', 'r+') as a:
        assign = a.read()
        #print(assign)
        assign = ast.literal_eval(assign)
        #print(type(assign))
        keys = [ key for key in assign ]

    if sum(assign.values()) == 0:
        return(0)

    def assignment():
        while sum(assign.values()) >=0:
            num = random.randint(0,len(assign)-1)
            if assign[keys[num]] > 0:
                assign[keys[num]] -= 1
                if assign[keys[num]] == 0:
                    del assign[keys[num]]
                return num
            else:
                
                assignment()
    ind = assignment()
    print(assign)
    with open('rollen_zuweisung.txt', 'w+') as b:
        b.write(str(assign))
    result = keys[ind]
    return(result)

def validiere_rolle(name: str,rolle: str)->bool:
    wort = ("'" + name + " = " +rolle+ "\n'").encode("unicode_escape").decode("utf-8") # create a string with the name and the role
    file = open('rollen_log.txt', "r") #    open the log file
    players_vorhanden = str(file.readlines()) # read the log file
    if wort in players_vorhanden:
        return(True)
    else:
        return (False) 
    
def validiere_rolle_original(name: str,rolle: str)->bool:
    wort = ("'" + name + " = " +rolle+ "\n'").encode("unicode_escape").decode("utf-8") # create a string with the name and the role
    file = open('rollen_original.txt', "r") #    open the log file
    players_vorhanden = str(file.readlines()) # read the log file
    if wort in players_vorhanden:
        return(True)
    else:
        return (False) 
    
def validiere_name(name: str)->bool:
    wort = ("'" + name + " = ").encode("unicode_escape").decode("utf-8") # create a string with the name and the role
    file = open('rollen_log.txt', "r") #    open the log file
    players_vorhanden = str(file.readlines()) # read the log file
    if wort in players_vorhanden:
        return(True)
    else:
        return (False) 
    
def hexe_verbraucht(flag: str):
    
    if  "t" in flag or "T" in flag:
        flag = str(2)
    elif "h" in flag or "H" in flag:
        flag = str(1)
    
    
    
        if str(flag) == "1" or str(flag) == "2":
            with open ('hexe_kann.txt','r') as hexe_kann:
                hexe_kann_text = hexe_kann.read()
                hexe_kann_text = hexe_kann_text.replace(str(flag),'')
                hexe_kann.close()
            with open ('hexe_kann.txt','w') as hexe_kann_schreiben:
                hexe_kann_schreiben.write(hexe_kann_text)
                hexe_kann_schreiben.close()
        else:
            raise ValueError("Die Hexe kann nur über die flags 1 oder 2 verfügen") 
        
 
  #heilen --> 1
  #toeten --> 2
 
     
def hexe_darf_toeten()->bool:
    with open ('hexe_kann.txt','r') as hexe_kann:
              hexe_kann_text = hexe_kann.read()
              if str(2) in hexe_kann_text:
                  hexe_kann.close()
                  return(True)
              else:
                      hexe_kann.close()                 
                      return(False)
                  



                  
def hexe_darf_heilen()->bool:
    with open ('hexe_kann.txt','r') as hexe_kann:
              hexe_kann_text = hexe_kann.read()
              if "1" in hexe_kann_text:
                  hexe_kann.close()
                  return(True)
              else:
                    hexe_kann.close()
                    return(False)                 
              
           
