from traceback import print_tb
from flask import Flask, request, url_for, render_template, session, make_response, redirect, Response
#from flask_session import Session
import requests, logging, werwolf, datetime, re
from inspect import currentframe, getframeinfo
from datetime import datetime
from flask_socketio import SocketIO, emit


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
    with open('rollen_log.txt','w+') as f: #leere rollen_log.txt
                f.write('*********************\n') 
                f.close #schließen der datei
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
            name = name.replace('=',"-") #gleich ist immer -
            name = name.replace(':',"_") #doppelpunkt ist immer _
            name = name.replace('*',"_") #stern ist immer _
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
                            names.close()
                        with open('rollen_original.txt', 'a') as names: # append the name to the log file
                            names.write(f'{name} = {operator}') # write the name and the operator to the log file
                            #names.write(f'{date}: {name} = {operator}')
                            names.write('\n') # write a new line to the log file  
                            #credits to @joschicraft 
                          
                          
                          
                          
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
            file = open("abstimmung.txt","r+")
            file.truncate(0)
            file.close()    
            file2 = open("rollen_original.txt","r+")
            file2.truncate(0)
            file2.close()    
            file3 = open("hat_gewaehlt.txt","r+")
            file3.truncate(0)
            file3.close()    
            file4 = open("hexe_kann.txt","w")
            file4.write(str(12))
            file4.close()
            
         
            return(render_template('einstellungen.html')) #zurück zur einstellungen
    elif request.method == 'GET': 
        return(render_template('index.html'))  #zurück zur homepage



@app.route("/weiterleitung/<target>")
def weiterleitung(target):
    return(redirect(target)) #redirect to the target
    


@app.route("/<name>/<rolle>/toeten/<name_kill>") #kill a player
def kill_player(name,rolle,name_kill):
    if rolle == 'Hexe':
        with open ('hexe_kann.txt','r') as hexe_kann:
            hexe_kann_text = hexe_kann.read()
            hexe_kann_text = hexe_kann_text.replace('2','')
            hexe_kann.close()
        with open ('hexe_kann.txt','w') as hexe_kann_schreiben:
            hexe_kann_schreiben.write(hexe_kann_text)
    wort = name+" = "+rolle    # create a string with the name and the role
    file = open('rollen_log.txt', "r") # open the log file
    players_vorhanden = file.read() # read the log file
    if wort in players_vorhanden: # if the name and the role is in the log file
        pass
    else:
         return(render_template('fehler.html'))
    
    
    
    with open('rollen_log.txt', 'r+') as fileTot_kill:
       

        file_list_kill = []
        counter_tot = 0

        for line in fileTot_kill:
            file_list_kill.append(line)
            
        #print(file_list)
        
        name_kill = name_kill.strip('\n')
        name_kill = name_kill.replace('\n', '')

        while counter_tot < len(file_list_kill):
            
            #print(name_tot + ' - File List: ' + file_list[counter_tot])
            print('Name Tot: ' + name_kill + ' =')
            
            if name_kill + ' =' in file_list_kill[counter_tot]:      
                #print("If")
                dffd = file_list_kill[counter_tot].split(" = ")
                new_line = dffd[0] + " = Tot \n"
                #print(new_line)
                file_list_kill[counter_tot] = new_line
                #print(file_list)

            counter_tot = counter_tot+1                
    fileTot_kill.close()    
    with open('rollen_log.txt', 'w') as fileFinal:
        fileFinal.writelines(file_list_kill)    
    fileFinal.close() 
    with open('letzter_tot.txt', "w") as file:
            file.write(name_kill)
    
    return(render_template('Dashboards/Dash_Dorfbewohner.html'))


