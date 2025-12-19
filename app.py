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
        <title>Radar Boarding Pass</title>
        <style>
            :root { --air-blue: #1A237E; --warning-gold: #FFD700; --bg-dark: #0a192f; }
            body { background-color: var(--bg-dark); display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; font-family: 'Courier New', monospace; }
            
            /* Busca Estilizada */
            .search-container { display: none; background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; margin-bottom: 25px; border: 1px solid var(--warning-gold); width: 90%; max-width: 550px; display: flex; gap: 10px; }
            input { flex: 1; background: #000; border: 1px solid #333; padding: 12px; color: white; font-weight: bold; outline: none; }
            button { background: var(--warning-gold); color: #000; border: none; padding: 12px 20px; font-weight: 900; cursor: pointer; }

            /* O TICKET (Layout idêntico à imagem 2) */
            .card { background: var(--air-blue); width: 95%; max-width: 650px; border-radius: 20px; position: relative; box-shadow: 0 30px 60px rgba(0,0,0,0.7); overflow: hidden; }
            
            /* Furos Laterais (Meia-Lua) */
            .notch { position: absolute; width: 40px; height: 40px; background: var(--bg-dark); border-radius: 50%; top: 50%; transform: translateY(-50%); z-index: 20; }
            .notch-left { left: -20px; }
            .notch-right { right: -20px; }

            /* Cabeçalho */
            .header { padding: 20px 0; text-align: center; color: white; display: flex; justify-content: center; align-items: center; gap: 20px; font-weight: 900; letter-spacing: 4px; font-size: 1.2em; }
            .header span { font-size: 1.8em; }

            /* Área Branca Picotada */
            .white-area { background: #fdfdfd; margin: 0 10px; position: relative; display: flex; padding: 30px; min-height: 230px; border-radius: 2px; }
            .white-area::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 6px; background-image: linear-gradient(to right, #ccc 40%, transparent 40%); background-size: 12px 100%; }

            .col-left { flex: 1.8; border-right: 2px dashed #e0e0e0; padding-right: 20px; display: flex; flex-direction: column; justify-content: space-around; }
            .col-right { flex: 1; padding-left: 20px; display: flex; flex-direction: column; justify-content: center; align-items: center; }
            
            .label { color: #999; font-size: 0.6em; font-weight: 800; text-transform: uppercase; margin-bottom: 2px; }
            .value { font-size: 1.6em; font-weight: 900; color: var(--air-blue); margin-bottom: 12px; letter-spacing: -0.5px; }
            
            .barcode { height: 65px; background: repeating-linear-gradient(90deg, #000, #000 1px, transparent 1px, transparent 3px, #000 3px, #000 4px); width: 100%; margin: 10px 0; }
            .scan-info { font-size: 9px; font-weight: 900; color: #333; letter-spacing: 1px; }

            /* Rodapé com as Duas Linhas Amarelas */
            .footer { padding: 20px 0; display: flex; flex-direction: column; align-items: center; background: var(--air-blue); }
            .double-line { width: 100%; height: 8px; border-top: 2px solid var(--warning-gold); border-bottom: 2px solid var(--warning-gold); margin-bottom: 15px; box-sizing: border-box; }
            .status-msg { color: var(--warning-gold); font-size: 0.9em; font-weight: bold; letter-spacing: 2px; min-height: 20px; }

            @media (max-width: 500px) {
                .white-area { flex-direction: column; padding: 20px; }
                .col-left { border-right: none; border-bottom: 2px dashed #eee; padding-bottom: 20px; }
                .col-right { padding: 20px 0 0 0; }
            }
        </style>
    </head>
    <body onclick="ativarAlertas()">
        
        <div id="busca" class="search-container">
            <input type="text" id="endereco" placeholder="DIGITE CEP OU CIDADE...">
            <button onclick="buscarEndereco()">VIGIAR</button>
        </div>

        <div class="card">
            <div class="notch notch-left"></div>
            <div class="notch notch-right"></div>
            
            <div class="header">
                <span>✈</span> FLIGHT MANIFEST / PASS <span>✈</span>
            </div>
            
            <div class="white-area">
                <div class="col-left">
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
                
                <div class="col-right">
                    <div class="label">RANGE TO TARGET</div>
                    <div id="dist" class="value">0.0 KM</div>
                    <div class="barcode"></div>
                    <div class="scan-info">SECURITY SCAN: 25KM</div>
                </div>
            </div>

            <div class="footer">
                <div class="double-line"></div>
                <div id="status" class="status-msg">INITIALIZING...</div>
            </div>
        </div>

        <script>
            const audioAlerta = new Audio('https://www.soundjay.com/buttons/beep-07a.mp3');
            const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/:- ";
            let latAlvo = null, lonAlvo = null;
            let targetLock = false;
            let systemTime = "--:--:--";
            let frasesVigia = ["RADAR ACTIVE", "SCANNING AIRSPACE", "SECTOR SECURED"];
            let frasesTarget = ["TARGET LOCKED", "TRACKING FLIGHT", "SIGNAL STABLE"];
            let indiceFrase = 0;

            function ativarAlertas() { audioAlerta.play().then(() => audioAlerta.pause()); }

            function splitFlapEffect(finalText) {
                const elem = document.getElementById('status');
                let iterations = 0;
                const interval = setInterval(() => {
                    elem.innerText = finalText.split('').map((char, index) => {
                        if (iterations > index + 2) return char;
                        return chars[Math.floor(Math.random() * chars.length)];
                    }).join('');
                    if (iterations > finalText.length + 5) {
                        elem.innerText = finalText;
                        clearInterval(interval);
                    }
                    iterations++;
                }, 40);
            }

            function rotacionar() {
                let lista = targetLock ? frasesTarget : frasesVigia;
                let msg = lista[indiceFrase % lista.length] + " [" + systemTime + "]";
                splitFlapEffect(msg);
                indiceFrase++;
                setTimeout(rotacionar, 6000);
            }

            window.onload = function() {
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude;
                    systemTime = new Date().toLocaleTimeString();
                    rotacionar();
                    iniciarRadar();
                }, () => {
                    document.getElementById('busca').style.display = "flex";
                    rotacionar();
                });
            };

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
                        document.getElementById('callsign').innerText = "SCANNING";
                    }
                });
            }

            async function buscarEndereco() {
                const query = document.getElementById('endereco').value;
                const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${query}`);
                const data = await res.json();
                if(data.length > 0) {
                    latAlvo = parseFloat(data[0].lat); lonAlvo = parseFloat(data[0].lon);
                    iniciarRadar();
                }
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





