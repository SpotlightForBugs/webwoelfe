
from flask import Flask, request, url_for, render_template, session, make_response, redirect, Response
#from flask_session import Session
import requests, logging, werwolf, datetime, re
from inspect import currentframe, getframeinfo
from datetime import datetime

app = Flask(__name__)

##index page

@app.route('/', methods = ['GET','POST'])   # Homepage  
def index():
    return render_template('index.html')  # Render index.html

##einstellungen

@app.route('/einstellungen', methods = ['GET','POST']) # Einstellungen
def einstellungen():
    return render_template('einstellungen.html') # Render einstellungen.html


##wie viele Spieler sollen vorhanden sein?

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

#namenseingabe spieler

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


##Pfad des Erzählers

@app.route('/erzaehler', methods = ['GET']) # Erzähler
def erzaehler():
    try:
        players_log = open('rollen_log.txt') # open the log file
        players_log = players_log.readlines() # read the log file
        return(render_template('erzaehler.html', names = players_log))  # render erzaehler.html
    except:
        return(404) # if the log file is not found
 
 ##Neues Spiel	
 
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


##Übersicht der Spieler

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
    
    if wort in players_vorhanden:  # if the name and the role are in the log file
     try: # try to get the role
        players_log = open('rollen_log.txt') # open the log file 
        players_log = players_log.readlines()   # read the log file
        
        nurNamen = []      # create a list with the names
        
        try:
            for line in players_log: # for every line in the log file
                
                if '*' in line: # if the line contains a *
                    pass # do nothing
                else:  # if the line does not contain a *
                    line = line.split(' = ') # split the line at the =
                    name = line[0] # set the name to the first part of the line
                    auswahlRolle = line[1] # set the role to the second part of the line
                    
                   # print('Name: ' + name + '; Rolle: ' + auswahlRolle) # print the name and the role
                    
                    if auswahlRolle != 'Tot' and auswahlRolle != 'Erzaehler': # if the role is not Tot or the role is not the Erzähler
                        nurNamen.append(name) # append the name to the list
                        
           
           # nurNamen = ( ''.join(str(nurNamen)))
            #print(nurNamen)
                
        except:
            print('[Debug] Fehler beim Auslesen des rollen_logs in app.py line ' + str(getframeinfo(currentframe()).lineno - 1)) # print the error
            
        return (render_template("Dashboards/Dash_"+ rolle +".html", name=name, rolle=rolle, names = players_log, nurNamen=nurNamen)) # render Dash_rolle.html
        
     except:
            return render_template("fehler.html") # render fehler.html
        
    else: 
        print("Spieler oder Rolle falsch, zeige ihm den Klobert und leite Ihn nach 10 sekunden zurück!") # print the error
        return render_template("url_system.html", name=name, rolle=rolle) # render url_system.html

#auswahl wahl

@app.route("/<name>/<rolle>/wahl/<auswahl>") # Wahl
def auswahl(name, rolle, auswahl): # Wahl
    wort = name+" = "+rolle   # create a string with the name and the role
    file = open('rollen_log.txt', "r") # open the log file
    players_vorhanden = file.read() # read the log file
    print (wort)  # print the string
    print (players_vorhanden) # print the log file
    
    voter = name + ' = ' + rolle # create a string with the name and the role
    if wort in players_vorhanden: # if the name and the role are in the log file
        try:
            with open('hat_gewaehlt.txt', 'a') as text:  # open the hat_gewaehlt.txt file
                # Überprüfen, ob der Spieler bereits gewählt hat und wenn nicht, dann wird er hinzugefügt
                for line in text:
                    if voter in line:   
                        grund = "Du hast bereits gewählt"
                        return render_template("url_system.html", name=name, rolle=rolle, grund = grund)
                        
                    else:
                         # Wenn der Spieler noch nicht gewählt hat, wird er in die Datei geschrieben
                        text.write(voter) # write the name and the role to the hat_gewaehlt.txt file
                        
                        # Wenn der Spieler noch nicht gewählt hat, wird seine Auswahl in die Datei geschrieben
                        text.write(voter + auswahl + '\n') # write the name and the role to the hat_gewaehlt.txt file
                        
                        # Zähler um zur Bestimmung der Anzahl legetimer Stimmen
                        i = i+1 # add 1 to the counter
                        print("Anzahl Stimmen: " + str(i)) # print the counter
                        
                        # Überprüfen, ob alle Spieler gewählt haben
                        file = open('spieler_anzahl.txt') # open the spieler_anzahl.txt file
                        spieler_anzahl = file.read() # read the spieler_anzahl.txt file
                        
                        if i == spieler_anzahl: # if the counter is equal to the number of players 
                            # Wechsel weg von warten 
                            return render_template("Dashboards/status/ergebnis.html", name=name, rolle=rolle, auswahl=auswahl) # render ergebnis.html
                        
                        else: # if the counter is not equal to the number of players
                            try: # try to get the role
                                players_log = open('rollen_log.txt') # open the log file
                                players_log = players_log.readlines()  # read the log file
                                
                                nurNamen = []       # create a list with the names
                                
                                try:      # try to get the role
                                    for line in players_log: # for every line in the log file
                                        
                                        if '*' in line: # if the line contains a *
                                            pass # do nothing
                                        else: # if the line does not contain a *
                                            line = line.split(' = ') # split the line at the =
                                            name = line[0] # set the name to the first part of the line
                                            rolle = line[1] # set the role to the second part of the line
                                            
                                            print('Name: ' + name + '; Rolle: ' + rolle) # print the name and the role
                                            
                                            if rolle != 'Tot': # if the role is not Tot
                                                nurNamen.append(name) # append the name to the list
                                except:
                                    print('[Debug] Fehler beim Auslesen des rollen_logs in app.py line ' + str(getframeinfo(currentframe()).lineno - 1)) # print the error
                            
                                #return render_template("Dashboards/status/warten.html", name=name, rolle=rolle, auswahl = auswahl) # render warten.html
                                return render_template("Dashboards/Dash_"+ rolle +".html", rolle=rolle, nurNamen=nurNamen) # Statdessen zurück zum Dashboard des Spielers
                        
                
                            except: 
                                print('[Debug] Fehler beim Auslesen des rollen_logs in app.py line ' + str(getframeinfo(currentframe()).lineno - 1)) # print the error
                                return render_template("fehler.html") # render fehler.html
                            
        except:
            print('[Debug] Fehler beim Auslesen der Wahl Logs in app.py line ' + str(getframeinfo(currentframe()).lineno - 1)) # print the error
            return render_template("fehler.html") # render fehler.html
            
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

