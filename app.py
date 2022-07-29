
from flask import Flask, request, url_for, render_template, session, make_response, redirect, Response
#from flask_session import Session
import requests, logging, werwolf, datetime, re
from inspect import currentframe, getframeinfo
from datetime import datetime

app = Flask(__name__)

@app.route('/', methods = ['GET','POST'])   # Homepage  
def index():
    return render_template('index.html')  # Render index.html



@app.route('/einstellungen', methods = ['GET','POST']) # Einstellungen
def einstellungen():
    return render_template('einstellungen.html') # Render einstellungen.html


@app.route('/einstellungen/spieleranzahl', methods = ['GET','POST']) # Spieleranzahl
def setPlayerNumber(): # set the number of players 
    spieleranzahl = request.form.get('num') # get the number of players from the form
    try: 
        spieleranzahl_int = int(spieleranzahl)   #eingabe ist wirklich ein integer
        if spieleranzahl_int < 0:
                spieleranzahl = 8 #auf 8 defaulten 
    except ValueError: 
        spieleranzahl = 8 #auf 8 defaulten
    
    
    with open('spieler_anzahl.txt', 'w+') as file: # speichern der spieleranzahl in einer textdatei
        file.write(str(spieleranzahl))
    if bool(request.form.get('cbx')) == True: # checkbox is checked
        erzaehler_flag = 1 # set erzaehler_flag to 1
    else:
        erzaehler_flag = 0 # set erzaehler_flag to 0
    with open('erzaehler_ist_zufaellig.txt', 'w+') as flag: # speichern des erzaehler_flag in einer textdatei
        flag.write(str(erzaehler_flag)) # speichern des erzaehler_flag in einer textdatei
    werwolf.createDict() # create the dictionary with the names of the players
    return(render_template('einstellungen_gespeichert.html', spieleranzahl_var = spieleranzahl)) # render einstellungen_gespeichert.html


@app.route('/spieler', methods = ['GET','POST']) # Spieler
def get_data(): # get the data from the form
    if request.method =='GET':  # if the request is a GET request
        return(render_template('fehler.html')) #fehlerseite ausgeben
    else: 
        if request.method == "POST": # if the request is a POST request
            name = request.form.get("name") # get the name from the form
            name = name.replace('1','i') #1 ist immer ein i
            name = name.replace('3','e') #3 ist immer ein e
            name = name.replace('4','a') #4 ist immer ein a 
            name = name.replace('/',"_") #/ ist immer ein _ 
            players_log = open('rollen_log.txt') # open the log file
            players_log = players_log.read() # read the log file
            name_ueberpruefung = name + ' = ' # create a string with the name and =
            if name_ueberpruefung in players_log: # if the name is already in the log file
                return(render_template('name_doppelt.html',name = name))    #name doppelt ausgeben
            else: 
                try:
                    if str(re.findall('\s*ivica\s*',name, re.IGNORECASE)[0]).upper() == 'IVICA': # if the name is ivica
                        name = 'ivo' # set the name to ivo
                except: # if the name is not ivica
                    pass # do nothing
                #date = datetime.datetime.now()
                file = open('spieler_anzahl.txt') # open the file with the number of players
                num = file.read() # read the file
                operator = werwolf.deduct() # get the operator
                try: # try to get the operator
                    if operator == 0: # if the operator is 0
                        code = 'code' # set the code to code
                        return(render_template('spiel_beginnt.html', code = code)) # render spiel_beginnt.html
                    else:
                        with open('rollen_log.txt', 'a') as names: # append the name to the log file
                            names.write(f'{name} = {operator}') # write the name and the operator to the log file
                            #names.write(f'{date}: {name} = {operator}')
                            names.write('\n') # write a new line to the log file
                         
                            return render_template('rollen_zuweisung.html', players = num, name = name, operator = operator)    # render rollen_zuweisung.html     
                except:
                    return render_template('neu_laden.html') # render neu_laden.html

@app.route('/erzaehler', methods = ['GET']) # Erzähler
def erzaehler():
    try:
        players_log = open('rollen_log.txt') # open the log file
        players_log = players_log.readlines() # read the log file
        return(render_template('erzaehler.html', names = players_log))  # render erzaehler.html
    except:
        return(404) # if the log file is not found
 
