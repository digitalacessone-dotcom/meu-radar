# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, render_template_string
import requests
import math
import random
from datetime import datetime, timedelta

app = Flask(__name__)

# Configurações de Escaneamento
RADIUS_KM = 190 
DEFAULT_LAT = -22.9068
DEFAULT_LON = -43.1729

def get_time_local():
    return datetime.utcnow() - timedelta(hours=3)

def is_rare_aircraft(icao, call):
    # Lista expandida de prefixos militares e raros
    rare_prefixes = ('MIL', 'NAVY', 'AF1', 'FORCA', 'RCH', 'VADER', 'SR71', 'B2', 'F22', 'F35', 'U2', 'K35R', 'R135', 'ROMA', 'GHOST')
    return call.upper().startswith(rare_prefixes) or icao.upper() in ["E4953E", "AE01CE", "ADFEB7"]

def get_weather_desc(code):
    mapping = {0: "CLEAR SKY", 1: "FEW CLOUDS", 2: "SCATTERED", 3: "OVERCAST", 45: "FOG", 48: "DEPOSITING RIME FOG", 51: "LIGHT DRIZZLE", 61: "RAIN", 80: "SHOWERS"}
    return mapping.get(code, "CONDITIONS OK")

def get_weather(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code,visibility"
        resp = requests.get(url, timeout=5).json()
        curr = resp['current']
        vis_km = int(curr.get('visibility', 10000) / 1000)
        return {"temp": f"{int(curr['temperature_2m'])}C", "sky": get_weather_desc(curr['weather_code']), "vis": f"{vis_km}KM"}
    except:
        return {"temp": "--C", "sky": "METAR ON", "vis": "--KM"}

def fetch_aircrafts(lat, lon):
    endpoints = [
        f"https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/200",
        f"https://opendata.adsb.fi/api/v2/lat/{lat}/lon/{lon}/dist/200"
    ]
    headers = {'User-Agent': 'Mozilla/5.0'}
    random.shuffle(endpoints)
    for url in endpoints:
        try:
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200: return r.json().get('aircraft', [])
        except: continue
    return []

@app.route('/api/radar')
def radar():
    try:
        lat = float(request.args.get('lat', DEFAULT_LAT))
        lon = float(request.args.get('lon', DEFAULT_LON))
        test = request.args.get('test', 'false').lower() == 'true'
        local_now = get_time_local()
        now_date = local_now.strftime("%d %b %Y").upper()
        now_time = local_now.strftime("%H.%M")
        w = get_weather(lat, lon)
        
        if test:
            # Mistura Blackbird com Comercial no Teste
            if random.random() > 0.5:
                f = {"icao": "SR71", "reg": "61-7972", "call": "BLACKBIRD", "airline": "STRATOSPHERE", "color": "#000", "dist": 42.1, "alt": 85000, "spd": 3530, "hd": 315, "date": now_date, "time": now_time, "route": "EDW-GIG", "rare": True, "vrate": 4500, "kts": 1900, "eta": 1}
            else:
                f = {"icao": "E4953E", "reg": "PT-MDS", "call": "TEST777", "airline": "LOCAL TEST", "color": "#34a8c9", "dist": 10.5, "alt": 35000, "spd": 850, "hd": 120, "date": now_date, "time": now_time, "route": "GIG-MIA", "rare": False, "vrate": -1500, "kts": 459, "eta": 2}
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
                        icao = s.get('hex', 'UNK').upper()
                        call = (s.get('flight') or s.get('call') or 'N/A').strip().upper()
                        rare = is_rare_aircraft(icao, call)
                        
                        airline, color = ("MILITARY", "#000") if rare else ("PRIVATE", "#444")
                        if not rare:
                            if call.startswith(("TAM", "JJ", "LA")): airline, color = "LATAM", "#E6004C"
                            elif call.startswith(("GLO", "G3")): airline, color = "GOL", "#FF6700"
                            elif call.startswith(("AZU", "AD")): airline, color = "AZUL", "#004590"
                        
                        spd_kts = int(s.get('gs', 0))
                        spd_kmh = int(spd_kts * 1.852)
                        proc.append({
                            "icao": icao, "reg": s.get('r', 'N/A').upper(), "call": call, 
                            "airline": airline, "color": color, "dist": round(d, 1), 
                            "alt": int(s.get('alt_baro', 0) if s.get('alt_baro') != "ground" else 0), 
                            "spd": spd_kmh, "kts": spd_kts, "hd": int(s.get('track', 0)), 
                            "date": now_date, "time": now_time, "route": s.get('route', "--- ---"), 
                            "eta": round((d / (spd_kmh or 1)) * 60), "vrate": int(s.get('baro_rate', 0)), "rare": rare
                        })
            if proc: found = sorted(proc, key=lambda x: x['dist'])[0]
        return jsonify({"flight": found, "weather": w, "date": now_date, "time": now_time})
    except: return jsonify({"flight": None})

@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
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
        
        /* Stub e Lógica de Aeronave Rara */
        .stub { height: 32%; background: var(--brand); color: #fff; padding: 20px; display: flex; flex-direction: column; justify-content: center; transition: background 0.5s; position: relative; }
        .rare-mode .stub { background: #000 !important; color: var(--gold) !important; }
        
        .dots-container { display: flex; gap: 4px; margin-top: 8px; }
        .sq { width: 10px; height: 10px; border: 1.5px solid rgba(255,255,255,0.3); background: rgba(0,0,0,0.2); border-radius: 2px; }
        .sq.on { background: #fff; }
        .rare-mode .sq.on { background: var(--gold); border-color: var(--gold); box-shadow: 0 0 10px var(--gold); }
        
        .perfor { height: 2px; border-top: 5px dotted #ccc; position: relative; background: #fff; }
        .perfor::before, .perfor::after { content:""; position:absolute; width:30px; height:30px; background:var(--bg); border-radius:50%; top:-15px; }
        .perfor::before { left:-25px; } .perfor::after { right:-25px; }
        
        .main { flex: 1; padding: 20px; display: flex; flex-direction: column; justify-content: space-between; }
        .flap { font-family: monospace; font-size: 18px; font-weight: 900; color: #000; height: 24px; display: flex; gap: 1px; }
        .char { width: 14px; height: 22px; background: #f0f0f0; border-radius: 3px; display: flex; align-items: center; justify-content: center; }
        
        .date-visual { color: var(--blue-txt); font-weight: 900; line-height: 0.95; text-align: right; }
        #bc { width: 110px; height: 35px; opacity: 0.15; filter: grayscale(1); cursor: pointer; }
        .ticker { width: 310px; height: 32px; background: #000; border-radius: 6px; margin-top: 15px; display: flex; align-items: center; justify-content: center; color: var(--gold); font-family: monospace; font-size: 11px; letter-spacing: 2px; white-space: pre; }
        
        /* Selo Elegante e Pequeno */
        .gold-seal { 
            position: absolute; bottom: 20px; right: 20px; 
            width: 48px; height: 48px; border-radius: 50%;
            background: radial-gradient(circle, #fff3a0, #d4af37);
            border: 1px solid #b8860b; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: none; align-items: center; justify-content: center;
            font-size: 7px; font-weight: 900; color: #5e4a0a; text-align: center; line-height: 1;
        }
        .rare-mode .gold-seal { display: flex; }

        @media (orientation: landscape) { .scene { width: 550px; height: 260px; } .face { flex-direction: row !important; } .stub { width: 30% !important; height: 100% !important; } .perfor { width: 2px !important; height: 100% !important; border-left: 5px dotted #ccc !important; border-top: none !important; } .main { width: 70% !important; } .ticker { width: 550px; } }
    </style>
</head>
<body onclick="handleFlip(event)">
    <div id="ui">
        <input type="text" id="in" placeholder="ENTER LOCATION">
        <button onclick="startSearch()">SCAN</button>
    </div>
    <div class="scene" id="card">
        <div class="face front">
            <div class="stub" id="stb">
                <div style="font-size:7px; font-weight:900; opacity:0.7;">RADAR SCANNING</div>
                <div style="font-size:10px; font-weight:900; margin-top:5px;" id="airl">SEARCHING TRAFFIC...</div>
                <div style="font-size:65px; font-weight:900; letter-spacing:-4px; margin:2px 0;">19A</div>
                <div class="dots-container" id="dots">
                    <div id="d1" class="sq"></div><div id="d2" class="sq"></div><div id="d3" class="sq"></div><div id="d4" class="sq"></div><div id="d5" class="sq"></div>
                </div>
            </div>
            <div class="perfor"></div>
            <div class="main">
                <div style="color: #333; font-weight: 900; font-size: 13px; border: 1.5px solid #333; padding: 3px 10px; border-radius: 4px; align-self: flex-start;">BOARDING PASS</div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:10px;">
                    <div><span id="lb-1" style="font-size: 7px; font-weight: 900; color: #bbb;">AIRCRAFT ICAO</span><div id="f-icao" class="flap"></div></div>
                    <div><span id="lb-2" style="font-size: 7px; font-weight: 900; color: #bbb;">DISTANCE</span><div id="f-dist" class="flap"></div></div>
                    <div><span style="font-size: 7px; font-weight: 900; color: #bbb;">FLIGHT IDENTIFICATION</span><div id="f-call" class="flap"></div></div>
                    <div><span style="font-size: 7px; font-weight: 900; color: #bbb;">ROUTE (AT-TO)</span><div id="f-route" class="flap"></div></div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                    <div id="arr" style="font-size:45px; transition:1.5s;">✈</div>
                    <div class="date-visual">
                        <div id="f-line1">-- --- ----</div>
                        <div id="f-line2" style="font-size:24px;">--.--</div>
                        <img id="bc" src="https://bwipjs-api.metafloor.com/?bcid=code128&text=WAITING" onclick="openMap(event)">
                    </div>
                </div>
            </div>
        </div>
        <div class="face back">
            <div style="height:100%; border:1px dashed #ccc; border-radius:15px; padding:20px; display:flex; flex-direction:column; position:relative;">
                <div style="display:flex; justify-content:space-between;">
                    <div><span style="font-size: 7px; font-weight: 900; color: #bbb;">ALTITUDE</span><div id="b-alt" class="flap"></div></div>
                    <div><span id="lb-3" style="font-size: 7px; font-weight: 900; color: #bbb;">GROUND SPEED</span><div id="b-spd" class="flap"></div></div>
                </div>
                <div class="gold-seal">AUTHENTIC<br>RADAR<br>CONTACT</div>
                
                <div style="border: 3px double var(--blue-txt); color: var(--blue-txt); padding: 10px; border-radius: 10px; transform: rotate(-10deg); align-self: center; margin-top: 25px; text-align: center; font-weight: 900;">
                    <div style="font-size:8px;">SECURITY CHECKED</div>
                    <div id="b-date-line1">-- --- ----</div>
                    <div id="b-date-line2" style="font-size:22px;">--.--</div>
                    <div style="font-size:8px; margin-top:5px;">RADAR CONTACT V109.0</div>
                </div>
            </div>
        </div>
    </div>
    <div class="ticker" id="tk">AWAITING LOCALIZATION...</div>

    <script>
        let pos = null, act = null, isTest = false, prevDist = null;
        let tickerMsg = [], tickerIdx = 0, toggleState = true;
        let audioCtx = null;
        const chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ.- ";

        function playPing() {
            try {
                if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const o = audioCtx.createOscillator(); const g = audioCtx.createGain();
                o.type = 'sine'; o.frequency.setValueAtTime(880, audioCtx.currentTime);
                g.gain.setValueAtTime(0.1, audioCtx.currentTime);
                g.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.5);
                o.connect(g); g.connect(audioCtx.destination); o.start(); o.stop(audioCtx.currentTime + 0.5);
            } catch(e) {}
        }

        function applyFlap(id, text, isTicker = false) {
            const container = document.getElementById(id); if(!container) return;
            const target = text.toUpperCase().padEnd(isTicker ? 32 : 8, ' ');
            container.innerHTML = '';
            [...target].forEach(char => {
                const span = document.createElement('span'); if(!isTicker) span.className = 'char';
                span.innerHTML = '&nbsp;'; container.appendChild(span);
                let count = 0, max = 15;
                const interval = setInterval(() => {
                    span.innerText = chars[Math.floor(Math.random() * chars.length)];
                    if (count++ >= max) { clearInterval(interval); span.innerHTML = char === ' ' ? '&nbsp;' : char; }
                }, 35);
            });
        }

        // Toggler de Informações (ICAO vs REG, DIST vs ETA)
        setInterval(() => {
            if(act) {
                toggleState = !toggleState;
                document.getElementById('lb-1').innerText = toggleState ? "AIRCRAFT ICAO" : "REGISTRATION";
                applyFlap('f-icao', toggleState ? act.icao : act.reg);
                document.getElementById('lb-2').innerText = toggleState ? "DISTANCE" : "ESTIMATED CONTACT";
                applyFlap('f-dist', toggleState ? act.dist + " KM" : "ETA " + act.eta + "M");
                document.getElementById('lb-3').innerText = toggleState ? "GROUND SPEED" : "AIRSPEED KTS";
                applyFlap('b-spd', toggleState ? act.spd + " KMH" : act.kts + " KTS");
            }
        }, 15000);

        async function update() {
            if(!pos) return;
            try {
                const r = await fetch(`/api/radar?lat=${pos.lat}&lon=${pos.lon}&test=${isTest}&_=${Date.now()}`);
                const d = await r.json();
                
                if(d.flight) {
                    const f = d.flight;
                    const card = document.getElementById('card');
                    
                    // Lógica de Lado Esquerdo (Rare)
                    if(f.rare) card.classList.add('rare-mode'); else card.classList.remove('rare-mode');
                    document.getElementById('stb').style.background = f.color;

                    // Mudança de Aeronave
                    if(!act || act.icao !== f.icao) {
                        playPing();
                        document.getElementById('airl').innerText = f.airline;
                        applyFlap('f-call', f.call); applyFlap('f-route', f.route);
                        applyFlap('b-alt', f.alt + " FT");
                        document.getElementById('bc').src = `https://bwipjs-api.metafloor.com/?bcid=code128&text=${f.icao}&scale=2`;
                        
                        // Grava no histórico se for real e raro
                        if(!isTest && f.rare) {
                            let history = JSON.parse(localStorage.getItem('rare_collection') || '[]');
                            if(!history.includes(f.icao)) { history.push(f.icao); localStorage.setItem('rare_collection', JSON.stringify(history)); }
                        }
                    }

                    // Atualiza Data/Hora (IDs Estáveis)
                    document.getElementById('f-line1').innerText = f.date;
                    document.getElementById('f-line2').innerText = f.time;
                    document.getElementById('b-date-line1').innerText = f.date;
                    document.getElementById('b-date-line2').innerText = f.time;

                    // Dots de Distância
                    for(let i=1; i<=5; i++) {
                        const threshold = 190 - ((i-1) * 40);
                        document.getElementById('d'+i).className = f.dist <= threshold ? 'sq on' : 'sq';
                    }

                    // Ticker Messages
                    let prox = "MAINTAINING";
                    if(prevDist && f.dist < prevDist - 0.1) prox = "CLOSING IN";
                    else if(prevDist && f.dist > prevDist + 0.1) prox = "MOVING AWAY";
                    prevDist = f.dist;

                    tickerMsg = [`V.RATE: ${f.vrate} FPM`, prox, `TEMP: ${d.weather.temp}`, `VIS: ${d.weather.vis}`, d.weather.sky];
                    document.getElementById('arr').style.transform = `rotate(${f.hd-45}deg)`;
                    act = f;
                } else {
                    tickerMsg = ["SEARCHING TRAFFIC...", `TEMP: ${d.weather.temp}`, d.weather.sky];
                }
            } catch(e) { console.log(e); }
        }

        function updateTicker() { if (tickerMsg.length > 0) { applyFlap('tk', tickerMsg[tickerIdx], true); tickerIdx = (tickerIdx + 1) % tickerMsg.length; } }
        setInterval(updateTicker, 8000);

        function startSearch() {
            const v = document.getElementById('in').value.toUpperCase();
            if(v === "TEST") { isTest = true; pos = {lat:-22.9, lon:-43.1}; hideUI(); }
            else { fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${v}`).then(r=>r.json()).then(d=>{ if(d[0]) { pos = {lat:parseFloat(d[0].lat), lon:parseFloat(d[0].lon)}; hideUI(); } }); }
        }
        
        function handleFlip(e) { if(!e.target.closest('#ui') && !e.target.closest('#bc')) document.getElementById('card').classList.toggle('flipped'); }
        function openMap(e) { e.stopPropagation(); if(act) window.open(`https://globe.adsbexchange.com/?icao=${act.icao}`, '_blank'); }
        function hideUI() { document.getElementById('ui').classList.add('hide'); setTimeout(() => { update(); setInterval(update, 15000); }, 800); }
        
        navigator.geolocation.getCurrentPosition(p => { pos = {lat:p.coords.latitude, lon:p.coords.longitude}; hideUI(); }, () => { applyFlap('tk', 'ENTER LOCATION ABOVE', true); }, { timeout: 6000 });
    </script>
</body>
</html>
''')

if __name__ == '__main__':
    app.run(debug=True)
