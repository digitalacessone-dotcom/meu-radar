# -*- coding: utf-8 -*-
# TERMINAL RADAR SYSTEM - VERSION 106.5
# OFFICIAL BRAND CALIBRATION - DEC 2025
from flask import Flask, jsonify, request, render_template_string
import requests
import math
import random
from datetime import datetime, timedelta

app = Flask(__name__)

# --- CONFIGURAÇÕES DE RADAR ---
RADIUS_KM = 190 
DEFAULT_LAT = -22.9068
DEFAULT_LON = -43.1729

def get_time_local():
    """Retorna o horário de Brasília"""
    return datetime.utcnow() - timedelta(hours=3)

def get_weather_desc(code):
    """Mapeamento de códigos meteorológicos"""
    mapping = {
        0: "CLEAR SKY", 1: "FEW CLOUDS", 2: "SCATTERED", 
        3: "OVERCAST", 45: "FOG", 51: "LIGHT DRIZZLE", 
        61: "RAIN", 80: "SHOWERS"
    }
    return mapping.get(code, "CONDITIONS OK")

def get_weather(lat, lon):
    """Consulta API de clima em tempo real"""
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
    except:
        return {"temp": "--C", "sky": "METAR ON", "vis": "--KM"}

def fetch_aircrafts(lat, lon):
    """Busca tráfego aéreo real em múltiplos endpoints"""
    endpoints = [
        f"https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/200",
        f"https://opendata.adsb.fi/api/v2/lat/{lat}/lon/{lon}/dist/200",
        f"https://api.adsb.one/v2/lat/{lat}/lon/{lon}/dist/200"
    ]
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}
    all_aircraft = []
    
    for url in endpoints:
        try:
            r = requests.get(url, headers=headers, timeout=4)
            if r.status_code == 200:
                data = r.json().get('aircraft', [])
                if data: all_aircraft.extend(data)
        except:
            continue
            
    # Remove duplicatas por HEX ICAO
    unique_data = {a['hex']: a for a in all_aircraft if 'hex' in a}.values()
    return list(unique_data)