@app.route("/<name>/Armor_aktion/<player1>/<player2>") #player auswahl
def armor_player(player1, player2, name):
    rolle = "Armor"
    
    wort = name+" = "+rolle    # create a string with the name and the role
    file = open('rollen_log.txt', "r") # open the log file
    players_vorhanden = file.read() # read the log file
    
    if wort in players_vorhanden:
        lover_one = player1
        lover_two = player2
        
        print(lover_one+" LIEBT "+lover_two)
        
        return(render_template('Dashboards/Dash_Armor.html'))


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
    
    rolleAusLog = players_vorhanden.split(' = ') # split the log file into a list
    rolleAusLog = rolleAusLog[1]
    
    if rolleAusLog == 'Tot':
        return render_template('tot.html', name = name) # render tot.html
    
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
                    name_line = line[0] 
                    auswahlRolle = line[1] # set the role to the second part of the line
                    
                   # print('Name: ' + name + '; Rolle: ' + auswahlRolle) # print the name and the role
                    
                    if auswahlRolle != 'Tot' and auswahlRolle != 'Erzaehler': # if the role is not Tot or the role is not the Erzähler
                        nurNamen.append(name_line) # append the name to the list
                        
           
        
                
        except:
            print('[Debug] Fehler beim Auslesen des rollen_logs in app.py line ' + str(getframeinfo(currentframe()).lineno - 1)) # print the error
            
        return (render_template("Dashboards/Dash_Dorfbewohner.html", name=name, rolle=rolle, names = players_log, nurNamen=nurNamen)) # render Dash_rolle.html
        
     except:
            return render_template("fehler.html") # render fehler.html
        
    else: 
        print("Spieler oder Rolle falsch, zeige ihm den Klobert und leite Ihn nach 10 sekunden zurück!") # print the error
        return render_template("url_system.html", name=name, rolle=rolle) # render url_system.html



@app.route("/<name>/<rolle>/Dashboard_sp")
def spezielles_Dashboard(name,rolle):
    if rolle == 'Tot':
     return render_template("fehler.html")  
    else:
         wort = name+" = "+rolle    # create a string with the name and the role
    file = open('rollen_log.txt', "r") # open the log file
    players_vorhanden = file.read() # read the log file
    
    rolleAusLog = players_vorhanden.split(' = ') # split the log file into a list
    rolleAusLog = rolleAusLog[1]
    
    if rolleAusLog == 'Tot':
        return render_template('tot.html', name = name) # render tot.html
    
     #print (wort) 
     # print (players_vorhanden[:-1])
    else:
        if wort in players_vorhanden: # if the name and the role are in the log file
     
        
            nurNamen = []      # create a list with the names
        
            if rolle == 'Hexe': 
                print('Hexe')
                with open ('letzter_tot.txt', 'r') as file:
                    letzter_tot = file.read()
                    file.close()
                    with open ('hexe_kann.txt', 'r') as file:
                        hexe_kann = file.read()
                        hexe_kann = str(hexe_kann)
                        file.close()
        
        players_log = open('rollen_log.txt') # open the log file 
        players_log = players_log.readlines()   # read the log file
            
        for line in players_log: # for every line in the log file
                
                if '*' in line or 'Tot' in line or 'Erzaehler' in line: # if the line contains a *
                    pass # do nothing
                else:  # if the line does not contain a *
                    line = line.split(' = ') # split the line at the =
                    name_line = line[0] 
                    auswahlRolle = line[1] # set the role to the second part of the line
                    
                   # print('Name: ' + name + '; Rolle: ' + auswahlRolle) # print the name and the role
                    nurNamen.append(name_line) # append the name to the list
                        
           
          
        if rolle == 'Hexe':
                
                return (render_template("Dashboards/Dash_"+ rolle +".html", name=name, rolle=rolle, names = players_log, nurNamen=nurNamen,letzter_tot=letzter_tot,hexe_kann=hexe_kann)) # render Dash_rolle.html     
        else:
                return (render_template("Dashboards/Dash_"+ rolle +".html", name=name, rolle=rolle, names = players_log, nurNamen=nurNamen)) # render Dash_rolle.html  
                    
        


