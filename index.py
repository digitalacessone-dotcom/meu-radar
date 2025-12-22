# -*- coding: utf-8 -*-
# ==============================================================================
# TERMINAL RADAR SYSTEM - VERSION 107.2
# FULL GLOBAL FLEET DATABASE & REGIONAL BRAZIL CALIBRATION
# UPDATED: DEC 2025 | STATUS: PRODUCTION READY | TICKER: ENGLISH ONLY
# ==============================================================================

from flask import Flask, jsonify, request, render_template_string
import requests
import math
import random
from datetime import datetime, timedelta

app = Flask(__name__)

# --- CONFIGURAÇÕES TÉCNICAS DO RADAR ---
# Alcance em KM para detecção de aeronaves ao redor do ponto central
RADIUS_KM = 190 
# Coordenadas padrão (Rio de Janeiro) caso o GPS falhe
DEFAULT_LAT = -22.9068
DEFAULT_LON = -43.1729

def get_time_local():
    """
    Calcula e retorna o horário oficial de Brasília.
    Ajuste de fuso horário UTC-3.
    """
    return datetime.utcnow() - timedelta(hours=3)

def get_weather_desc(code):
    """
    Mapeamento universal de códigos meteorológicos WMO em Inglês para o Ticker.
    """
    mapping = {
        0: "CLEAR SKY", 
        1: "MAINLY CLEAR", 
        2: "PARTLY CLOUDY", 
        3: "OVERCAST", 
        45: "FOGGY", 
        48: "RIME FOG",
        51: "LIGHT DRIZZLE", 
        61: "LIGHT RAIN", 
        71: "LIGHT SNOW",
        80: "RAIN SHOWERS",
        95: "THUNDERSTORM"
    }
    return mapping.get(code, "STABLE")

def get_weather(lat, lon):
    """
    Consulta a API Open-Meteo para obter telemetria climática.
    Retorna temperatura, estado do céu e visibilidade em KM.
    """
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code,visibility"
        resp = requests.get(url, timeout=5).json()
        curr = resp['current']
        vis_km = int(curr.get('visibility', 10000) / 1000)
        return {
            "temp": f"{int(curr['temperature_2m'])}C", 
            "sky": get_weather_desc(curr['weather_code']), 
            "vis": f"{vis_km}KM"
        }
    except Exception as e:
        return {"temp": "--C", "sky": "METAR ON", "vis": "--KM"}

def fetch_aircrafts(lat, lon):
    """
    Realiza a varredura do espaço aéreo usando 3 endpoints ADS-B.
    Garante redundância caso um servidor de dados esteja offline.
    """
    endpoints = [
        f"https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/200",
        f"https://opendata.adsb.fi/api/v2/lat/{lat}/lon/{lon}/dist/200",
        f"https://api.adsb.one/v2/lat/{lat}/lon/{lon}/dist/200"
    ]
    headers = {'User-Agent': 'RadarSystem_V107_2/2025', 'Accept': 'application/json'}
    all_aircraft = []
    
    for url in endpoints:
        try:
            r = requests.get(url, headers=headers, timeout=4)
            if r.status_code == 200:
                data = r.json().get('aircraft', [])
                if data: 
                    all_aircraft.extend(data)
                    break 
        except:
            continue
            
    # Remove duplicatas baseadas no endereço HEX único do transponder ICAO
    unique_data = {a['hex']: a for a in all_aircraft if 'hex' in a}.values()
    return list(unique_data)

