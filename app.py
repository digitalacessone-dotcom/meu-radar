from flask import Flask, render_template_string, jsonify, request
import requests
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

RAIO_KM = 50.0 

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1-a))

def calculate_bearing(lat1, lon1, lat2, lon2):
    start_lat, start_lon = radians(lat1), radians(lon1)
    end_lat, end_lon = radians(lat2), radians(lon2)
    d_lon = end_lon - start_lon
    y = sin(d_lon) * cos(end_lat)
    x = cos(start_lat) * sin(end_lat) - sin(start_lat) * cos(end_lat) * cos(d_lon)
    return (degrees(atan2(y, x)) + 360) % 360

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Manifesto de Voo Profissional</title>
        <style>
            :root { --air-blue: #1A237E; --warning-gold: #FFD700; --bg-dark: #050b14; }
            
            body { 
                background-color: var(--bg-dark); 
                display: flex; flex-direction: column; align-items: center; justify-content: center; 
                min-height: 100vh; margin: 0; font-family: 'Courier New', monospace;
                background-image: radial-gradient(circle at center, #1a2a44 0%, #050b14 100%);
            }

            /* EFEITO DE DOBRA E TEXTURA DE PAPEL */
            .card { 
                background: #fdfdfd; width: 95%; max-width: 650px; border-radius: 4px; 
                position: relative; box-shadow: 0 30px 60px rgba(0,0,0,0.8);
                overflow: hidden; transition: transform 0.3s ease;
                background-image: url('https://www.transparenttextures.com/patterns/p6.png'); /* Textura de papel */
            }
            .card::after { /* Sombra da dobra */
                content: ""; position: absolute; top: 0; left: 0; right: 0; bottom: 0;
                background: linear-gradient(135deg, rgba(255,255,255,0) 45%, rgba(0,0,0,0.05) 50%, rgba(255,255,255,0) 55%);
                pointer-events: none;
            }

            .blue-header { background: var(--air-blue); color: white; padding: 15px; display: flex; justify-content: space-between; align-items: center; }
            .airline-info { font-size: 0.7em; font-weight: bold; letter-spacing: 1px; }

            /* PICOTE ANIMADO */
            .tear-line { 
                border-right: 2px dashed #ccc; position: absolute; right: 30%; top: 0; bottom: 0; z-index: 5;
            }
            .tear-line.active { border-right-color: var(--warning-gold); box-shadow: -2px 0 10px var(--warning-gold); animation: blink 1s infinite; }
            @keyframes blink { 50% { opacity: 0.3; } }

            .white-area { display: flex; padding: 25px; min-height: 280px; position: relative; }
            .col-main { flex: 2; padding-right: 20px; }
            .col-stub { flex: 1; border-left: 1px solid #eee; padding-left: 20px; display: flex; flex-direction: column; align-items: center; text-align: center; }

            /* CARIMBO DE IMIGRAÇÃO */
            .stamp {
                position: absolute; top: 50%; left: 40%; transform: translate(-50%, -50%) rotate(-15deg);
                border: 4px double #d32f2f; color: #d32f2f; padding: 10px 20px; font-weight: 900;
                font-size: 1.5em; border-radius: 10px; opacity: 0; transition: opacity 0.5s;
                text-transform: uppercase; pointer-events: none; z-index: 10;
                background: rgba(211, 47, 47, 0.05);
            }
            .stamp.visible { opacity: 0.4; }

            .label { color: #888; font-size: 0.65em; font-weight: 800; margin-bottom: 2px; }
            .value { font-size: 1.5em; font-weight: 900; color: #111; margin-bottom: 15px; }
            
            #compass { font-size: 1.5em; color: var(--air-blue); display: inline-block; transition: 0.5s; }
            
            .footer { background: #eee; padding: 15px; }
            .yellow-bar { background: var(--warning-gold); padding: 8px; text-align: center; font-weight: 900; font-size: 0.8em; color: #000; }

            /* PAINEL DE SEGURANÇA (BACK) */
            .safety-tips { font-size: 0.6em; color: #666; margin-top: 10px; display: flex; gap: 10px; justify-content: center; }
            .tip-icon { border: 1px solid #666; border-radius: 50%; width: 15px; height: 15px; display: inline-block; text-align: center; }

        </style>
    </head>
    <body>

        <div class="card" id="ticket">
            <div class="blue-header">
                <div class="airline-info">FLIGHT MANIFEST / <span id="airline-name">GENERAL AVIATION</span></div>
                <div style="font-size: 1.2em;">✈</div>
            </div>

            <div class="white-area">
                <div class="stamp" id="main-stamp">VISUAL CONTACT</div>
                <div class="tear-line" id="tear"></div>

                <div class="col-main">
                    <div class="label">PASSENGER/CALLSIGN</div>
                    <div id="callsign" class="value" style="font-size: 2.2em;">SEARCHING</div>
                    
                    <div style="display: flex; gap: 20px;">
                        <div><div class="label">ALTITUDE</div><div id="alt" class="value">---</div></div>
                        <div><div class="label">SPEED</div><div id="speed" class="value">---</div></div>
                    </div>
                    
                    <div class="label">SAFETY INSTRUCTIONS</div>
                    <div class="safety-tips">
                        <span><span class="tip-icon">!</span> EYE PROTECTION</span>
                        <span><span class="tip-icon">!</span> BINOCULARS RDY</span>
                    </div>
                </div>

                <div class="col-stub">
                    <div class="label">BEARING</div>
                    <div id="compass">↑</div>
                    <div id="dist" class="value" style="margin-top:10px;">0.0 KM</div>
                    <div class="label">EST. VISUAL</div>
                    <div id="eta" class="value" style="color:var(--air-blue)">-- MIN</div>
                </div>
            </div>

            <div class="footer">
                <div id="status-bar" class="yellow-bar">RADAR SYSTEM STANDBY...</div>
            </div>
        </div>

        <script>
            const audioAlerta = new Audio('https://www.soundjay.com/buttons/beep-07a.mp3');
            let latAlvo, lonAlvo;
            let targetLock = false;
            let flightData = null;
            let weatherData = { temp: "--", vis: "--", desc: "---" };

            window.onload = function() {
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude;
                    iniciarRadar();
                });
            };

            function updateAirline(callsign) {
                const nameEl = document.getElementById('airline-name');
                if(callsign.startsWith('TAM') || callsign.startsWith('LAT')) nameEl.innerText = "OPERATED BY LATAM";
                else if(callsign.startsWith('GLO')) nameEl.innerText = "OPERATED BY GOL";
                else if(callsign.startsWith('AZU')) nameEl.innerText = "OPERATED BY AZUL";
                else nameEl.innerText = "GENERAL AVIATION";
            }

            function iniciarRadar() {
                setInterval(executarBusca, 8000);
                
                // Ciclo do Rodapé Amarelo
                let cycle = 0;
                setInterval(() => {
                    const bar = document.getElementById('status-bar');
                    const msgs = targetLock ? [
                        `LOCKED: ${flightData.callsign}`,
                        `FROM: ${flightData.origin}`,
                        `TO: ${flightData.dest}`,
                        `VISIBILITY: ${weatherData.vis} KM`
                    ] : [
                        "SCANNING AIRSPACE",
                        `TEMP: ${weatherData.temp}°C | ${weatherData.desc}`,
                        "CHECKING RADARBOX...",
                        "VILA VELHA UPLINK OK"
                    ];
                    bar.innerText = msgs[cycle % msgs.length];
                    cycle++;
                }, 4000);
            }

            function executarBusca() {
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}`)
                .then(res => res.json()).then(data => {
                    weatherData = data.weather;
                    if(data.found) {
                        flightData = data;
                        document.getElementById('callsign').innerText = data.callsign;
                        document.getElementById('alt').innerText = Math.round(data.alt * 3.28) + " FT";
                        document.getElementById('speed').innerText = data.speed + " KM/H";
                        document.getElementById('dist').innerText = data.dist + " KM";
                        document.getElementById('eta').innerText = (data.speed > 0 ? Math.round(data.dist/data.speed*60) : "--") + " MIN";
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        
                        // Efeitos Visuais do Bilhete
                        document.getElementById('main-stamp').classList.add('visible');
                        updateAirline(data.callsign);
                        
                        // Picote brilha se perto
                        if(data.dist < 15) document.getElementById('tear').classList.add('active');
                        else document.getElementById('tear').classList.remove('active');

                        if(!targetLock) audioAlerta.play();
                        targetLock = true;
                    } else {
                        targetLock = false;
                        document.getElementById('main-stamp').classList.remove('visible');
                        document.getElementById('tear').classList.remove('active');
                        document.getElementById('callsign').innerText = "SEARCHING";
                    }
                });
            }
        </script>
    </body>
    </html>
    ''')

@app.route('/api/data')
def get_data():
    lat_u = float(request.args.get('lat', 0))
    lon_u = float(request.args.get('lon', 0))
    
    # Busca Clima
    weather = {"temp": "--", "vis": "--", "desc": "CLOUDY"}
    try:
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat_u}&longitude={lon_u}&current=temperature_2m,visibility,weather_code"
        wr = requests.get(w_url, timeout=2).json()
        weather = {
            "temp": round(wr['current']['temperature_2m']),
            "vis": round(wr['current']['visibility']/1000, 1),
            "desc": "CLEAR" if wr['current']['weather_code'] == 0 else "RAINY" if wr['current']['weather_code'] > 50 else "CLOUDY"
        }
    except: pass

    # Busca Aeronave
    try:
        url = f"https://api.adsb.lol/v2/lat/{lat_u}/lon/{lon_u}/dist/{RAIO_KM}"
        r = requests.get(url, timeout=3).json()
        if r.get('ac'):
            ac = sorted(r['ac'], key=lambda x: haversine(lat_u, lon_u, x.get('lat',0), x.get('lon',0)))[0]
            return jsonify({
                "found": True, "callsign": ac.get('flight', 'UNKN').strip(),
                "dist": round(haversine(lat_u, lon_u, ac['lat'], ac['lon']), 1),
                "alt": ac.get('alt_baro', 0) / 3.28,
                "bearing": calculate_bearing(lat_u, lon_u, ac['lat'], ac['lon']),
                "speed": round(ac.get('gs', 0) * 1.852),
                "origin": ac.get('db_origin', 'N/A'), "dest": ac.get('db_dest', 'N/A'),
                "weather": weather
            })
    except: pass
    return jsonify({"found": False, "weather": weather})

if __name__ == '__main__':
    app.run(debug=True)














