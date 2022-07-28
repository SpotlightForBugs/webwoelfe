
from flask import Flask, request, url_for, render_template, session, make_response, redirect, Response
#from flask_session import Session
import requests, logging, werwolf, datetime, re
from inspect import currentframe, getframeinfo
from datetime import datetime

app = Flask(__name__)

@app.route('/', methods = ['GET','POST'])   
def index():
    return render_template('index.html') 



@app.route('/einstellungen', methods = ['GET','POST'])
def einstellungen():
    return render_template('einstellungen.html')


@app.route('/einstellungen/spieleranzahl', methods = ['GET','POST']) 
def setPlayerNumber(): # set the number of players
    spieleranzahl = request.form.get('num')
    try: 
        spieleranzahl_int = int(spieleranzahl)   #eingabe ist wirklich ein integer
        if spieleranzahl_int < 0:
                spieleranzahl = 8 #auf 8 defaulten 
    except ValueError: 
        spieleranzahl = 8 #auf 8 defaulten
    
    
    with open('spieler_anzahl.txt', 'w+') as file: 
        file.write(str(spieleranzahl))
    if bool(request.form.get('cbx')) == True: 
        erzaehler_flag = 1
    else:
        erzaehler_flag = 0
    with open('erzaehler_ist_zufaellig.txt', 'w+') as flag:
        flag.write(str(erzaehler_flag))
    werwolf.createDict()
    return(render_template('einstellungen_gespeichert.html', spieleranzahl_var = spieleranzahl))


@app.route('/spieler', methods = ['GET','POST'])
def get_data():
    if request.method =='GET':
        return(render_template('fehler.html')) #fehlerseite
    else:
        if request.method == "POST":
            name = request.form.get("name")
            name = name.replace('1','i') #1 ist immer ein i
            name = name.replace('3','e') #3 ist immer ein e
            name = name.replace('4','a') #4 ist immer ein a 
            name = name.replace('/',"_") #/ ist immer ein _ 
            players_log = open('rollen_log.txt')
            players_log = players_log.read()
            name_ueberpruefung = name + ' = '
            if name_ueberpruefung in players_log:
                return(render_template('name_doppelt.html',name = name))    #name doppelt
            else:
                try:
                    if str(re.findall('\s*ivica\s*',name, re.IGNORECASE)[0]).upper() == 'IVICA':
                        name = 'ivo'
                except:
                    pass
                #date = datetime.datetime.now()
                file = open('spieler_anzahl.txt')
                num = file.read()
                operator = werwolf.deduct()
                try:
                    if operator == 0:
                        code = 'code'
                        return(render_template('spiel_beginnt.html', code = code))
                    else:
                        with open('rollen_log.txt', 'a') as names:
                            names.write(f'{name} = {operator}')
                            #names.write(f'{date}: {name} = {operator}')
                            names.write('\n')
                        
                            return render_template('rollen_zuweisung.html', players = num, name = name, operator = operator)        
                except:
                    return render_template('neu_laden.html')

@app.route('/erzaehler', methods = ['GET'])
def erzaehler():
    try:
        players_log = open('rollen_log.txt')
        players_log = players_log.readlines()
        return(render_template('erzaehler.html', names = players_log))
    except:
        return(404)

@app.route('/erzaehler/reset', methods = ['GET','POST'])   #reset der rollen_log.txt
def reset():
    if request.method == 'POST':
        if request.form['reset_button'] == 'Neues Spiel': #wenn neues spiel gewuenscht
            with open('rollen_log.txt','w+') as f: #leere rollen_log.txt
                f.write('*********************\n') 
                f.close
            return(render_template('einstellungen.html')) #zurück zur einstellungen
    elif request.method == 'GET':
        return(render_template('index.html')) 



@app.route("/uebersicht/<ist_unschuldig>")
def overview_all(ist_unschuldig):
 
    try:
        ist_unschuldig = int(ist_unschuldig)
        if ist_unschuldig == 1:
            players_log = open('rollen_log.txt')
            players_log = players_log.readlines()
            return (render_template('overview_innocent.html', names = players_log))
        elif ist_unschuldig == 0:
            players_log = open('rollen_log.txt')
            players_log = players_log.readlines()
            return (render_template('overview_guilty.html', names = players_log))
        else:
            return(render_template('fehler.html'))
    except:
         return(render_template('fehler.html'))

### Rollen Dashboards
@app.route("/<name>/<rolle>/Dashboard")
def Dashboard(name, rolle): 

    wort = name+" = "+rolle  
    file = open('rollen_log.txt', "r")
    players_vorhanden = file.read()
    print (wort) 
    print (players_vorhanden)
    
    if wort in players_vorhanden:
     try:
        players_log = open('rollen_log.txt')
        players_log = players_log.readlines()
        
        nurNamen = []      
        
        try:
            frameinfo = getframeinfo(currentframe())
            
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
            print('[Debug] Fehler beim Auslesen des rollen_logs in app.py line ' + str(frameinfo.lineno - 1))
            
        return (render_template("Dashboards/Dash_"+ rolle +".html", name=name, rolle=rolle, names = players_log, nurNamen=nurNamen))
        #return (render_template("index.html", name=name, rolle=rolle, names = players_log, nurNamen=nurNamen))
        
     except:
            return render_template("fehler.html")
        
    else: 
        print("Spieler oder Rolle falsch, zeige ihm den Klobert und leite Ihn nach 10 sekunden zurück!")
        return render_template("url_system.html", name=name, rolle=rolle)


  
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
                        text.write(voter)
                # Wenn der Spieler noch nicht gewählt hat, wird er in die Datei geschrieben
                # Zähler um zur Bestimmung der Anzahl legetimer Stimmen
                
                        i = i+1
                        print("i ist: " + str(i))
                        
                        # Wenn der Spieler noch nicht gewählt hat, wird seine Auswahl in die Datei geschrieben
                        text.write(voter + auswahl + '\n')
                        
                        # Überprüfen, ob alle Spieler gewählt haben
                        file = open('spieler_anzahl.txt')
                        spieler_anzahl = file.read()
                        if i == spieler_anzahl:
                            # Wechsel weg von warten
                            return render_template("Dashboards/status/ergebnis.html", name=name, rolle=rolle, auswahl=auswahl)
                        else:
            
                            players_log = open('rollen_log.txt')
                            players_log = players_log.readlines()
                            return render_template("Dashboards/status/warten.html", name=name, rolle=rolle, auswahl = auswahl)
                        
                
        except: 
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

    
    
    

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}   # inject a variable called 'now' into the template context for use in templates (templates can then access it as {{now}})
#https://stackoverflow.com/questions/41231290/how-to-display-current-year-in-flask-template   #the source of this code
#context_processor: Injects a function into the template context.

if __name__ == '__main__':
    app.run(debug=True)
    #app.run(debug=True, host='0.0.0.0')