@app.route('/api/radar')
def radar():
    """
    Endpoint principal: Processa telemetria e identifica as companhias.
    """
    try:
        lat = float(request.args.get('lat', DEFAULT_LAT))
        lon = float(request.args.get('lon', DEFAULT_LON))
        test = request.args.get('test', 'false').lower() == 'true'
        
        local_now = get_time_local()
        now_date = local_now.strftime("%d %b %Y").upper()
        now_time = local_now.strftime("%H.%M")
        w = get_weather(lat, lon)
        
        if test:
            f = {
                "icao": "SQ321", "reg": "9V-SWM", "call": "SIA321", 
                "airline": "SINGAPORE AIRLINES", "color": "#002244", "is_rare": True, 
                "dist": 14.8, "alt": 39000, "spd": 905, "hd": 265, 
                "date": now_date, "time": now_time, "route": "SIN -> GRU", 
                "eta": 2, "kts": 488, "vrate": 0
            }
            return jsonify({"flight": f, "weather": w, "date": now_date, "time": now_time})
        
        data = fetch_aircrafts(lat, lon)
        found = None
        
        if data:
            proc = []
            for s in data:
                slat, slon = s.get('lat'), s.get('lon')
                if slat and slon:
                    d = 6371 * 2 * math.asin(math.sqrt(math.sin(math.radians(slat-lat)/2)**2 + math.cos(math.radians(lat)) * math.cos(math.radians(slat)) * math.sin(math.radians(slon-lon)/2)**2))
                    
                    if d <= RADIUS_KM:
                        call = (s.get('flight') or s.get('call') or 'N/A').strip().upper()
                        airline, color, is_rare = "PRIVATE AVIATION", "#444", False
                        
                        # --- DATABASE DE IDENTIDADE VISUAL ---
                        # 1. REGIONAIS BRASIL
                        if call.startswith("ABJ"): airline, color = "ABAETÉ AVIAÇÃO", "#004A99"
                        elif call.startswith("ASO"): airline, color = "AEROSUL", "#E30613"
                        elif call.startswith("SST"): airline, color = "ASTA LINHAS", "#003366"
                        elif call.startswith("NWG"): airline, color = "AVION EXPRESS BR", "#CC0000"
                        elif call.startswith(("TTL", "TOT")): airline, color = "TOTAL LINHAS", "#005544"
                        elif call.startswith(("PTB", "2Z")): airline, color = "VOEPASS", "#F9A825"
                        
                        # 2. NACIONAL / INTERNACIONAL BRASIL
                        elif call.startswith(("TAM", "JJ", "LA")): airline, color = "LATAM BRASIL", "#1b0088"
                        elif call.startswith(("GLO", "G3")): airline, color = "GOL AIRLINES", "#FF5A00"
                        elif call.startswith(("AZU", "AD")): airline, color = "AZUL LINHAS", "#00205B"
                        
                        # 3. SKYTRAX TOP 2025 & GLOBAIS
                        elif call.startswith("QTR"): airline, color, is_rare = "QATAR AIRWAYS", "#5A0225", True
                        elif call.startswith("SIA"): airline, color, is_rare = "SINGAPORE AIR", "#002244", True
                        elif call.startswith("CPA"): airline, color, is_rare = "CATHAY PACIFIC", "#006564", True
                        elif call.startswith("UAE"): airline, color = "EMIRATES", "#FF0000"
                        elif call.startswith("ANA"): airline, color = "ANA JAPAN", "#0044BB"
                        elif call.startswith("THY"): airline, color = "TURKISH AIRLINES", "#C8102E"
                        elif call.startswith("KAL"): airline, color = "KOREAN AIR", "#003399"
                        elif call.startswith("AFR"): airline, color = "AIR FRANCE", "#002395"
                        elif call.startswith("AAL"): airline, color = "AMERICAN AIRLINES", "#0078D2"
                        elif call.startswith("DAL"): airline, color = "DELTA AIR LINES", "#E01933"
                        elif call.startswith("UAL"): airline, color = "UNITED AIRLINES", "#005DAA"
                        elif call.startswith("DLH"): airline, color = "LUFTHANSA", "#001F3F"
                        elif call.startswith("CSN"): airline, color = "CHINA SOUTHERN", "#0066CC"
                        
                        # 4. CARGUEIRAS & MERCADO LIVRE
                        elif "MLBR" in call or "MELI" in call: airline, color, is_rare = "MERCADO LIVRE", "#FFE600", True
                        elif call.startswith("FDX"): airline, color = "FEDEX EXPRESS", "#4D148C"
                        elif call.startswith("UPS"): airline, color = "UPS CARGO", "#351C15"
                        elif call.startswith("DHL"): airline, color = "DHL LOGISTICS", "#D40511"
                        
                        # 5. MILITAR
                        elif s.get('mil'): airline, color, is_rare = "AIR FORCE", "#000", True
                        
                        spd_kts = int(s.get('gs', 0))
                        spd_kmh = int(spd_kts * 1.852)
                        
                        proc.append({
                            "icao": s.get('hex', 'UNK').upper(), 
                            "reg": s.get('r', 'N/A').upper(), 
                            "call": call, 
                            "airline": airline, 
                            "color": color, 
                            "is_rare": is_rare, 
                            "dist": round(d, 1), 
                            "alt": int(s.get('alt_baro', 0) if s.get('alt_baro') != "ground" else 0), 
                            "spd": spd_kmh, 
                            "kts": spd_kts, 
                            "hd": int(s.get('track', 0)), 
                            "date": now_date, 
                            "time": now_time, 
                            "route": s.get('route', "--- ---"), 
                            "eta": round((d/(spd_kmh or 1))*60)
                        })
            
            if proc:
                proc.sort(key=lambda x: x['dist'])
                found = proc[0]
                
        return jsonify({"flight": found, "weather": w, "date": now_date, "time": now_time})
    except:
        return jsonify({"flight": None})