@app.route('/api/radar')
def radar():
    """Processa dados do radar para o frontend"""
    try:
        lat = float(request.args.get('lat', DEFAULT_LAT))
        lon = float(request.args.get('lon', DEFAULT_LON))
        current_icao = request.args.get('current_icao', None)
        test = request.args.get('test', 'false').lower() == 'true'
        
        local_now = get_time_local()
        now_date = local_now.strftime("%d %b %Y").upper()
        now_time = local_now.strftime("%H.%M")
        w = get_weather(lat, lon)
        
        if test:
            f = {
                "icao": "ABC123", "reg": "61-7972", "call": "BLACKBIRD", 
                "airline": "SR-71 RARE", "color": "#000", "is_rare": True, 
                "dist": 15.2, "alt": 80000, "spd": 3200, "hd": 350, 
                "date": now_date, "time": now_time, "route": "BEALE-EDW", 
                "eta": 2, "kts": 1800, "vrate": 0
            }
            return jsonify({"flight": f, "weather": w, "date": now_date, "time": now_time})
        
        data = fetch_aircrafts(lat, lon)
        found = None
        
        if data:
            proc = []
            for s in data:
                slat, slon = s.get('lat'), s.get('lon')
                if slat and slon:
                    # Cálculo de distância Haversine
                    d = 6371 * 2 * math.asin(math.sqrt(math.sin(math.radians(slat-lat)/2)**2 + math.cos(math.radians(lat)) * math.cos(math.radians(slat)) * math.sin(math.radians(slon-lon)/2)**2))
                    
                    if d <= RADIUS_KM:
                        call = (s.get('flight') or s.get('call') or 'N/A').strip().upper()
                        airline, color, is_rare = "PRIVATE", "#444", False
                        
                        # FILTRO DE COMPANHIAS - CORES REAIS 2025
                        if s.get('mil') or s.get('t') in ['H60', 'C130', 'F16', 'F35', 'B52']:
                            airline, color, is_rare = "MILITARY", "#000", True
                        elif call.startswith(("TAM", "JJ", "LA")): 
                            airline, color = "LATAM BRASIL", "#1b0088" # Indigo Real
                        elif call.startswith(("GLO", "G3")): 
                            airline, color = "GOL AIRLINES", "#FF5A00" # Laranja Real
                        elif call.startswith(("AZU", "AD")): 
                            airline, color = "AZUL LINHAS", "#00205B" # Azul Marinho
                        elif call.startswith(("PTB", "2Z")): 
                            airline, color = "VOEPASS", "#F9A825"
                        elif call.startswith("QTR"): 
                            airline, color = "QATAR AIRWAYS", "#5A0225"
                        elif call.startswith("UAE"): 
                            airline, color = "EMIRATES", "#FF0000"
                        
                        spd_kts = int(s.get('gs', 0))
                        spd_kmh = int(spd_kts * 1.852)
                        eta = round((d / (spd_kmh or 1)) * 60)
                        
                        proc.append({
                            "icao": s.get('hex', 'UNK').upper(), 
                            "reg": s.get('r', 'N/A').upper(), 
                            "call": call, "airline": airline, 
                            "color": color, "is_rare": is_rare, 
                            "dist": round(d, 1), 
                            "alt": int(s.get('alt_baro', 0) if s.get('alt_baro') != "ground" else 0), 
                            "spd": spd_kmh, "kts": spd_kts, "hd": int(s.get('track', 0)), 
                            "date": now_date, "time": now_time, 
                            "route": s.get('route', "--- ---"), "eta": eta, 
                            "vrate": int(s.get('baro_rate', 0))
                        })
            
            if proc:
                proc.sort(key=lambda x: x['dist'])
                new_closest = proc[0]
                if current_icao:
                    current_on_radar = next((x for x in proc if x['icao'] == current_icao), None)
                    if current_on_radar:
                        # Mantém o atual a menos que o novo esteja muito mais perto
                        found = new_closest if new_closest['dist'] < (current_on_radar['dist'] - 5) else current_on_radar
                    else: found = new_closest
                else: found = new_closest
                
        return jsonify({"flight": found, "weather": w, "date": now_date, "time": now_time})
    except:
        return jsonify({"flight": None})