@app.route('/erzaehler/reset', methods = ['GET','POST'])   #reset der rollen_log.txt
def reset():
    if request.method == 'POST':
        if request.form['reset_button'] == 'Neues Spiel': #wenn neues spiel gewuenscht
            with open('rollen_log.txt','w+') as f: #leere rollen_log.txt
                f.write('*********************\n') 
                f.close #schließen der datei
            return(render_template('einstellungen.html')) #zurück zur einstellungen
    elif request.method == 'GET': #wenn reset gewuenscht
        return(render_template('index.html'))  #zurück zur homepage



@app.route("/uebersicht/<ist_unschuldig>") # Übersicht
def overview_all(ist_unschuldig): # Übersicht
 
    try:
        ist_unschuldig = int(ist_unschuldig) #ist_unschuldig ist wirklich ein integer
        if ist_unschuldig == 1: #wenn ist_unschuldig = 1
            players_log = open('rollen_log.txt') # open the log file
            players_log = players_log.readlines() # read the log file
            return (render_template('overview_innocent.html', names = players_log)) # render overview_innocent.html
        elif ist_unschuldig == 0: #wenn ist_unschuldig = 0
            players_log = open('rollen_log.txt') # open the log file
            players_log = players_log.readlines() # read the log file
            return (render_template('overview_guilty.html', names = players_log)) # render overview_guilty.html
        else:
            return(render_template('fehler.html')) # render fehler.html
    except:
         return(render_template('fehler.html')) # render fehler.html

### Rollen Dashboards
@app.route("/<name>/<rolle>/Dashboard") # Dashboard
def Dashboard(name, rolle):  # Dashboard

    wort = name+" = "+rolle    # create a string with the name and the role
    file = open('rollen_log.txt', "r") # open the log file
    players_vorhanden = file.read() # read the log file
     #print (wort) 
     # print (players_vorhanden[:-1])
    
    if wort in players_vorhanden: 
     try:
        players_log = open('rollen_log.txt') # open the log file 
        players_log = players_log.readlines()   # read the log file
        
        nurNamen = []      
        
        try:
            for line in players_log:
                
                if '*' in line:
                    pass
                else:
                    line = line.split(' = ')
                    name = line[0]
                    auswahlRolle = line[1]
                    
                   # print('Name: ' + name + '; Rolle: ' + auswahlRolle)
                    
                    if auswahlRolle != 'Tot' and auswahlRolle != 'Erzaehler':
                        nurNamen.append(name)
                        
           
           # nurNamen = ( ''.join(str(nurNamen)))
            #print(nurNamen)
                
        except:
            print('[Debug] Fehler beim Auslesen des rollen_logs in app.py line ' + str(getframeinfo(currentframe()).lineno - 1))
            
        return (render_template("Dashboards/Dash_"+ rolle +".html", name=name, rolle=rolle, names = players_log, nurNamen=nurNamen))
        
     except:
            return render_template("fehler.html")
        
    else: 
        print("Spieler oder Rolle falsch, zeige ihm den Klobert und leite Ihn nach 10 sekunden zurück!")
        return render_template("url_system.html", name=name, rolle=rolle)