@app.route('/')
def index():
    """Interface Principal em HTML/JS"""
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <style>
        :root { --gold: #FFD700; --bg: #0b0e11; --brand: #444; --blue-txt: #34a8c9; }
        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body { background: var(--bg); font-family: -apple-system, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100dvh; margin: 0; perspective: 1500px; overflow: hidden; }
        
        #ui { width: 280px; display: flex; gap: 6px; margin-bottom: 15px; z-index: 500; transition: opacity 0.8s; }
        #ui.hide { opacity: 0; pointer-events: none; }
        input { flex: 1; padding: 14px; border-radius: 12px; border: none; background: #1a1d21; color: #fff; font-size: 11px; outline: none; }
        button { background: #fff; border: none; padding: 0 18px; border-radius: 12px; font-weight: 900; }
        
        .scene { width: 310px; height: 480px; position: relative; transform-style: preserve-3d; transition: transform 0.8s cubic-bezier(0.4, 0, 0.2, 1); }
        .scene.flipped { transform: rotateY(180deg); }
        .face { position: absolute; width: 100%; height: 100%; backface-visibility: hidden; border-radius: 24px; background: #fff; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 25px 60px rgba(0,0,0,0.6); }
        .face.back { transform: rotateY(180deg); background: #fafafa; padding: 20px; }
        
        .stub { height: 32%; background: var(--brand); color: #fff; padding: 25px; display: flex; flex-direction: column; justify-content: center; transition: 0.6s; }
        .stub.rare-mode { background: #000 !important; color: var(--gold) !important; }
        .dots-container { display: flex; gap: 5px; margin-top: 10px; }
        .sq { width: 12px; height: 12px; border: 1.5px solid rgba(255,255,255,0.2); background: rgba(0,0,0,0.1); border-radius: 3px; }
        .sq.on { background: var(--gold); border-color: var(--gold); box-shadow: 0 0 12px var(--gold); }
        
        .perfor { height: 4px; border-top: 6px dotted #ddd; position: relative; background: #fff; }
        .perfor::before, .perfor::after { content:""; position:absolute; width:34px; height:34px; background:var(--bg); border-radius:50%; top:-17px; }
        .perfor::before { left:-28px; } .perfor::after { right:-28px; }
        
        .main { flex: 1; padding: 25px; display: flex; flex-direction: column; justify-content: space-between; }
        .flap { font-family: "Courier New", monospace; font-size: 20px; font-weight: 900; color: #000; height: 26px; display: flex; gap: 2px; }
        .char { width: 16px; height: 24px; background: #f4f4f4; border-radius: 4px; display: flex; align-items: center; justify-content: center; }
        
        .ticker { width: 320px; height: 35px; background: #000; border-radius: 8px; margin-top: 20px; display: flex; align-items: center; justify-content: center; color: var(--gold); font-family: monospace; font-size: 11px; letter-spacing: 2px; text-transform: uppercase; }
        #bc { width: 120px; height: 40px; opacity: 0.3; cursor: pointer; }

        @media (orientation: landscape) {
            .scene { width: 580px; height: 280px; }
            .face { flex-direction: row !important; }
            .stub { width: 30% !important; height: 100% !important; }
            .perfor { width: 4px !important; height: 100% !important; border-left: 6px dotted #ddd !important; border-top: none !important; }
            .main { width: 70% !important; }
        }
    </style>
</head>
<body onclick="handleFlip(event)">
    <div id="ui">
        <input type="text" id="in" placeholder="TYPE LOCATION (EX: LONDON)">
        <button onclick="startSearch()">SCAN</button>
    </div>

    <div class="scene" id="card">
        <div class="face front">
            <div class="stub" id="stb">
                <div style="font-size:8px; font-weight:900; opacity:0.8; letter-spacing:1px;">FLIGHT RADAR 2025</div>
                <div style="font-size:11px; font-weight:900; margin-top:6px;" id="airl">SEARCHING...</div>
                <div style="font-size:68px; font-weight:900; letter-spacing:-5px; margin:4px 0;">19A</div>
                <div class="dots-container">
                    <div id="d1" class="sq"></div><div id="d2" class="sq"></div><div id="d3" class="sq"></div><div id="d4" class="sq"></div><div id="d5" class="sq"></div>
                </div>
            </div>
            <div class="perfor"></div>
            <div class="main">
                <div style="color: #333; font-weight: 900; font-size: 13px; border: 1.5px solid #333; padding: 4px 12px; border-radius: 6px; align-self: flex-start; letter-spacing: 1px;">BOARDING PASS</div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:15px; margin-top:15px;">
                    <div><span style="font-size: 8px; color: #aaa; font-weight: 900;">AIRCRAFT ICAO</span><div id="f-icao" class="flap"></div></div>
                    <div><span style="font-size: 8px; color: #aaa; font-weight: 900;">DISTANCE</span><div id="f-dist" class="flap"></div></div>
                    <div><span style="font-size: 8px; color: #aaa; font-weight: 900;">CALLSIGN</span><div id="f-call" class="flap"></div></div>
                    <div><span style="font-size: 8px; color: #aaa; font-weight: 900;">PROBABLE ROUTE</span><div id="f-route" class="flap"></div></div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-top: 10px;">
                    <div id="arr" style="font-size:50px; transition: 2s cubic-bezier(0.16, 1, 0.3, 1);">✈</div>
                    <div style="text-align:right;">
                        <div id="f-date" style="font-size:11px; font-weight:900; color:var(--blue-txt);">-- --- ----</div>
                        <img id="bc" src="https://bwipjs-api.metafloor.com/?bcid=code128&text=RADAR2025" onclick="openMap(event)">
                    </div>
                </div>
            </div>
        </div>

        <div class="face back">
            <div style="height:100%; border:1.5px dashed #ddd; border-radius:18px; padding:25px; display:flex; flex-direction:column;">
                <div><span style="font-size:8px; color:#aaa; font-weight:900;">ALTITUDE</span><div id="b-alt" class="flap"></div></div>
                <div style="margin-top:25px;"><span style="font-size:8px; color:#aaa; font-weight:900;">GROUND SPEED</span><div id="b-spd" class="flap"></div></div>
                <div style="margin-top:auto; border:2.5px solid var(--blue-txt); padding:15px; border-radius:12px; color:var(--blue-txt); text-align:center; font-weight:900; transform:rotate(-6deg);">
                    <div style="font-size:9px;">SECURITY CHECKED</div>
                    <div id="b-time" style="font-size:24px;">00.00</div>
                    <div style="font-size:9px;">GLOBAL RADAR V107.2</div>
                </div>
            </div>
        </div>
    </div>

    <div class="ticker" id="tk">INITIALIZING AIRSPACE SCAN...</div>

    <script>
        let pos = null, act = null, isTest = false;
        const chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ.- ";

        function applyFlap(id, text) {
            const container = document.getElementById(id);
            if(!container) return;
            const target = text.toUpperCase().padEnd(8, ' ');
            container.innerHTML = '';
            [...target].forEach(char => {
                const span = document.createElement('span');
                span.className = 'char';
                span.innerHTML = '&nbsp;';
                container.appendChild(span);
                let count = 0, max = 35 + Math.floor(Math.random()*40);
                const interval = setInterval(() => {
                    span.innerText = chars[Math.floor(Math.random()*chars.length)];
                    if(count++ >= max) {
                        clearInterval(interval);
                        span.innerHTML = (char === ' ') ? '&nbsp;' : char;
                    }
                }, 25);
            });
        }

        async function update() {
            if(!pos) return;
            try {
                const r = await fetch(`/api/radar?lat=${pos.lat}&lon=${pos.lon}&test=${isTest}&_=${Date.now()}`);
                const d = await r.json();
                if(d.flight) {
                    const f = d.flight, stub = document.getElementById('stb');
                    stub.style.background = f.color;
                    stub.style.color = (f.color === "#FFE600") ? "#000" : "#fff";
                    if(f.is_rare) stub.classList.add('rare-mode'); else stub.classList.remove('rare-mode');
                    document.getElementById('airl').innerText = f.airline;
                    document.getElementById('f-date').innerText = d.date;
                    document.getElementById('b-time').innerText = d.time;
                    if(!act || act.icao !== f.icao) {
                        applyFlap('f-icao', f.icao);
                        applyFlap('f-call', f.call);
                        applyFlap('f-route', f.route);
                        document.getElementById('bc').src = `https://bwipjs-api.metafloor.com/?bcid=code128&text=${f.icao}&scale=2`;
                    }
                    applyFlap('f-dist', f.dist + "KM");
                    applyFlap('b-alt', f.alt + "FT");
                    applyFlap('b-spd', f.spd + "KMH");
                    for(let i=1; i<=5; i++) {
                        document.getElementById('d'+i).className = f.dist <= (190 - (i-1)*40) ? 'sq on' : 'sq';
                    }
                    document.getElementById('arr').style.transform = `rotate(${f.hd-45}deg)`;
                    // TICKER EM INGLÊS CONFORME SOLICITADO
                    document.getElementById('tk').innerText = `CONTACT: ${f.airline} | ${d.weather.temp} | ${d.weather.sky}`;
                    act = f;
                }
            } catch(e) { }
        }

        function startSearch() {
            const v = document.getElementById('in').value.toUpperCase();
            if(v === "TEST") { isTest = true; pos = {lat:-23.55, lon:-46.63}; hideUI(); }
            else {
                fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${v}`)
                .then(r => r.json())
                .then(d => {
                    if(d[0]) {
                        pos = {lat: parseFloat(d[0].lat), lon: parseFloat(d[0].lon)};
                        hideUI();
                    }
                });
            }
        }

        function handleFlip(e) {
            if(!e.target.closest('#ui') && !e.target.closest('#bc')) {
                document.getElementById('card').classList.toggle('flipped');
            }
        }

        function openMap(e) {
            e.stopPropagation();
            if(act) window.open(`https://globe.adsbexchange.com/?icao=${act.icao}`, '_blank');
        }

        function hideUI() {
            document.getElementById('ui').classList.add('hide');
            setInterval(update, 20000);
            update();
        }

        navigator.geolocation.getCurrentPosition(p => {
            pos = {lat: p.coords.latitude, lon: p.coords.longitude};
            hideUI();
        });
    </script>
</body>
</html>
''')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