@app.route("/<name>/<rolle>/spiel_ende")
def spiel_ende(name,rolle):
     wort = name+" = "+rolle 
     file = open('rollen_original.txt', "r") 
     players_vorhanden = file.read()
     print (wort)  
     print (players_vorhanden) 
    
     if wort in players_vorhanden:
         if 'Werwolf' in players_vorhanden and 'Dorfbewohner' in players_vorhanden or 'Hexe' in players_vorhanden and 'Werwolf' in players_vorhanden or 'Seherin' in players_vorhanden and 'Werwolf' in players_vorhanden or 'Jäger' in players_vorhanden and 'Werwolf' in players_vorhanden or 'Armor' in players_vorhanden and 'Werwolf' in players_vorhanden:
             return(f'Hallo {name}, das Spiel ist noch nicht beendet!')
         else:
           
           

            print('Spiel ist beendet!')
            
            if rolle == 'Werwolf':
                if 'Werwolf' in players_vorhanden:
                    return(render_template('gewonnen.html', name=name, rolle=rolle,unschuldig=0))
                else:
                    return(render_template('verloren.html', name=name, rolle=rolle,unschuldig=0))
                    
               
            else :
               if 'Werwolf' in players_vorhanden:
                    return(render_template('verloren.html', name=name, rolle=rolle,unschuldig=1))
               else:
                    return(render_template('gewonnen.html', name=name, rolle=rolle,unschuldig=1))
             
    

        


@app.route("/waehlen/<name>/<rolle>/<auswahl>")
def wahl(name, rolle, auswahl):
   
   if rolle == 'Tot' : 
       return render_template("warten.html")
   else :
    wort = name+" = "+rolle  
    wort2 = name+" : "
    file = open('rollen_log.txt', "r")
    players_vorhanden = file.read()
    if wort in players_vorhanden:
        
        with open('hat_gewaehlt.txt', 'r+') as text: 
            contents = text.read()
            
            if wort2 in contents:
                return render_template("wahl_doppelt.html")
            else:
                text.write(name + " : " + '\n')
                text.close()
                with open("abstimmung.txt","a") as abstimmung:
                 abstimmung.write(auswahl+''+ '\n') 
                 
                 
                 abstimmung.close()
                 return render_template("Dashboards/status/warten.html")
             
#schlafen function 
     
@app.route("/<name>/<rolle>/schlafen") # route for the sleep function
def schlafen(name, rolle):  # function for the sleep function


    if rolle == 'Tot':
        return render_template("tot.html", name = name)

    wort = name+" = "+rolle   # create a string with the name and the role
    file = open('rollen_log.txt', "r") # open the log file
    players_vorhanden = file.read() # read the log file
    
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

@app.route("/warten") # route for the wait function  
def warten():     # function for the wait function
    i = 0 # set i to 0
    
    try:
        
        
        with open ('rollen_log.txt', 'r') as text:
            for line in text:
                if not 'Tot' in line and not 'Erzaehler' in line and not '*' in line:
                    i = i + 1
            text.close()
        with open ('abstimmung.txt', 'r') as text:
             #empty lines are not counted
                         anzahl_stimmen = sum(1 for line in text if line.rstrip()) 
            
            
            
        text.close()
        print(anzahl_stimmen)
        print(i)
        if i == anzahl_stimmen:
            print("Alle Spieler haben gewaehlt")
            count = 0;  
            name_tot = "";  
            maxCount = 0;  
            words = [];  
            
            file = open("abstimmung.txt", "r")  
                
            for line in file:
                 
                string = line.lower().replace(',','').replace('.','').split(" ");  
                for s in string:  
                    words.append(s);  
            
            for i in range(0, len(words)):  
                count = 1;  
                for j in range(i+1, len(words)):  
                    if(words[i] == words[j]):  
                        count = count + 1;  
                        
                if(count > maxCount):  
                    maxCount = count;  
                    name_tot = words[i];  
            
            
          

            with open('rollen_log.txt', 'r+') as fileTot:

                file_list = []
                counter_tot = 0

                for line in fileTot:
                    file_list.append(line)
                    
                #print(file_list)
                
                name_tot = name_tot.strip('\n')
                name_tot = name_tot.replace('\n', '')

                while counter_tot < len(file_list):
                    
                    #print(name_tot + ' - File List: ' + file_list[counter_tot])
                    print('Name Tot: ' + name_tot + ' =')
                    
                    if name_tot in file_list[counter_tot]:      
                        #print("If")
                        dffd = file_list[counter_tot].split(" = ")
                        new_line = dffd[0] + " = Tot \n"
                        #print(new_line)
                        file_list[counter_tot] = new_line
                        #print(file_list)

                    counter_tot = counter_tot+1
                    
            fileTot.close()    
            with open('rollen_log.txt', 'w') as fileFinal:
                fileFinal.writelines(file_list)    
            fileFinal.close()             
            with open('letzter_tot.txt', "w") as file:
                    file.write(name_tot)
            
                                    
                    
           
            
            return render_template("Dashboards/status/ergebnis.html",name = name_tot)
        else: 
             return render_template("Dashboards/status/warten.html")
        
     
    except: 
            return render_template("fehler.html")  # render the fehler.html
        
 
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
  
  
@app.route("/wahlstatus") # route for the wahlstatus function
def wahl_stats():
     
     
            anzahl = 0;  
            name_tot = "";  
            maxCount = 0;  
            words = [];  
            
            file = open("abstimmung.txt", "r")  
                
            for line in file:
                 
                string = line.lower().replace(',','').replace('.','').split(" ");  
                for s in string:  
                    words.append(s);  
            
            for i in range(0, len(words)):  
                anzahl = 1;  
                for j in range(i+1, len(words)):  
                    if(words[i] == words[j]):  
                        anzahl = anzahl + 1;  
                        
                if(anzahl > maxCount):  
                    maxCount = anzahl;  
                    name_tot = words[i];  
                    

            
            with open('letzter_tot.txt', "w") as file:
                    file.write(name_tot)
            
            return render_template("wahlstatus.html", name_tot = name_tot);
  
  
