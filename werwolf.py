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
      #  print("erzaehler ist nicht zufaellig")
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