@app.route('/')
def index():
    """Interface Principal (HTML/CSS/JS)"""
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
        #ui { width: 280px; display: flex; gap: 6px; margin-bottom: 12px; z-index: 500; transition: opacity 0.8s; }
        #ui.hide { opacity: 0; pointer-events: none; }
        input { flex: 1; padding: 12px; border-radius: 12px; border: none; background: #1a1d21; color: #fff; font-size: 11px; outline: none; }
        button { background: #fff; border: none; padding: 0 15px; border-radius: 12px; font-weight: 900; }
        .scene { width: 300px; height: 460px; position: relative; transform-style: preserve-3d; transition: transform 0.8s; }
        .scene.flipped { transform: rotateY(180deg); }
        .face { position: absolute; width: 100%; height: 100%; backface-visibility: hidden; border-radius: 20px; background: #fff; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 20px 50px rgba(0,0,0,0.5); }
        .face.back { transform: rotateY(180deg); background: #fdfdfd; padding: 15px; }
        .stub { height: 32%; background: var(--brand); color: #fff; padding: 20px; display: flex; flex-direction: column; justify-content: center; transition: 0.5s; }
        .stub.rare-mode { background: #000 !important; color: var(--gold) !important; }
        .dots-container { display: flex; gap: 4px; margin-top: 8px; }
        .sq { width: 10px; height: 10px; border: 1.5px solid rgba(255,255,255,0.3); background: rgba(0,0,0,0.2); border-radius: 2px; transition: 0.3s; }
        .sq.on { background: var(--gold); border-color: var(--gold); box-shadow: 0 0 10px var(--gold); }
        .perfor { height: 2px; border-top: 5px dotted #ccc; position: relative; background: #fff; }
        .perfor::before, .perfor::after { content:""; position:absolute; width:30px; height:30px; background:var(--bg); border-radius:50%; top:-15px; }
        .perfor::before { left:-25px; } .perfor::after { right:-25px; }
        .main { flex: 1; padding: 20px; display: flex; flex-direction: column; justify-content: space-between; }
        .flap { font-family: monospace; font-size: 18px; font-weight: 900; color: #000; height: 24px; display: flex; gap: 1px; }
        .char { width: 14px; height: 22px; background: #f0f0f0; border-radius: 3px; display: flex; align-items: center; justify-content: center; }
        .date-visual { color: var(--blue-txt); font-weight: 900; line-height: 0.95; text-align: right; }
        #bc { width: 110px; height: 35px; opacity: 0.15; filter: grayscale(1); cursor: pointer; margin-top: 5px; }
        .ticker { width: 310px; height: 32px; background: #000; border-radius: 6px; margin-top: 15px; display: flex; align-items: center; justify-content: center; color: var(--gold); font-family: monospace; font-size: 11px; letter-spacing: 2px; white-space: pre; }
        .metal-seal { position: absolute; bottom: 30px; right: 30px; width: 85px; height: 85px; border-radius: 50%; background: radial-gradient(circle, #f9e17d 0%, #d4af37 40%, #b8860b 100%); border: 2px solid #8a6d3b; box-shadow: 0 4px 10px rgba(0,0,0,0.3), inset 0 0 10px rgba(255,255,255,0.5); display: none; flex-direction: column; align-items: center; justify-content: center; transform: rotate(15deg); z-index: 10; border-style: double; border-width: 4px; }
        .metal-seal span { color: #5c4412; font-size: 8px; font-weight: 900; text-align: center; text-transform: uppercase; line-height: 1; padding: 2px; }
        @media (orientation: landscape) { .scene { width: 550px; height: 260px; } .face { flex-direction: row !important; } .stub { width: 30% !important; height: 100% !important; } .perfor { width: 2px !important; height: 100% !important; border-left: 5px dotted #ccc !important; border-top: none !important; } .main { width: 70% !important; } .ticker { width: 550px; } }
    </style>
</head>
<body onclick="handleFlip(event)">
    <div id="ui">
        <input type="text" id="in" placeholder="ENTER LOCATION">
        <button onclick="startSearch()">CHECK-IN</button>
    </div>
    <div class="scene" id="card">
        <div class="face front">
            <div class="stub" id="stb">
                <div style="font-size:7px; font-weight:900; opacity:0.7;">RADAR SCANNING</div>
                <div style="font-size:10px; font-weight:900; margin-top:5px;" id="airl">SEARCHING...</div>
                <div style="font-size:65px; font-weight:900; letter-spacing:-4px; margin:2px 0;">19A</div>
                <div class="dots-container" id="dots">
                    <div id="d1" class="sq"></div><div id="d2" class="sq"></div><div id="d3" class="sq"></div><div id="d4" class="sq"></div><div id="d5" class="sq"></div>
                </div>
            </div>
            <div class="perfor"></div>
            <div class="main">
                <div style="color: #333; font-weight: 900; font-size: 13px; border: 1.5px solid #333; padding: 3px 10px; border-radius: 4px; align-self: flex-start;">BOARDING PASS</div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:10px;">
                    <div><span id="icao-label" style="font-size: 7px; font-weight: 900; color: #bbb;">AIRCRAFT ICAO</span><div id="f-icao" class="flap"></div></div>
                    <div><span id="dist-label" style="font-size: 7px; font-weight: 900; color: #bbb;">DISTANCE</span><div id="f-dist" class="flap" style="color:#666"></div></div>
                    <div><span style="font-size: 7px; font-weight: 900; color: #bbb;">FLIGHT IDENTIFICATION</span><div id="f-call" class="flap"></div></div>
                    <div><span style="font-size: 7px; font-weight: 900; color: #bbb;">ROUTE (AT-TO)</span><div id="f-route" class="flap"></div></div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                    <div id="arr" style="font-size:45px; transition:1.5s;">✈</div>
                    <div class="date-visual">
                        <div id="f-line1">-- --- ----</div>
                        <div id="f-line2">--.--</div>
                        <img id="bc" src="https://bwipjs-api.metafloor.com/?bcid=code128&text=WAITING" onclick="openMap(event)">
                    </div>
                </div>
            </div>
        </div>
        <div class="face back">
            <div style="height:100%; border:1px dashed #ccc; border-radius:15px; padding:20px; display:flex; flex-direction:column; position:relative;">
                <div style="display:flex; justify-content:space-between;">
                    <div><span style="font-size: 7px; font-weight: 900; color: #bbb;">ALTITUDE</span><div id="b-alt" class="flap"></div></div>
                    <div><span id="spd-label" style="font-size: 7px; font-weight: 900; color: #bbb;">GROUND SPEED</span><div id="b-spd" class="flap"></div></div>
                </div>
                <div style="border: 3px double var(--blue-txt); color: var(--blue-txt); padding: 15px; border-radius: 10px; transform: rotate(-10deg); align-self: center; margin-top: 30px; text-align: center; font-weight: 900;">
                    <div style="font-size:8px;">SECURITY CHECKED</div>
                    <div id="b-date-line1">-- --- ----</div>
                    <div id="b-date-line2" style="font-size:22px;">--.--</div>
                    <div style="font-size:8px; margin-top:5px;">RADAR CONTACT V106.5</div>
                </div>
                <div id="gold-seal" class="metal-seal">
                    <span>Rare</span>
                    <span style="font-size:10px;">Aircraft</span>
                    <span>Found</span>
                </div>
            </div>
        </div>
    </div>
    <div class="ticker" id="tk">WAITING...</div>
    <script>
        let pos = null, act = null, isTest = false;
        let toggleState = true, tickerMsg = [], tickerIdx = 0, audioCtx = null;
        let lastDist = null;
        const chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ.- ";

        function playPing() {
            try {
                if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                osc.type = 'sine'; osc.frequency.setValueAtTime(880, audioCtx.currentTime); 
                gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.5);
                osc.connect(gain); gain.connect(audioCtx.destination);
                osc.start(); osc.stop(audioCtx.currentTime + 0.5);
            } catch(e) {}
        }

        function applyFlap(id, text, isTicker = false) {
            const container = document.getElementById(id);
            if(!container) return;
            const limit = isTicker ? 32 : 8;
            const target = text.toUpperCase().padEnd(limit, ' ');
            container.innerHTML = '';
            [...target].forEach((char) => {
                const span = document.createElement('span');
                if(!isTicker) span.className = 'char';
                span.innerHTML = '&nbsp;';
                container.appendChild(span);
                let count = 0;
                let max = 40 + Math.floor(Math.random() * 80); 
                const interval = setInterval(() => {
                    span.innerText = chars[Math.floor(Math.random() * chars.length)];
                    if (count++ >= max) { 
                        clearInterval(interval); 
                        span.innerHTML = (char === ' ') ? '&nbsp;' : char; 
                    }
                }, 20);
            });
        }

        function saveHistory(f) {
            if(isTest) return;
            if(!f.is_rare) return;
            let history = JSON.parse(localStorage.getItem('rare_flights') || '[]');
            if(!history.find(x => x.icao === f.icao)) {
                history.push({icao: f.icao, call: f.call, date: f.date, time: f.time});
                localStorage.setItem('rare_flights', JSON.stringify(history));
            }
        }

        setInterval(() => {
            if(act) {
                toggleState = !toggleState;
                document.getElementById('icao-label').innerText = toggleState ? "AIRCRAFT ICAO" : "REGISTRATION";
                applyFlap('f-icao', toggleState ? act.icao : act.reg);
                document.getElementById('dist-label').innerText = toggleState ? "DISTANCE" : "ESTIMATED CONTACT";
                applyFlap('f-dist', toggleState ? act.dist + " KM" : "ETA " + act.eta + "M");
                document.getElementById('spd-label').innerText = toggleState ? "GROUND SPEED" : "AIRSPEED INDICATOR";
                applyFlap('b-spd', toggleState ? act.spd + " KMH" : act.kts + " KTS");
            }
        }, 12000);

        function updateTicker() { 
            if (tickerMsg.length > 0) { 
                applyFlap('tk', tickerMsg[tickerIdx], true); 
                tickerIdx = (tickerIdx + 1) % tickerMsg.length; 
            } 
        }
        setInterval(updateTicker, 15000);

        async function update() {
            if(!pos) return;
            try {
                const current_icao = act ? act.icao : '';
                const r = await fetch(`/api/radar?lat=${pos.lat}&lon=${pos.lon}&current_icao=${current_icao}&test=${isTest}&_=${Date.now()}`);
                const d = await r.json();
                if(d.flight) {
                    const f = d.flight;
                    const stub = document.getElementById('stb');
                    const seal = document.getElementById('gold-seal');
                    let trend = "MAINTAINING";
                    if(lastDist !== null) {
                        if(f.dist < lastDist - 0.1) trend = "CLOSING IN";
                        else if(f.dist > lastDist + 0.1) trend = "MOVING AWAY";
                    }
                    lastDist = f.dist;
                    if(f.is_rare) {
                        stub.className = 'stub rare-mode';
                        seal.style.display = 'flex';
                        saveHistory(f);
                    } else {
                        stub.className = 'stub';
                        stub.style.background = f.color;
                        seal.style.display = 'none';
                    }
                    if(!act || act.icao !== f.icao) {
                        playPing();
                        document.getElementById('airl').innerText = f.airline;
                        applyFlap('f-call', f.call); applyFlap('f-route', f.route);
                        document.getElementById('bc').src = `https://bwipjs-api.metafloor.com/?bcid=code128&text=${f.icao}&scale=2`;
                    }
                    document.getElementById('f-line1').innerText = d.date;
                    document.getElementById('f-line2').innerText = d.time;
                    document.getElementById('b-date-line1').innerText = d.date;
                    document.getElementById('b-date-line2').innerText = d.time;
                    for(let i=1; i<=5; i++) {
                        const threshold = 190 - ((i-1) * 40);
                        document.getElementById('d'+i).className = f.dist <= threshold ? 'sq on' : 'sq';
                    }
                    if(!act || act.alt !== f.alt) applyFlap('b-alt', f.alt + " FT");
                    document.getElementById('arr').style.transform = `rotate(${f.hd-45}deg)`;
                    tickerMsg = ["CONTACT ESTABLISHED", trend, d.weather.temp + " " + d.weather.sky];
                    act = f;
                } else if (act) {
                    tickerMsg = ["SIGNAL LOST", "SEARCHING TRAFFIC..."];
                    for(let i=1; i<=5; i++) document.getElementById('d'+i).className = 'sq';
                    document.getElementById('stb').className = 'stub';
                    document.getElementById('stb').style.background = 'var(--brand)';
                } else { tickerMsg = ["SEARCHING TRAFFIC..."]; }
            } catch(e) {}
        }

        function startSearch() {
            if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const v = document.getElementById('in').value.toUpperCase();
            tickerMsg = ["SEARCHING TRAFFIC..."];
            updateTicker();
            if(v === "TEST") { isTest = true; pos = {lat:-22.9, lon:-43.1}; hideUI(); }
            else { fetch("https://nominatim.openstreetmap.org/search?format=json&q="+v).then(r=>r.json()).then(d=>{ if(d[0]) { pos = {lat:parseFloat(d[0].lat), lon:parseFloat(d[0].lon)}; hideUI(); } }); }
        }
        function handleFlip(e) { if(!e.target.closest('#ui') && !e.target.closest('#bc')) document.getElementById('card').classList.toggle('flipped'); }
        function openMap(e) { e.stopPropagation(); if(act) window.open(`https://globe.adsbexchange.com/?icao=${act.icao}`, '_blank'); }
        function hideUI() { document.getElementById('ui').classList.add('hide'); update(); setInterval(update, 20000); }
        navigator.geolocation.getCurrentPosition(p => { pos = {lat:p.coords.latitude, lon:p.coords.longitude}; hideUI(); }, () => {}, { timeout: 6000 });
    </script>
</body>
</html>
''')

if __name__ == '__main__':
    app.run(debug=True)