@app.route("/<name>/<rolle>/wahl/<auswahl>")
def auswahl(name, rolle, auswahl):
    wort = name+" = "+rolle  
    file = open('rollen_log.txt', "r")
    players_vorhanden = file.read()
    print (wort) 
    print (players_vorhanden)
    
    voter = name + ' = '
    if wort in players_vorhanden:
        try:
            with open('hat_gewaehlt.txt', 'a') as text:
                # Überprüfen, ob der Spieler bereits gewählt hat  
                for line in text:
                    if voter in line:   
                        grund = "Du hast bereits gewählt"
                        return render_template("url_system.html", name=name, rolle=rolle, grund = grund)
                        
                    else:
                         # Wenn der Spieler noch nicht gewählt hat, wird er in die Datei geschrieben
                        text.write(voter)
                        
                        # Wenn der Spieler noch nicht gewählt hat, wird seine Auswahl in die Datei geschrieben
                        text.write(voter + auswahl + '\n')
                        
                        # Zähler um zur Bestimmung der Anzahl legetimer Stimmen
                        i = i+1
                        print("Anzahl Stimmen: " + str(i))
                        
                        # Überprüfen, ob alle Spieler gewählt haben
                        file = open('spieler_anzahl.txt')
                        spieler_anzahl = file.read()
                        
                        if i == spieler_anzahl:
                            # Wechsel weg von warten
                            return render_template("Dashboards/status/ergebnis.html", name=name, rolle=rolle, auswahl=auswahl)
                        
                        else:
                            try:
                                players_log = open('rollen_log.txt')
                                players_log = players_log.readlines()
                                
                                nurNamen = []      
                                
                                try:      
                                    for line in players_log:
                                        
                                        if '*' in line:
                                            pass
                                        else:
                                            line = line.split(' = ')
                                            name = line[0]
                                            rolle = line[1]
                                            
                                            print('Name: ' + name + '; Rolle: ' + rolle)
                                            
                                            if rolle != 'Tot':
                                                nurNamen.append(name)
                                except:
                                    print('[Debug] Fehler beim Auslesen des rollen_logs in app.py line ' + str(getframeinfo(currentframe()).lineno - 1))
                            
                                #return render_template("Dashboards/status/warten.html", name=name, rolle=rolle, auswahl = auswahl)
                                return render_template("Dashboards/Dash_"+ rolle +".html", rolle=rolle, nurNamen=nurNamen) # Statdessen zurück zum Dashboard
                        
                
                            except:
                                print('[Debug] Fehler beim Auslesen des rollen_logs in app.py line ' + str(getframeinfo(currentframe()).lineno - 1))
                                return render_template("fehler.html")
                            
        except:
            print('[Debug] Fehler beim Auslesen der Wahl Logs in app.py line ' + str(getframeinfo(currentframe()).lineno - 1))
            return render_template("fehler.html")
            
    ### Braver Copilot. Eines Tages dafst du mal selber entscheiden...
    # wort = name+" = "+rolle  
    # file = open('rollen_log.txt', "r")
    # players_vorhanden = file.read()
    # print (wort) 
    # print (players_vorhanden)
    # if wort in players_vorhanden:
    #  try:
    #     players_log = open('rollen_log.txt')
    #     players_log = players_log.readlines()
    #     return (render_template("Dashboards/status/TÖTENÖTENTÖTEN.html", name=name, rolle=rolle, names = players_log))
    #  except: 
    #         return render_template("fehler.html")
        
    # else: 
    #     print("Spieler oder Rolle falsch, zeige ihm den Klobert und leite Ihn nach 10 sekunden zurück!")
    #     return render_template("fehler.html")

    
     
@app.route("/<name>/<rolle>/schlafen")
def schlafen(name, rolle): 

    wort = name+" = "+rolle  
    file = open('rollen_log.txt', "r")
    players_vorhanden = file.read()
    print (wort) 
    print (players_vorhanden)
    if wort in players_vorhanden:
     try:
        players_log = open('rollen_log.txt')
        players_log = players_log.readlines()
        return (render_template("Dashboards/status/schlafen.html", name=name, rolle=rolle, names = players_log))
     except: 
            return render_template("fehler.html")
        
    else: 
        print("Spieler oder Rolle falsch, zeige ihm den Klobert und leite Ihn nach 10 sekunden zurück!")
        return render_template("url_system.html" , name=name, rolle=rolle)



@app.route("/<name>/<rolle>/warten")
def warten(name, rolle): 

    wort = name+" = "+rolle  
    file = open('rollen_log.txt', "r")
    players_vorhanden = file.read()
    print (wort) 
    print (players_vorhanden)
    print(rolle)
    print(name)
    if wort in players_vorhanden:
     try:
        players_log = open('rollen_log.txt')
        players_log = players_log.readlines()
        return (render_template("Dashboards/status/warten.html", name=name, rolle=rolle, names = players_log))
     except: 
            return render_template("fehler.html")
        
    else: 
        print("Spieler oder Rolle falsch, zeige ihm den Klobert und leite Ihn nach 10 sekunden zurück!")
        return render_template("url_system.html", name=name, rolle=rolle)

 
  