@app.route("/sehen/<name>/<rolle>/<auswahl>")
def sehen(name, rolle, auswahl):
    wort = name+" = "+rolle  # create a string with the name and the role
    file = open('rollen_log.txt', "r") #    open the log file
    players_vorhanden = file.read() # read the log file
    if wort in players_vorhanden: # if the string is in the log file
        players_log = open('rollen_log.txt') # open the log file
        players_log = players_log.readlines() # read the log file
        for line in players_log:
            if auswahl in line:
                ergebnis = line
                ergebnis = ergebnis.replace('=', 'hat die Rolle')
                return (render_template("Dashboards/status/sehen.html", ergebnis = ergebnis)) 
    
    
    
    
    
    else:
         print("Spieler oder Rolle falsch, zeige ihm den Klobert und leite Ihn nach 10 sekunden zurück!")    # print the error
         return (render_template("url_system.html",name = name, rolle = rolle)) 
        


@app.route("/<name>/<rolle>/<auswahl>/wer_tot")
def wer_tot(name, rolle, auswahl):
    
    wort = name+" = "+rolle  # create a string with the name and the role
    file = open('rollen_log.txt', "r") #    open the log file
    players_vorhanden = file.read() # read the log file
    if wort in players_vorhanden: 
        with open ('hat_gewaehlt.txt', 'r') as f:
            if name +" : " in f.read():
                return (render_template("wahl_doppelt.html"))
            else:
              auswahl = auswahl.strip() #erase the whitespace %20
            if auswahl in players_vorhanden:
              print("Eine legetime Auswahl wurde getroffen!")
              with open('abstimmung.txt','a') as abstimmung:
               abstimmung.write(auswahl + '\n')
              abstimmung.close()
              with open ('hat_gewaehlt.txt', 'a') as hat_gewaehlt:
                    hat_gewaehlt.write(name +" : " +"\n")
                    return render_template("Dashboards/status/wer_wahl_warten.html") 
    
    