#schlafen function 
     
@app.route("/<name>/<rolle>/schlafen") # route for the sleep function
def schlafen(name, rolle):  # function for the sleep function

    wort = name+" = "+rolle   # create a string with the name and the role
    file = open('rollen_log.txt', "r") # open the log file
    players_vorhanden = file.read() # read the log file
    print (wort)  # print the string
    print (players_vorhanden) # print the log file
    if wort in players_vorhanden: # if the string is in the log file
     try:
        players_log = open('rollen_log.txt') # open the log file
        players_log = players_log.readlines() # read the log file
        return (render_template("Dashboards/status/schlafen.html", name=name, rolle=rolle, names = players_log))    # render the sleep.html
     except: 
            return render_template("fehler.html")   # render the fehler.html
        
    else: 
        print("Spieler oder Rolle falsch, zeige ihm den Klobert und leite Ihn nach 10 sekunden zurück!") # print the error
        return render_template("url_system.html" , name=name, rolle=rolle) # render the url_system.html

#warten funktion

@app.route("/<name>/<rolle>/warten") # route for the wait function  
def warten(name, rolle):     # function for the wait function

    wort = name+" = "+rolle  # create a string with the name and the role  
    file = open('rollen_log.txt', "r") # open the log file
    players_vorhanden = file.read() # read the log file
    print (wort)  # print the string
    print (players_vorhanden) # print the log file
    print(rolle) # print the role
    print(name) # print the name
    if wort in players_vorhanden: # if the string is in the log file
     try: # try to get the role
        players_log = open('rollen_log.txt') # open the log file
        players_log = players_log.readlines() # read the log file
        return (render_template("Dashboards/status/warten.html", name=name, rolle=rolle, names = players_log))  # render the warten.html
     except: 
            return render_template("fehler.html")  # render the fehler.html
        
    else: 
        print("Spieler oder Rolle falsch, zeige ihm den Klobert und leite Ihn nach 10 sekunden zurück!") # print the error
        return render_template("url_system.html", name=name, rolle=rolle) # render the url_system.html
 
 
#tot function

@app.route("/<name>/<rolle>/<todesgrund>/tot")     # route for the death function
def tot(name, rolle, todesgrund):  # function for the death function

    wort = name+" = "+rolle   # create a string with the name and the role
    file = open('rollen_log.txt', "r") # open the log file
    players_vorhanden = file.read() # read the log file
    print (wort)  # print the string
    print (players_vorhanden) # print the log file
    
    if wort in players_vorhanden: # if the string is in the log file
        try: # try to get the role
            players_log = open('rollen_log.txt') # open the log file
            players_log = players_log.readlines() # read the log file
            
            if todesgrund == 'Werwolf' or todesgrund == 'werwolf': # if the death reason is a werewolf
                todesgrund = 'Du wurdest von einem Werwolf getötet' # set the death reason to a werewolf
            elif todesgrund == 'Abstimung' or todesgrund == 'abstimmung': # if the death reason is a abstimulation
                todesgrund = 'Du wurdest in Folge einer Abstimmung getötet' # set the death reason to a abstimulation
            elif todesgrund == 'Hexe' or todesgrund == 'Hexe': # if the death reason is a witch
                todesgrund = 'Du wurdest von der Hexe getötet' # set the death reason to a witch
            else: 
                todesgrund = 'Du wurdest getötet' # set the death reason to a normal death
            return (render_template('Dashboards/status/tot.html', name = name, todesgrund = todesgrund, )) # rendert die Seite zum Status Tot
        
        except: 
                return render_template("fehler.html") # rendert die Seite zum Status Fehler
            
    else: 
        print("Spieler oder Rolle falsch, zeige ihm den Klobert und leite Ihn nach 10 sekunden zurück!") # print the error
        return render_template("url_system.html", name=name, rolle=rolle) # render the url_system.html
 
 #kick function
 
