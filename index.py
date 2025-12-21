# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, render_template_string
import requests
import math
import random
from datetime import datetime, timedelta

app = Flask(__name__)

# Configurações V100.0 - Ultimate Collector Edition
RADIUS_KM = 190 
DEFAULT_LAT = -22.9068
DEFAULT_LON = -43.1729

# Base de Dados Ampliada
RARE_MODELS = ["C5", "C17", "B1", "B2", "B52", "F22", "F35", "F16", "F15", "F18", "A10", "U2", "Q9", "E6", "P8", "K35R", "K46", "H60", "H47", "H64", "V22"]
RARE_CALLSIGNS = ["RCH", "PAT", "CNV", "GOTO", "NVY", "DOD", "CGX", "SDR", "RRR", "FAF", "GAF", "ASY", "CFC"]

def get_time_local():
    return datetime.utcnow() - timedelta(hours=3)

def get_weather_desc(code):
    mapping = {0: "CLEAR SKY", 1: "FEW CLOUDS", 2: "SCATTERED", 3: "OVERCAST", 45: "FOG", 51: "LIGHT DRIZZLE", 61: "RAIN", 80: "SHOWERS"}
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
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}
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
            return jsonify({"flight": {"icao": "AE0802", "reg": "06-6161", "call": "RCH144", "airline": "US AIR FORCE", "color": "#003087", "dist": 10.5, "alt": 35000, "spd": 850, "hd": 120, "date": now_date, "time": now_time, "route": "DOV-RMS", "eta": 1, "kts": 459, "vrate": 1500, "rare": True, "type": "C17"}, "weather": w, "date": now_date, "time": now_time})
        
        data = fetch_aircrafts(lat, lon)
        found = None
        if data:
            proc = []
            for s in data:
                slat, slon = s.get('lat'), s.get('lon')
                if slat and slon:
                    d = 6371 * 2 * math.asin(math.sqrt(math.sin(math.radians(slat-lat)/2)**2 + math.cos(math.radians(lat)) * math.cos(math.radians(slat)) * math.sin(math.radians(slon-lon)/2)**2))
                    if d <= RADIUS_KM:
                        call = (s.get('flight') or s.get('call') or 'N/A').strip()
                        tipo = s.get('t', '').upper()
                        is_rare = tipo in RARE_MODELS or any(call.startswith(p) for p in RARE_CALLSIGNS)
                        
                        airline, color = "PRIVATE", "#444"
                        if is_rare: airline, color = "MILITARY / SPECIAL", "#bf953f"
                        elif call.startswith(("TAM", "JJ", "LA")): airline, color = "LATAM", "#E6004C"
                        elif call.startswith(("GLO", "G3")): airline, color = "GOL", "#FF6700"
                        elif call.startswith(("AZU", "AD")): airline, color = "AZUL", "#004590"
                        
                        spd_kts = int(s.get('gs', 0))
                        spd_kmh = int(spd_kts * 1.852)
                        eta = round((d / (spd_kmh or 1)) * 60)
                        proc.append({"icao": s.get('hex', 'UNK').upper(), "reg": s.get('r', 'N/A').upper(), "call": call, "airline": airline, "color": color, "dist": round(d, 1), "alt": int(s.get('alt_baro', 0) if s.get('alt_baro') != "ground" else 0), "spd": spd_kmh, "kts": spd_kts, "hd": int(s.get('track', 0)), "date": now_date, "time": now_time, "route": s.get('route', "--- ---"), "eta": eta, "vrate": int(s.get('baro_rate', 0)), "rare": is_rare, "type": tipo or "UNK"})
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
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <style>
        :root { --gold: #FFD700; --bg: #0b0e11; --brand: #444; --blue-txt: #34a8c9; }
        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body { background: var(--bg); font-family: -apple-system, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100dvh; margin: 0; perspective: 1500px; overflow: hidden; }
        
        /* Rare Golden Paper Effect */
        .rare-card .face {
            background: linear-gradient(135deg, #bf953f 0%, #fcf6ba 45%, #b38728 50%, #fbf5b7 55%, #aa771c 100%) !important;
            box-shadow: 0 0 40px rgba(191, 149, 63, 0.4), 0 20px 50px rgba(0,0,0,0.6);
            border: 1px solid rgba(255,255,255,0.3);
        }
        .rare-card .face::after {
            content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            opacity: 0.25; pointer-events: none; mix-blend-mode: multiply;
            background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 250 250' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
        }
        .rare-card .perfor { background: transparent !important; border-top: 5px dotted rgba(0,0,0,0.2) !important; }
        .rare-card .char { background: rgba(255,255,255,0.3) !important; color: #332b00 !important; }

        #ui { width: 280px; display: flex; gap: 6px; margin-bottom: 12px; z-index: 500; transition: 0.5s; }
        #ui.hide { opacity: 0; pointer-events: none; }
        input { flex: 1; padding: 12px; border-radius: 12px; border: none; background: #1a1d21; color: #fff; font-size: 11px; outline: none; }
        button { background: #fff; border: none; padding: 0 15px; border-radius: 12px; font-weight: 900; }
        
        .scene { width: 300px; height: 460px; position: relative; transform-style: preserve-3d; transition: transform 0.8s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
        .scene.flipped { transform: rotateY(180deg); }
        
        .face { position: absolute; width: 100%; height: 100%; backface-visibility: hidden; border-radius: 20px; background: #fff; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 20px 50px rgba(0,0,0,0.5); }
        .face.back { transform: rotateY(180deg); background: #f4f4f4; padding: 15px; }
        
        .stub { height: 30%; background: var(--brand); color: #fff; padding: 20px; display: flex; flex-direction: column; justify-content: center; transition: 0.5s; z-index: 2; }
        .perfor { height: 2px; border-top: 5px dotted #ccc; position: relative; background: #fff; z-index: 5; }
        .perfor::before, .perfor::after { content:""; position:absolute; width:30px; height:30px; background:var(--bg); border-radius:50%; top:-15px; }
        .perfor::before { left:-25px; } .perfor::after { right:-25px; }
        
        .main { flex: 1; padding: 20px; display: flex; flex-direction: column; justify-content: space-between; z-index: 2; }
        .flap { font-family: monospace; font-size: 18px; font-weight: 900; color: #000; height: 24px; display: flex; gap: 1px; }
        .char { width: 14px; height: 22px; background: #f0f0f0; border-radius: 3px; display: flex; align-items: center; justify-content: center; }
        
        /* Colecionáveis Grid */
        .collection-title { font-size: 8px; font-weight: 900; color: #aaa; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px; }
        .collection-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; margin-bottom: 15px; background: rgba(0,0,0,0.03); padding: 8px; border-radius: 10px; }
        .badge { font-size: 8px; font-weight: 900; padding: 4px 2px; background: #e0e0e0; color: #bbb; border-radius: 4px; text-align: center; border: 1px solid #ddd; transition: 0.5s; }
        .badge.owned { background: #bf953f; color: #fff; border-color: #ffd700; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        
        .security-stamp { border: 3px double var(--blue-txt); color: var(--blue-txt); padding: 8px; border-radius: 10px; transform: rotate(-8deg); align-self: center; text-align: center; font-weight: 900; margin-top: 5px; }
        .ticker { width: 310px; height: 32px; background: #000; border-radius: 6px; margin-top: 15px; display: flex; align-items: center; justify-content: center; color: var(--gold); font-family: monospace; font-size: 11px; white-space: pre; }
        .sq { width: 10px; height: 10px; border: 1.5px solid rgba(255,255,255,0.3); background: rgba(0,0,0,0.2); border-radius: 2px; }
        .sq.on { background: var(--gold); border-color: var(--gold); box-shadow: 0 0 10px var(--gold); }
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
                <div style="font-size:10px; font-weight:900; margin-top:5px;" id="airl">AWAITING SIGNAL...</div>
                <div style="font-size:60px; font-weight:900; letter-spacing:-4px; margin:2px 0;">19A</div>
                <div style="display:flex; gap:4px;" id="dots">
                    <div id="d1" class="sq"></div><div id="d2" class="sq"></div><div id="d3" class="sq"></div><div id="d4" class="sq"></div><div id="d5" class="sq"></div>
                </div>
            </div>
            <div class="perfor"></div>
            <div class="main">
                <div style="color: #333; font-weight: 900; font-size: 13px; border: 1.5px solid #333; padding: 3px 10px; border-radius: 4px; align-self: flex-start;">BOARDING PASS</div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:10px;">
                    <div><span id="icao-label" style="font-size: 7px; font-weight: 900; color: #bbb;">AIRCRAFT ICAO</span><div id="f-icao" class="flap"></div></div>
                    <div><span id="dist-label" style="font-size: 7px; font-weight: 900; color: #bbb;">DISTANCE</span><div id="f-dist" class="flap" style="color:#666"></div></div>
                    <div><span style="font-size: 7px; font-weight: 900; color: #bbb;">FLIGHT IDENT</span><div id="f-call" class="flap"></div></div>
                    <div><span style="font-size: 7px; font-weight: 900; color: #bbb;">ROUTE (ESTIMATED)</span><div id="f-route" class="flap"></div></div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                    <div id="arr" style="font-size:45px; transition:1.5s;">✈</div>
                    <div style="text-align:right;">
                        <div id="f-date" style="font-weight:900; color:var(--blue-txt); font-size:12px;">-- --- ----</div>
                        <div id="f-time" style="font-weight:900; color:var(--blue-txt); font-size:18px;">--.--</div>
                        <img id="bc" src="https://bwipjs-api.metafloor.com/?bcid=code128&text=WAITING" style="width:100px; opacity:0.2; cursor:pointer;" onclick="openMap(event)">
                    </div>
                </div>
            </div>
        </div>

        <div class="face back">
            <div class="collection-title">Rare Finds History</div>
            <div class="collection-grid" id="col-grid"></div>
            
            <div style="border-top: 1px dashed #ccc; padding-top: 10px; display: flex; justify-content: space-between;">
                <div><span style="font-size: 7px; font-weight: 900; color: #bbb;">ALTITUDE</span><div id="b-alt" class="flap"></div></div>
                <div><span id="spd-label" style="font-size: 7px; font-weight: 900; color: #bbb;">GROUND SPEED</span><div id="b-spd" class="flap"></div></div>
            </div>

            <div class="security-stamp">
                <div style="font-size:7px;">SCAN VERIFIED</div>
                <div id="b-date">-- --- ----</div>
                <div id="b-time" style="font-size:20px;">--.--</div>
                <div style="font-size:7px; margin-top:3px;">RADAR CONTACT V100.0</div>
            </div>
        </div>
    </div>

    <div class="ticker" id="tk">INITIALIZING RADAR SYSTEM...</div>

    <script>
        let pos = null, act = null, prevDist = null, isTest = false;
        let tickerMsg = [], tickerIdx = 0;
        const RARE_MODELS = ["C17", "F22", "F35", "B2", "C5", "A10", "F16", "F15", "F18", "B52", "U2", "P8"];
        const chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ.- ";

        function handleFlip(e) { if(!e.target.closest('#ui') && !e.target.closest('#bc')) document.getElementById('card').classList.toggle('flipped'); }
        function openMap(e) { e.stopPropagation(); if(act) window.open(`https://globe.adsbexchange.com/?icao=${act.icao}`, '_blank'); }

        function applyFlap(id, text, isTicker = false) {
            const container = document.getElementById(id);
            if(!container) return;
            const target = text.toUpperCase().padEnd(isTicker ? 32 : 8, ' ');
            container.innerHTML = '';
            [...target].forEach(char => {
                const span = document.createElement('span');
                if(!isTicker) span.className = 'char';
                span.innerHTML = '&nbsp;';
                container.appendChild(span);
                let c = 0; 
                const it = setInterval(() => {
                    span.innerText = chars[Math.floor(Math.random()*chars.length)];
                    if(c++ > 15) { clearInterval(it); span.innerText = char === ' ' ? '\u00A0' : char; }
                }, 40);
            });
        }

        function updateCollectionUI(newType = null) {
            let saved = JSON.parse(localStorage.getItem('planeCollection') || '[]');
            if(newType && !saved.includes(newType) && RARE_MODELS.includes(newType)) {
                saved.push(newType);
                localStorage.setItem('planeCollection', JSON.stringify(saved));
            }
            const grid = document.getElementById('col-grid');
            grid.innerHTML = '';
            RARE_MODELS.forEach(m => {
                const div = document.createElement('div');
                div.className = 'badge' + (saved.includes(m) ? ' owned' : '');
                div.innerText = saved.includes(m) ? m : '???';
                grid.appendChild(div);
            });
        }

        async function update() {
            if(!pos) return;
            try {
                const r = await fetch(`/api/radar?lat=${pos.lat}&lon=${pos.lon}&test=${isTest}&_=${Date.now()}`);
                const d = await r.json();
                if(d.flight) {
                    const f = d.flight;
                    const card = document.getElementById('card');
                    
                    if(f.rare) { 
                        card.classList.add('rare-card'); 
                        updateCollectionUI(f.type);
                    } else { 
                        card.classList.remove('rare-card'); 
                    }

                    document.getElementById('stb').style.background = f.color;
                    document.getElementById('airl').innerText = f.airline;
                    
                    if(!act || act.icao !== f.icao) {
                        applyFlap('f-icao', f.icao); applyFlap('f-call', f.call);
                        applyFlap('f-route', f.route);
                        document.getElementById('bc').src = `https://bwipjs-api.metafloor.com/?bcid=code128&text=${f.icao}&scale=2`;
                    }

                    applyFlap('f-dist', f.dist + " KM");
                    applyFlap('b-alt', f.alt + " FT");
                    applyFlap('b-spd', f.spd + " KMH");
                    
                    document.getElementById('f-date').innerText = f.date;
                    document.getElementById('f-time').innerText = f.time;
                    document.getElementById('b-date').innerText = f.date;
                    document.getElementById('b-time').innerText = f.time;
                    document.getElementById('arr').style.transform = `rotate(${f.hd-45}deg)`;

                    for(let i=1; i<=5; i++) {
                        const threshold = 190 - ((i-1) * 40);
                        document.getElementById('d'+i).className = f.dist <= threshold ? 'sq on' : 'sq';
                    }

                    let trend = prevDist && f.dist < prevDist ? "CLOSING IN" : "STABLE";
                    tickerMsg = [f.rare ? "RARE CONTACT DETECTED" : "RADAR ACTIVE", `V.RATE: ${f.vrate} FPM`, trend, `SKY: ${d.weather.sky}`];
                    prevDist = f.dist; act = f;
                } else {
                    tickerMsg = ["SCANNING SKY...", `TEMP: ${d.weather.temp}`, "NO CONTACT"];
                }
            } catch(e) { console.error(e); }
        }

        function startSearch() {
            const v = document.getElementById('in').value.toUpperCase();
            if(v === "TEST") { isTest = true; pos = {lat:0, lon:0}; hideUI(); }
            else { 
                fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${v}`)
                .then(r=>r.json()).then(d=>{ if(d[0]) { pos={lat:parseFloat(d[0].lat), lon:parseFloat(d[0].lon)}; hideUI(); }});
            }
        }

        function hideUI() { document.getElementById('ui').classList.add('hide'); update(); setInterval(update, 15000); }
        
        setInterval(() => { if(tickerMsg.length) { applyFlap('tk', tickerMsg[tickerIdx], true); tickerIdx = (tickerIdx+1)%tickerMsg.length; }}, 6000);
        updateCollectionUI();
    </script>
</body>
</html>
''')

if __name__ == '__main__':
    app.run(debug=True)