@app.route("/<name>/<rolle>/<todesgrund>/tot")   
def tot(name, rolle, todesgrund): 

    wort = name+" = "+rolle  
    file = open('rollen_log.txt', "r")
    players_vorhanden = file.read()
    print (wort) 
    print (players_vorhanden)
    
    if wort in players_vorhanden:
        try:
            players_log = open('rollen_log.txt')
            players_log = players_log.readlines()
            
            if todesgrund == 'Werwolf' or todesgrund == 'werwolf':
                todesgrund = 'Du wurdest von einem Werwolf getötet'
            elif todesgrund == 'Abstimung' or todesgrund == 'abstimmung':
                todesgrund = 'Du wurdest in Folge einer Abstimmung getötet'
            elif todesgrund == 'Hexe' or todesgrund == 'Hexe':
                todesgrund = 'Du wurdest von der Hexe getötet'
            else:
                todesgrund = 'Du wurdest getötet'
            return (render_template('Dashboards/status/tot.html', name = name, todesgrund = todesgrund, )) # rendert die Seite zum Status Tot
        
        except: 
                return render_template("fehler.html")
            
    else: 
        print("Spieler oder Rolle falsch, zeige ihm den Klobert und leite Ihn nach 10 sekunden zurück!")
        return render_template("url_system.html", name=name, rolle=rolle)

@app.route("/<name>/<rolle>/kick/")
def rausschmeissen(name,rolle):
    wort = name+" = "+rolle
    file = open('rollen_log.txt', "r")
    players_vorhanden = file.read()
    if wort in players_vorhanden:
        print("Spieler vorhanden")
        try:
            players_log = open('rollen_log.txt')
            players_log = players_log.readlines()
            return (render_template('rausschmeissen.html', name = name, rolle = rolle, names = players_log))
        except:
            
            return render_template("fehler.html")
        
    else:
        print("Spieler oder Rolle falsch, zeige ihm den Klobert und leite Ihn nach 10 sekunden zurück!")    
        return render_template("url_system.html", name=name, rolle=rolle)

 
@app.route("/<name>/<rolle>/resultat_Dorf")
def resultatDorf(name, rolle): 

    wort = name+" = "+rolle  
    file = open('rollen_log.txt', "r")
    players_vorhanden = file.read()
    print (wort) 
    print (players_vorhanden)
    if wort in players_vorhanden:
     try:
        players_log = open('rollen_log.txt')
        players_log = players_log.readlines()
        return (render_template("Dashboards/status/resultat_Dorf.html", name=name, rolle=rolle, names = players_log))
     except: 
            return render_template("fehler.html")
        
    else: 
        print("Spieler oder Rolle falsch, zeige ihm den Klobert und leite Ihn nach 10 sekunden zurück!")
        return render_template("url_system.html", name=name, rolle=rolle)
    
    

@app.route("/<name>/<rolle>/resultat_Wolf")
def resultatWolf(name, rolle): 

    wort = name+" = "+rolle  
    file = open('rollen_log.txt', "r")
    players_vorhanden = file.read()
    print (wort) 
    print (players_vorhanden)
    if wort in players_vorhanden:
     try:
        players_log = open('rollen_log.txt')
        players_log = players_log.readlines()
        return (render_template("Dashboards/status/resultat_Wolf.html", name=name, rolle=rolle, names = players_log))
     except: 
            return render_template("fehler.html")
        
    else: 
        print("Spieler oder Rolle falsch, zeige ihm den Klobert und leite Ihn nach 10 sekunden zurück!")
        return render_template("url_system.html", name=name, rolle=rolle)

@app.route("/wahlbalken/")
def wahlbalken():
     players_log = open('rollen_log.txt')
     players_log = players_log.readlines()
        
     nurNamen = []      
        
     try:
            for line in players_log:
                
                if '*' in line:
                    pass
                else:
                    line = line.split(' = ')
                    name = line[0]
                    auswahlRolle = line[1]
                    
                   # print('Name: ' + name + '; Rolle: ' + auswahlRolle)
                    
                    if auswahlRolle != 'Tot' and auswahlRolle != 'Erzaehler':
                        nurNamen.append(name)
                        return (render_template("wahlbalken.html", names = nurNamen))
     except:
            return render_template("fehler.html")
                        
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}
# inject a variable called 'now' into the template context for use in templates (templates can then access it as {{now}})
#https://stackoverflow.com/questions/41231290/how-to-display-current-year-in-flask-template   #the source of this code
if __name__ == '__main__': 
    app.run(debug=True)
    #app.run(debug=True, host='0.0.0.0')