@app.route("/wer_wahl_warten")
def wer_wahl_warten():
    
        with open ('hat_gewaehlt.txt', 'r+') as hat_gewaehlt:
             wer_anzahl_stimmen = sum(1 for line in hat_gewaehlt if line.rstrip()) 
             if wer_anzahl_stimmen == 4:
            
                count = 0;  
                name_tot = "";  
                maxCount = 0;  
                words = [];  
                
                file = open("abstimmung.txt", "r")  
                    
                for line in file:
                    
                    string = line.lower().replace(',','').replace('.','').split(" ");  
                    for s in string:  
                        words.append(s);  
                
                for i in range(0, len(words)):  
                    count = 1;  
                    for j in range(i+1, len(words)):  
                        if(words[i] == words[j]):  
                            count = count + 1;  
                            
                    if(count > maxCount):  
                        maxCount = count;  
                        name_tot = words[i];  
                
                
            

                with open('rollen_log.txt', 'r+') as fileTot:

                    file_list = []
                    counter_tot = 0

                    for line in fileTot:
                        file_list.append(line)
                        
                    #print(file_list)
                    
                    name_tot = name_tot.strip('\n')
                    name_tot = name_tot.replace('\n', '')

                    while counter_tot < len(file_list):
                        
                        #print(name_tot + ' - File List: ' + file_list[counter_tot])
                        print('Name Tot: ' + name_tot + ' =')
                        
                        if name_tot in file_list[counter_tot]:      
                            #print("If")
                            dffd = file_list[counter_tot].split(" = ")
                            new_line = dffd[0] + " = Tot \n"
                            #print(new_line)
                            file_list[counter_tot] = new_line
                            #print(file_list)

                        counter_tot = counter_tot+1
                        
                fileTot.close()    
                with open('rollen_log.txt', 'w') as fileFinal:
                    fileFinal.writelines(file_list)    
                fileFinal.close()  
                
                with open('letzter_tot.txt', "w") as file:
                    file.write(name_tot)
                
                name = name_tot
                return (render_template("Dashboards/status/wer_wahl_ergebnis.html", name=name ))
             else:
                  return (render_template("Dashboards/status/wer_wahl_warten.html"))




@app.route('/partner/<nummer>/<nummer2>',methods = ['GET','POST'])
def partner(nummer,nummer2 ):
    pass

    
   
         
         
         
@app.route("/<name>/<rolle>/heilen/<auswahl>")
def heilen(name, rolle, auswahl):
    if rolle == "Hexe":
     wort = name+" = "+rolle
     file = open('rollen_log.txt', "r")
     players_vorhanden = file.read()
     if wort in players_vorhanden:
         with open ('rollen_original.txt') as f:
             for line in f:
                 if auswahl + " =" in line:
                     line_zu_schreiben = line.replace(wort, auswahl)
                     
                     with open ('rollen_log.txt', 'r+') as file:
                         for line in file:
                             if wort in line:
                                with open('rollen_log.txt', 'r+') as file_heal:
       
                                    
                                    file_heal_list = []
                                    counter_heal = 0

                                    for line in file_heal:
                                        file_heal_list.append(line)
                                        

                                    while counter_heal < len(file_heal_list):
                                        
                
                                        
                                        if auswahl + ' =' in file_heal_list[counter_heal]:      
                                            #print("If")
                        
                                            new_line = line_zu_schreiben
                                            #print(new_line)
                                            file_heal_list[counter_heal] = new_line
                                            #print(file_list)

                                        counter_heal = counter_heal+1                
                                file_heal.close()    
                                with open('rollen_log.txt', 'w') as fileFinal:
                                    fileFinal.writelines(file_heal_list)    
                                fileFinal.close() 
                                
                                with open ('hexe_kann.txt','r') as hexe_kann:
                                    hexe_kann_text = hexe_kann.read()
                                    hexe_kann_text = hexe_kann_text.replace('1','')
                                    hexe_kann.close()
                                    
                                with open ('hexe_kann.txt','w') as hexe_kann_schreiben:
                                    hexe_kann_schreiben.write(hexe_kann_text)
                                
                                return(render_template('Dashboards/Dash_Dorfbewohner.html'))
                                                            
                                                            
                                 
                                 
                    
       
     
     
    


#context processor
  
                         
@app.context_processor 
def inject_now():
    return {'now': datetime.utcnow()}
# inject a variable called 'now' into the template context for use in templates (templates can then access it as {{now}})
#https://stackoverflow.com/questions/41231290/how-to-display-current-year-in-flask-template   #the source of this code
if __name__ == '__main__': 
    app.run(debug=True)
    #app.run(debug=True, host='0.0.0.0')