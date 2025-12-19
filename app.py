from flask import Flask, render_template_string, jsonify, request
import requests
from math import radians, sin, cos, sqrt, atan2

app = Flask(__name__)

RAIO_KM = 25.0 
API_URL = "https://api.vatsim.net/v2/fed/flights"

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1-a))

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="pt">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Radar Pro Boarding Pass</title>
        <style>
            :root { --air-blue: #1A237E; --warning-gold: #FFD700; --radar-green: #00FF41; }
            body { background-color: #0a192f; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; font-family: 'Courier New', monospace; color: white; }
            
            /* Container de Busca Estilizado */
            .search-container { display: none; background: rgba(255,255,255,0.1); padding: 15px; border-radius: 5px; margin-bottom: 20px; border: 1px solid var(--warning-gold); width: 90%; max-width: 500px; gap: 10px; }
            input { flex: 1; background: #000; border: 1px solid var(--air-blue); padding: 12px; color: var(--radar-green); font-weight: bold; }
            button { background: var(--warning-gold); color: #000; border: none; padding: 12px 20px; font-weight: 900; cursor: pointer; text-transform: uppercase; }

            /* Cartão com Efeito de Bilhete Real */
            .card { background: #fdfdfd; color: #1a1a1a; width: 95%; max-width: 600px; border-radius: 4px; position: relative; box-shadow: 0 20px 50px rgba(0,0,0,0.8); overflow: hidden; border-left: 15px solid var(--air-blue); }
            /* Recortes de Ticket */
            .card::before, .card::after { content: ""; position: absolute; width: 30px; height: 30px; background: #0a192f; border-radius: 50%; top: 50%; transform: translateY(-50%); }
            .card::before { left: -22px; } .card::after { right: -22px; }

            .header { background: var(--air-blue); color: white; padding: 15px; text-align: center; font-weight: 900; letter-spacing: 8px; font-size: 1.2em; border-bottom: 2px dashed #ccc; }
            
            .main-content { display: flex; padding: 25px; min-height: 200px; }
            .data-section { flex: 2; border-right: 2px dashed #ddd; padding-right: 20px; display: flex; flex-direction: column; justify-content: space-between; }
            .side-section { flex: 1; padding-left: 20px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
            
            .label { color: #777; font-size: 0.65em; font-weight: bold; margin-bottom: 5px; }
            .value { font-size: 1.5em; font-weight: 900; color: var(--air-blue); letter-spacing: -1px; }
            
            .barcode-area { margin-top: 15px; width: 100%; }
            .barcode { height: 50px; background: repeating-linear-gradient(90deg, #000, #000 1px, transparent 1px, transparent 3px, #000 3px, #000 4px); opacity: 0.8; }
            
            /* Rodapé Radar Ativo */
            .footer { background: var(--air-blue); color: var(--warning-gold); padding: 15px; text-align: center; font-size: 0.8em; font-weight: bold; border-top: 4px double var(--warning-gold); min-height: 40px; display: flex; align-items: center; justify-content: center; text-transform: uppercase; }
            
            @media (max-width: 480px) {
                .main-content { flex-direction: column; text-align: center; }
                .data-section { border-right: none; border-bottom: 2px dashed #ddd; padding: 0 0 20px 0; }
                .side-section { padding: 20px 0 0 0; }
            }
        </style>
    </head>
    <body onclick="ativarAlertas()">
        <div id="busca" class="search-container">
            <input type="text" id="endereco" placeholder="ENTER ICAO / CEP / CITY">
            <button onclick="buscarEndereco()">ENGAGE</button>
        </div>

        <div class="card">
            <div class="header">FLIGHT MANIFEST / PASS</div>
            <div class="main-content">
                <div class="data-section">
                    <div>
                        <div class="label">IDENTIFICATION / CALLSIGN</div>
                        <div id="callsign" class="value">---</div>
                    </div>
                    <div>
                        <div class="label">SECTOR: ORIGIN / DESTINATION</div>
                        <div id="route" class="value">--- / ---</div>
                    </div>
                    <div>
                        <div class="label">PRESSURE ALTITUDE (FL)</div>
                        <div id="alt" class="value">00000 FT</div>
                    </div>
                </div>
                <div class="side-section">
                    <div class="label">RANGE TO TARGET</div>
                    <div id="dist" class="value">0.0 KM</div>
                    <div class="barcode-area">
                        <div class="barcode"></div>
                        <div style="font-size: 10px; margin-top: 5px; font-weight: bold;">SECURITY SCAN: 25KM</div>
                    </div>
                </div>
            </div>
            <div id="status" class="footer">INITIALIZING RADAR...</div>
        </div>

        <script>
            const audioAlerta = new Audio('https://www.soundjay.com/buttons/beep-07a.mp3');
            let latAlvo = null, lonAlvo = null;
            let targetLock = false;
            let systemTime = "--:--:--";
            let frasesVigia = ["RADAR ACTIVE: SCANNING AIRSPACE", "TRANSPONDER INTERROGATION...", "SECTOR SECURED / NO TARGETS"];
            let frasesTarget = ["TARGET ACQUIRED / TRACKING...", "IDENTIFIED AIRCRAFT IN SECTOR", "MAINTAINING SIGNAL LOCK"];
            let indiceFrase = 0;

            function ativarAlertas() {
                audioAlerta.play().then(() => { audioAlerta.pause(); });
            }

            // Efeito Máquina de Escrever Criativo
            function typeText(text) {
                const elem = document.getElementById('status');
                let i = 0;
                elem.innerText = "";
                const timer = setInterval(() => {
                    if (i < text.length) {
                        elem.innerText += text.charAt(i);
                        i++;
                    } else {
                        clearInterval(timer);
                    }
                }, 50);
            }

            function rotacionarMensagens() {
                let lista = targetLock ? frasesTarget : frasesVigia;
                let msg = lista[indiceFrase % lista.length] + " [" + systemTime + "]";
                typeText(msg);
                indiceFrase++;
                setTimeout(rotacionarMensagens, 5000);
            }

            window.onload = function() {
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude;
                    systemTime = new Date().toLocaleTimeString();
                    rotacionarMensagens();
                    iniciarRadar();
                }, () => {
                    document.getElementById('busca').style.display = "flex";
                    document.getElementById('status').innerText = "INPUT TARGET LOCATION COORDINATES";
                    rotacionarMensagens();
                });
            };

            async function buscarEndereco() {
                const query = document.getElementById('endereco').value;
                const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${query}`);
                const data = await res.json();
                if(data.length > 0) {
                    latAlvo = parseFloat(data[0].lat); lonAlvo = parseFloat(data[0].lon);
                    iniciarRadar();
                }
            }

            function iniciarRadar() {
                setInterval(executarBusca, 15000); 
                executarBusca();
            }

            function executarBusca() {
                if(!latAlvo) return;
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}&t=${Date.now()}`)
                .then(res => res.json()).then(data => {
                    systemTime = new Date().toLocaleTimeString();
                    if(data.found) {
                        document.getElementById('callsign').innerText = data.callsign;
                        document.getElementById('route').innerText = data.dep + " / " + data.arr;
                        document.getElementById('alt').innerText = data.alt.toLocaleString() + " FT";
                        document.getElementById('dist').innerText = data.dist + " KM";
                        if (!targetLock) audioAlerta.play();
                        targetLock = true;
                    } else {
                        targetLock = false;
                        document.getElementById('callsign').innerText = "SEARCHING";
                        document.getElementById('dist').innerText = "0.0 KM";
                    }
                });
            }
        </script>
    </body>
    </html>
    ''')

@app.route('/api/data')
def get_data():
    lat_user = float(request.args.get('lat', 0))
    lon_user = float(request.args.get('lon', 0))
    try:
        r = requests.get(API_URL, timeout=10).json()
        for p in r.get('pilots', []):
            lat, lon = p.get('latitude'), p.get('longitude')
            if lat and lon:
                d = haversine(lat_user, lon_user, lat, lon)
                if d <= RAIO_KM:
                    f = p.get('flight_plan', {})
                    return jsonify({"found": True, "callsign": p.get('callsign'), "dep": f.get('departure', 'UNK'), "arr": f.get('arrival', 'UNK'), "dist": round(d, 1), "alt": p.get('altitude', 0)})
    except: pass
    return jsonify({"found": False})