@app.route("/<name>/<rolle>/kick/") # route for the kick function
def rausschmeissen(name,rolle): # function for the kick function
    wort = name+" = "+rolle  # create a string with the name and the role
    file = open('rollen_log.txt', "r") #    open the log file
    players_vorhanden = file.read() # read the log file
    if wort in players_vorhanden: # if the string is in the log file
        print("Spieler vorhanden") # print the string
        try:
            players_log = open('rollen_log.txt') # open the log file
            players_log = players_log.readlines() # read the log file
            return (render_template('rausschmeissen.html', name = name, rolle = rolle, names = players_log)) # render the rausschmeissen.html
        except:
            
            return render_template("fehler.html")   # render the fehler.html
        
    else:
        print("Spieler oder Rolle falsch, zeige ihm den Klobert und leite Ihn nach 10 sekunden zurück!")     # print the error
        return render_template("url_system.html", name=name, rolle=rolle)   # render the url_system.html

#Resultat Dorf
 
@app.route("/<name>/<rolle>/resultat_Dorf") # route for the resultat_Dorf function
def resultatDorf(name, rolle):  # function for the resultat_Dorf function

    wort = name+" = "+rolle     # create a string with the name and the role
    file = open('rollen_log.txt', "r") # open the log file
    players_vorhanden = file.read() # read the log file
    print (wort)  # print the string
    print (players_vorhanden) # print the log file
    if wort in players_vorhanden: # if the string is in the log file
     try: # try to get the role
        players_log = open('rollen_log.txt') # open the log file
        players_log = players_log.readlines() # read the log file
        return (render_template("Dashboards/status/resultat_Dorf.html", name=name, rolle=rolle, names = players_log)) # render the resultat_Dorf.html
     except: 
            return render_template("fehler.html") # render the fehler.html
        
    else: 
        print("Spieler oder Rolle falsch, zeige ihm den Klobert und leite Ihn nach 10 sekunden zurück!") # print the error
        return render_template("url_system.html", name=name, rolle=rolle) # render the url_system.html
    
    
#resultat_Werwolf

@app.route("/<name>/<rolle>/resultat_Wolf") # route for the resultat_Wolf function
def resultatWolf(name, rolle):      # function for the resultat_Wolf function

    wort = name+" = "+rolle   # create a string with the name and the role
    file = open('rollen_log.txt', "r") # open the log file
    players_vorhanden = file.read() # read the log file
    print (wort)  # print the string
    print (players_vorhanden)   # print the log file
    if wort in players_vorhanden: # if the string is in the log file
     try:
        players_log = open('rollen_log.txt') # open the log file
        players_log = players_log.readlines() # read the log file
        return (render_template("Dashboards/status/resultat_Wolf.html", name=name, rolle=rolle, names = players_log)) # render the resultat_Wolf.html
     except: 
            return render_template("fehler.html")   # render the fehler.html
        
    else: 
        print("Spieler oder Rolle falsch, zeige ihm den Klobert und leite Ihn nach 10 sekunden zurück!")    # print the error
        return render_template("url_system.html", name=name, rolle=rolle) # render the url_system.html

#wahlbalken

@app.route("/wahlbalken/") # route for the wahlbalken function
def wahlbalken():
     players_log = open('rollen_log.txt') # open the log file
     players_log = players_log.readlines() # read the log file
     
     print(players_log)
     
     print('Test')
        
     nurNamen = [] # create a list for the names
        
     try:
        for line in players_log: # for every line in the log file
                    
            if '*' in line: # if the line contains a *
                pass # do nothing
            else:   # if the line does not contain a *
                line = line.split(' = ') # split the line at the =
                name = line[0] # get the name
                auswahlRolle = line[1] # get the role
                
                # print('Name: ' + name + '; Rolle: ' + auswahlRolle) # print the name and the role
                
                if auswahlRolle != 'Tot' and auswahlRolle != 'Erzaehler': # if the role is not dead or the narrator
                    nurNamen.append(name) # append the name to the list
        
        return (render_template("wahlbalken.html", names = nurNamen)) # render the wahlbalken.html
        
     except:
            return render_template("fehler.html") # render the fehler.html
  
#context processor
  
                         
@app.context_processor 
def inject_now():
    return {'now': datetime.utcnow()}
# inject a variable called 'now' into the template context for use in templates (templates can then access it as {{now}})
#https://stackoverflow.com/questions/41231290/how-to-display-current-year-in-flask-template   #the source of this code
if __name__ == '__main__': 
    app.run(debug=True)
    #app.run(debug=True, host='0.0.0.0')