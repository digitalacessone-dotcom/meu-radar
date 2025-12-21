# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, render_template_string
import requests
import math
import random
from datetime import datetime, timedelta

app = Flask(__name__)

# Settings V102 - Long Spin & Smart Ticker Fix
RADIUS_KM = 190 
DEFAULT_LAT = -22.9068
DEFAULT_LON = -43.1729

def get_time_local():
    return datetime.utcnow() - timedelta(hours=3)

def get_weather_info(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code"
        resp = requests.get(url, timeout=5).json()
        curr = resp['current']
        code = curr['weather_code']
        mapping = {0: "CLEAR SKY", 1: "FEW CLOUDS", 2: "SCATTERED", 3: "OVERCAST", 45: "FOGGY", 51: "DRIZZLE", 61: "RAIN", 80: "SHOWERS"}
        sky = mapping.get(code, "STABLE")
        vis = "10KM+"
        if code in [45, 48]: vis = "1.5KM"
        elif code in [51, 53, 55, 61]: vis = "5KM"
        elif code in [63, 65, 80]: vis = "3KM"
        return {"temp": f"{int(curr['temperature_2m'])}C", "sky": sky, "vis": vis}
    except:
        return {"temp": "--C", "sky": "METAR ON", "vis": "---"}

def fetch_aircrafts(lat, lon):
    endpoints = [
        f"https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/250",
        f"https://opendata.adsb.fi/api/v2/lat/{lat}/lon/{lon}/dist/250"
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
        weather = get_weather_info(lat, lon)
        
        if test:
            return jsonify({"flight": {"icao": "E4953E", "reg": "PT-MDS", "call": "TEST777", "airline": "LOCAL TEST", "color": "#34a8c9", "dist": 10.5, "alt": 35000, "spd": 850, "hd": 120, "date": now_date, "time": now_time, "route": "GIG-MIA", "eta": 1, "kts": 459, "squawk": "2241", "vrate": -1200, "cat": "LARGE", "mach": 0.78}, "weather": weather, "date": now_date, "time": now_time})
        
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
                        airline, color = "PRIVATE", "#444"
                        if call.startswith(("TAM", "JJ", "LA")): airline, color = "LATAM", "#E6004C"
                        elif call.startswith(("GLO", "G3")): airline, color = "GOL", "#FF6700"
                        elif call.startswith(("AZU", "AD")): airline, color = "AZUL", "#004590"
                        spd_kts = int(s.get('gs', 0))
                        alt = int(s.get('alt_baro', 0) if s.get('alt_baro') != "ground" else 0)
                        proc.append({
                            "icao": s.get('hex', 'UNK').upper(), "reg": s.get('r', 'N/A').upper(), 
                            "call": call, "airline": airline, "color": color, 
                            "dist": round(d, 1), "alt": alt, "spd": int(spd_kts * 1.852), "kts": spd_kts, 
                            "hd": int(s.get('track', 0)), "date": now_date, "time": now_time, 
                            "route": s.get('route', "--- ---"), "eta": round((d / ((spd_kts * 1.852) or 1)) * 60),
                            "squawk": s.get('squawk', '0000'), "vrate": s.get('baro_rate', 0),
                            "cat": "HEAVY" if s.get('category','').startswith('A5') else "MEDIUM", "mach": round(spd_kts / 661.7, 2)
                        })
            if proc: found = sorted(proc, key=lambda x: x['dist'])[0]
        return jsonify({"flight": found, "weather": weather, "date": now_date, "time": now_time})
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
        #ui { width: 280px; display: flex; gap: 6px; margin-bottom: 12px; z-index: 500; transition: opacity 0.8s; }
        #ui.hide { opacity: 0; pointer-events: none; }
        input { flex: 1; padding: 12px; border-radius: 12px; border: none; background: #1a1d21; color: #fff; font-size: 11px; outline: none; }
        button { background: #fff; border: none; padding: 0 15px; border-radius: 12px; font-weight: 900; }
        .scene { width: 300px; height: 460px; position: relative; transform-style: preserve-3d; transition: transform 0.8s; }
        .scene.flipped { transform: rotateY(180deg); }
        .face { position: absolute; width: 100%; height: 100%; backface-visibility: hidden; border-radius: 20px; background: #fff; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 20px 50px rgba(0,0,0,0.5); }
        .face.back { transform: rotateY(180deg); background: #f4f4f4; padding: 15px; }
        .stub { height: 32%; background: var(--brand); color: #fff; padding: 20px; display: flex; flex-direction: column; justify-content: center; transition: background 0.5s; }
        .dots-container { display: flex; gap: 4px; margin-top: 8px; }
        .sq { width: 10px; height: 10px; border: 1.5px solid rgba(255,255,255,0.3); background: rgba(0,0,0,0.2); border-radius: 2px; transition: 0.3s; }
        .sq.on { background: var(--gold); border-color: var(--gold); box-shadow: 0 0 10px var(--gold); }
        .perfor { height: 2px; border-top: 5px dotted #ccc; position: relative; background: #fff; }
        .perfor::before, .perfor::after { content:""; position:absolute; width:30px; height:30px; background:var(--bg); border-radius:50%; top:-15px; }
        .perfor::before { left:-25px; } .perfor::after { right:-25px; }
        .main { flex: 1; padding: 20px; display: flex; flex-direction: column; justify-content: space-between; }
        .flap { font-family: monospace; font-size: 18px; font-weight: 900; color: #000; height: 24px; display: flex; gap: 1px; }
        .char { width: 14px; height: 22px; background: #f0f0f0; border-radius: 3px; display: flex; align-items: center; justify-content: center; }
        .date-visual { color: var(--blue-txt); font-weight: 900; line-height: 0.95; }
        #bc { width: 110px; height: 35px; opacity: 0.15; filter: grayscale(1); cursor: pointer; }
        .ticker { width: 310px; height: 32px; background: #000; border-radius: 6px; margin-top: 15px; display: flex; align-items: center; justify-content: center; color: var(--gold); font-family: monospace; font-size: 11px; letter-spacing: 1px; white-space: pre; }
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
                    <div><span id="icao-label" style="font-size: 7px; font-weight: 900; color: #bbb;">AIRCRAFT ICAO</span><div id="f-icao" class="flap" data-limit="8"></div></div>
                    <div><span id="dist-label" style="font-size: 7px; font-weight: 900; color: #bbb;">DISTANCE</span><div id="f-dist" class="flap" style="color:#666" data-limit="8"></div></div>
                    <div><span style="font-size: 7px; font-weight: 900; color: #bbb;">FLIGHT IDENTIFICATION</span><div id="f-call" class="flap" data-limit="8"></div></div>
                    <div><span style="font-size: 7px; font-weight: 900; color: #bbb;">ROUTE (AT-TO)</span><div id="f-route" class="flap" data-limit="8"></div></div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                    <div id="arr" style="font-size:45px; transition:1.5s;">✈</div>
                    <div class="date-visual"><div id="f-line1">-- --- ----</div><div id="f-line2">--.--</div><img id="bc" src="https://bwipjs-api.metafloor.com/?bcid=code128&text=WAITING" onclick="openMap(event)"></div>
                </div>
            </div>
        </div>
        <div class="face back">
            <div style="height:100%; border:1px dashed #ccc; border-radius:15px; padding:20px; display:flex; flex-direction:column;">
                <div style="display:flex; justify-content:space-between;">
                    <div><span style="font-size: 7px; font-weight: 900; color: #bbb;">ALTITUDE</span><div id="b-alt" class="flap" data-limit="8"></div></div>
                    <div><span id="spd-label" style="font-size: 7px; font-weight: 900; color: #bbb;">GROUND SPEED</span><div id="b-spd" class="flap" data-limit="8"></div></div>
                </div>
                <div style="border: 3px double var(--blue-txt); color: var(--blue-txt); padding: 10px; border-radius: 10px; transform: rotate(-10deg); align-self: center; margin-top: 20px; text-align: center; font-weight: 900;">
                    <div style="font-size:8px;">SECURITY CHECKED</div>
                    <div id="b-date-line1">-- --- ----</div>
                    <div id="b-date-line2" style="font-size:22px;">--.--</div>
                    <div style="font-size:8px; margin-top:5px;">RADAR CONTACT V102</div>
                </div>
            </div>
        </div>
    </div>
    <div class="ticker" id="tk">AWAITING LOCALIZATION...</div>
    <script>
        let pos = null, act = null, isTest = false, weather = null;
        let tickerMsg = [], tickerIdx = 0, lastDist = null;
        let audioCtx = null, fDate = "-- --- ----", fTime = "--.--";
        const chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ.- ";

        function playPing() {
            try {
                if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = audioCtx.createOscillator(); const gain = audioCtx.createGain();
                osc.type = 'sine'; osc.frequency.setValueAtTime(880, audioCtx.currentTime); 
                gain.gain.setValueAtTime(0.05, audioCtx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.5);
                osc.connect(gain); gain.connect(audioCtx.destination);
                osc.start(); osc.stop(audioCtx.currentTime + 0.5);
            } catch(e) {}
        }

        function applyFlap(id, text, isTicker = false) {
            const container = document.getElementById(id);
            if(!container) return;
            const limit = parseInt(container.getAttribute('data-limit') || (isTicker ? 30 : 8));
            const target = text.toUpperCase().padEnd(limit, ' ');
            if (container.children.length === 0) {
                for (let i = 0; i < limit; i++) {
                    const span = document.createElement('span');
                    if (!isTicker) span.className = 'char';
                    span.innerHTML = '&nbsp;';
                    container.appendChild(span);
                }
            }
            [...target].forEach((char, i) => {
                const span = container.children[i];
                if (!span || span.innerText === char || (char === ' ' && span.innerHTML === '&nbsp;')) return;
                
                // MUDANÇA: max aumentado de 8 para 25 para girar por mais tempo
                let count = 0, max = Math.floor(Math.random() * 15) + 15; 
                const interval = setInterval(() => {
                    span.innerText = chars[Math.floor(Math.random() * chars.length)];
                    if (count++ >= max) { 
                        clearInterval(interval); 
                        span.innerHTML = (char === ' ') ? '&nbsp;' : char; 
                    }
                }, 40 + (Math.random() * 30)); // Velocidade mais cadenciada
            });
        }

        function updateTicker() { 
            if (tickerMsg.length > 0) { 
                applyFlap('tk', tickerMsg[tickerIdx], true); 
                tickerIdx = (tickerIdx + 1) % tickerMsg.length; 
            } 
        }
        setInterval(updateTicker, 10000);

        async function update() {
            if(!pos) return;
            try {
                const r = await fetch(`/api/radar?lat=${pos.lat}&lon=${pos.lon}&test=${isTest}&_=${Date.now()}`);
                const d = await r.json();
                weather = d.weather;
                if(d.flight) {
                    const f = d.flight;
                    let trend = "OVERHEAD";
                    if(lastDist !== null) {
                        if(f.dist < lastDist - 0.2) trend = "CLOSING IN";
                        else if(f.dist > lastDist + 0.2) trend = "MOVING AWAY";
                    }
                    lastDist = f.dist;
                    
                    if(!act || act.icao !== f.icao) {
                        fDate = f.date; fTime = f.time; playPing();
                        document.getElementById('stb').style.background = f.color;
                        document.getElementById('arr').style.color = f.color;
                        document.getElementById('airl').innerText = f.airline;
                        applyFlap('f-call', f.call); applyFlap('f-route', f.route);
                        applyFlap('f-icao', f.icao); applyFlap('f-dist', f.dist + " KM");
                        document.getElementById('bc').src = `https://bwipjs-api.metafloor.com/?bcid=code128&text=${f.icao}&scale=2`;
                        
                        // LIMPEZA IMEDIATA DO TICKER AO LOCALIZAR
                        tickerIdx = 0;
                    }
                    
                    document.getElementById('f-line1').innerText = fDate; document.getElementById('f-line2').innerText = fTime;
                    document.getElementById('b-date-line1').innerText = fDate; document.getElementById('b-date-line2').innerText = fTime;
                    
                    for(let i=1; i<=5; i++) {
                        const threshold = (6 - i) * 38; 
                        document.getElementById('d'+i).className = f.dist <= threshold ? 'sq on' : 'sq';
                    }

                    if(!act || act.alt !== f.alt) applyFlap('b-alt', f.alt + " FT");
                    if(!act || act.spd !== f.spd) applyFlap('b-spd', f.spd + " KMH");
                    document.getElementById('arr').style.transform = `rotate(${f.hd-45}deg)`;
                    act = f;

                    tickerMsg = [
                        `STATUS: ${trend}`,
                        `CAT: ${f.cat} • MACH: ${f.mach}`,
                        `V.RATE: ${f.vrate} FPM • SQK: ${f.squawk}`,
                        `TEMP: ${weather.temp} • SKY: ${weather.sky}`,
                        `VISIBILITY: ${weather.vis}`
                    ];
                } else if (act) {
                    document.getElementById('stb').style.background = "#444"; 
                    for(let i=1; i<=5; i++) document.getElementById('d'+i).className = 'sq';
                    tickerMsg = [`SIGNAL LOST: ${act.call}`, `STATUS: GHOST MODE`, `TEMP: ${weather.temp} • ${weather.sky}` ];
                } else {
                    tickerMsg = [`SEARCHING TRAFFIC...`, `TEMP: ${weather.temp} • ${weather.sky}`, `SYSTEM READY V102` ];
                    for(let i=1; i<=5; i++) document.getElementById('d'+i).className = 'sq';
                }
            } catch(e) {}
        }

        function startSearch() {
            if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const v = document.getElementById('in').value.toUpperCase();
            if(v === "TEST") { isTest = true; pos = {lat:-22.9, lon:-43.1}; hideUI(); }
            else { fetch("https://nominatim.openstreetmap.org/search?format=json&q="+v).then(r=>r.json()).then(d=>{ if(d[0]) { pos = {lat:parseFloat(d[0].lat), lon:parseFloat(d[0].lon)}; hideUI(); } }); }
        }
        function handleFlip(e) { if(!e.target.closest('#ui') && !e.target.closest('#bc')) document.getElementById('card').classList.toggle('flipped'); }
        function openMap(e) { e.stopPropagation(); if(act) window.open(`https://globe.adsbexchange.com/?icao=${act.icao}`, '_blank'); }
        function hideUI() { document.getElementById('ui').classList.add('hide'); setTimeout(() => { update(); setInterval(update, 10000); }, 800); }
        navigator.geolocation.getCurrentPosition(p => { pos = {lat:p.coords.latitude, lon:p.coords.longitude}; hideUI(); }, () => { applyFlap('tk', 'ENTER LOCATION ABOVE', true); }, { timeout: 6000 });
    </script>
</body>
</html>
