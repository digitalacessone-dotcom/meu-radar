# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, render_template_string
import requests
import math
import random
from datetime import datetime, timedelta

app = Flask(__name__)

# Configurações V101 - Foco em Acúmulo de Funcionalidades
RADIUS_KM = 250 
DEFAULT_LAT = -22.9068
DEFAULT_LON = -43.1729

def get_time_local():
    return datetime.utcnow() - timedelta(hours=3)

def get_weather_full(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,visibility,weather_code"
        r = requests.get(url, timeout=3).json()["current"]
        codes = {0: "CLEAR SKY", 1: "MAINLY CLEAR", 2: "PARTLY CLOUDY", 3: "OVERCAST", 45: "FOGGY", 61: "RAIN", 80: "SHOWERS"}
        return {
            "temp": f"{int(r['temperature_2m'])}C",
            "vis": f"{int(r['visibility']/1000)}KM",
            "sky": codes.get(r['weather_code'], "CONDITIONS OK")
        }
    except: return {"temp": "--C", "vis": "--KM", "sky": "METAR OK"}

def fetch_aircrafts(lat, lon):
    endpoints = [
        f"https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/250",
        f"https://opendata.adsb.fi/api/v2/lat/{lat}/lon/{lon}/dist/250"
    ]
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    random.shuffle(endpoints)
    for url in endpoints:
        try:
            r = requests.get(url, headers=headers, timeout=4)
            if r.status_code == 200: 
                data = r.json().get('aircraft', [])
                return data if isinstance(data, list) else []
        except: continue
    return []

@app.route('/api/radar')
def radar():
    try:
        lat = float(request.args.get('lat', DEFAULT_LAT))
        lon = float(request.args.get('lon', DEFAULT_LON))
        test = request.args.get('test', 'false').lower() == 'true'
        local_now = get_time_local()
        now_date, now_time = local_now.strftime("%d %b %Y").upper(), local_now.strftime("%H.%M")
        w = get_weather_full(lat, lon)
        
        if test:
            return jsonify({"flight": {"icao": "E80273", "reg": "CC-BFP", "call": "LAN774", "airline": "LATAM", "color": "#E6004C", "dist": 45.2, "alt": 35000, "spd": 850, "hd": 120, "date": now_date, "time": now_time, "route": "SCL-GIG", "eta": 4, "kts": 459, "v_rate": -1500, "sqk": "3314"}, "weather": w})
        
        data = fetch_aircrafts(lat, lon)
        found = None
        if data:
            proc = []
            for s in data:
                slat, slon = s.get('lat'), s.get('lon')
                if slat and slon:
                    d = 6371 * 2 * math.asin(math.sqrt(math.sin(math.radians(slat-lat)/2)**2 + math.cos(math.radians(lat)) * math.cos(math.radians(slat)) * math.sin(math.radians(slon-lon)/2)**2))
                    call = (s.get('flight') or s.get('call') or 'N/A').strip()
                    airline, color = "PRIVATE", "#444"
                    if call.startswith(("TAM", "JJ", "LA", "LAN")): airline, color = "LATAM", "#E6004C"
                    elif call.startswith(("GLO", "G3")): airline, color = "GOL", "#FF6700"
                    elif call.startswith(("AZU", "AD")): airline, color = "AZUL", "#004590"
                    
                    proc.append({
                        "icao": str(s.get('hex', 'UNK')).upper(), "reg": str(s.get('r', 'N/A')).upper(),
                        "call": call, "airline": airline, "color": color, "dist": round(d, 1),
                        "alt": int(s.get('alt_baro', 0) if s.get('alt_baro') != "ground" else 0),
                        "spd": int(s.get('gs', 0) * 1.852), "kts": int(s.get('gs', 0)),
                        "hd": int(s.get('track', 0)), "date": now_date, "time": now_time,
                        "route": s.get('route', "--- ---"), "eta": round((d / ((s.get('gs', 1)*1.852) or 1)) * 60),
                        "v_rate": s.get('baro_rate', 0), "sqk": s.get('squawk', '0000')
                    })
            if proc: found = sorted(proc, key=lambda x: x['dist'])[0]
        return jsonify({"flight": found, "weather": w})
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
        .perfor { height: 2px; border-top: 5px dotted #ccc; position: relative; }
        .main { flex: 1; padding: 20px; display: flex; flex-direction: column; justify-content: space-between; }
        .flap { font-family: monospace; font-size: 18px; font-weight: 900; color: #000; height: 24px; display: flex; gap: 1px; }
        .char { width: 14px; height: 22px; background: #f0f0f0; border-radius: 3px; display: flex; align-items: center; justify-content: center; }
        .ticker { width: 315px; height: 42px; background: #000; border-radius: 10px; margin-top: 15px; display: flex; align-items: center; justify-content: center; color: var(--gold); font-family: monospace; font-size: 9px; text-align: center; padding: 0 10px; letter-spacing: 0.5px; border: 1px solid #333; }
        .ghost { opacity: 0.6; filter: grayscale(0.8); }
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
                <div class="dots-container"><div id="d1" class="sq"></div><div id="d2" class="sq"></div><div id="d3" class="sq"></div><div id="d4" class="sq"></div><div id="d5" class="sq"></div></div>
            </div>
            <div class="perfor"></div>
            <div class="main">
                <div style="color:#333; font-weight:900; font-size:13px; border:1.5px solid #333; padding:3px 10px; border-radius:4px; align-self:flex-start;">BOARDING PASS</div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:10px;">
                    <div><span id="lbl-l" style="font-size:7px; font-weight:900; color:#bbb;">AIRCRAFT ICAO</span><div id="f-l" class="flap"></div></div>
                    <div><span id="lbl-r" style="font-size:7px; font-weight:900; color:#bbb;">DISTANCE</span><div id="f-r" class="flap" style="color:#666"></div></div>
                    <div><span style="font-size:7px; font-weight:900; color:#bbb;">FLIGHT IDENTIFICATION</span><div id="f-call" class="flap"></div></div>
                    <div><span style="font-size:7px; font-weight:900; color:#bbb;">ROUTE (AT-TO)</span><div id="f-route" class="flap"></div></div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                    <div id="arr" style="font-size:45px; transition:1.5s;">✈</div>
                    <div style="text-align:right; color:var(--blue-txt); font-weight:900;">
                        <div id="f-date">-- --- ----</div><div id="f-time" style="font-size:20px;">--.--</div>
                        <img id="bc" src="https://bwipjs-api.metafloor.com/?bcid=code128&text=WAITING" style="width:100px; height:30px; opacity:0.15; cursor:pointer;" onclick="openMap(event)">
                    </div>
                </div>
            </div>
        </div>
        <div class="face back">
            <div style="height:100%; border:1px dashed #ccc; border-radius:15px; padding:20px; display:flex; flex-direction:column; justify-content:space-between;">
                <div style="display:flex; justify-content:space-between;">
                    <div><span style="font-size:7px; font-weight:900; color:#bbb;">ALTITUDE</span><div id="b-alt" class="flap"></div></div>
                    <div><span id="lbl-b-spd" style="font-size:7px; font-weight:900; color:#bbb;">GROUND SPEED</span><div id="b-spd" class="flap"></div></div>
                </div>
                <div style="border:3px double var(--blue-txt); color:var(--blue-txt); padding:10px; border-radius:10px; transform:rotate(-10deg); text-align:center; font-weight:900;">
                    <div style="font-size:8px;">SECURITY CHECKED</div>
                    <div id="b-date">-- --- ----</div><div id="b-time" style="font-size:22px;">--.--</div>
                    <div style="font-size:8px; margin-top:5px;">RADAR CONTACT V101</div>
                </div>
            </div>
        </div>
    </div>
    <div class="ticker" id="tk">AWAITING LOCALIZATION...</div>

    <script>
        let pos = null, act = null, isTest = false, toggle = true, lastDist = 999;
        let audioCtx = null;
        let fDate = "-- --- ----", fTime = "--.--";
        const chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ.- ";

        function playPing() {
            try {
                if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = audioCtx.createOscillator(); const gain = audioCtx.createGain();
                osc.type = 'sine'; osc.frequency.setValueAtTime(880, audioCtx.currentTime);
                gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.5);
                osc.connect(gain); gain.connect(audioCtx.destination);
                osc.start(); osc.stop(audioCtx.currentTime + 0.5);
            } catch(e) {}
        }

        function applyFlap(id, text) {
            const container = document.getElementById(id);
            if(!container) return;
            const target = text.toUpperCase().padEnd(8, ' ');
            container.innerHTML = '';
            [...target].forEach(char => {
                const span = document.createElement('span');
                span.className = 'char'; span.innerHTML = '&nbsp;';
                container.appendChild(span);
                let count = 0, max = 15 + Math.floor(Math.random() * 20);
                const interval = setInterval(() => {
                    span.innerText = chars[Math.floor(Math.random() * chars.length)];
                    if (count++ >= max) { clearInterval(interval); span.innerText = char === ' ' ? '' : char; }
                }, 40);
            });
        }

        async function update() {
            if(!pos) return;
            try {
                const r = await fetch(`/api/radar?lat=${pos.lat}&lon=${pos.lon}&test=${isTest}&_=${Date.now()}`);
                const d = await r.json();
                const w = d.weather;
                
                if(d.flight) {
                    const f = d.flight;
                    document.getElementById('card').classList.remove('ghost');
                    if(!act || act.icao !== f.icao) {
                        fDate = f.date; fTime = f.time; playPing();
                        document.getElementById('stb').style.background = f.color;
                        document.getElementById('airl').innerText = f.airline;
                        applyFlap('f-call', f.call); applyFlap('f-route', f.route);
                        document.getElementById('bc').src = `https://bwipjs-api.metafloor.com/?bcid=code128&text=${f.icao}`;
                        document.getElementById('bc').style.opacity = "0.7";
                    }
                    
                    toggle = !toggle;
                    document.getElementById('lbl-l').innerText = toggle ? "AIRCRAFT ICAO" : "REGISTRATION";
                    applyFlap('f-l', toggle ? f.icao : f.reg);
                    document.getElementById('lbl-r').innerText = toggle ? "DISTANCE" : "ESTIMATED CONTACT";
                    applyFlap('f-r', toggle ? f.dist + " KM" : "ETA " + f.eta + "M");
                    document.getElementById('lbl-b-spd').innerText = toggle ? "GROUND SPEED" : "AIRSPEED";
                    applyFlap('b-spd', toggle ? f.spd + " KMH" : f.kts + " KTS");
                    applyFlap('b-alt', f.alt + " FT");
                    
                    document.getElementById('f-date').innerText = fDate; document.getElementById('f-time').innerText = fTime;
                    document.getElementById('b-date').innerText = fDate; document.getElementById('b-time').innerText = fTime;
                    document.getElementById('arr').style.transform = `rotate(${f.hd-45}deg)`;
                    for(let i=1; i<=5; i++) document.getElementById('d'+i).className = f.dist <= (250-(i*40)) ? 'sq on' : 'sq';

                    let v_status = f.v_rate > 150 ? "SUBINDO" : (f.v_rate < -150 ? "DESCENDO" : "ESTÁVEL");
                    let d_status = f.dist < lastDist ? "APROXIMANDO" : "AFASTANDO";
                    lastDist = f.dist;

                    document.getElementById('tk').innerText = `V.RATE: ${f.v_rate} FPM (${v_status}) • SQK: ${f.sqk} • ${d_status} • TEMP: ${w.temp} • VIS: ${w.vis} • ${w.sky}`;
                    act = f;
                } else if(act) {
                    document.getElementById('card').classList.add('ghost');
                    document.getElementById('tk').innerText = "SIGNAL LOST / GHOST MODE ACTIVE";
                    for(let i=1; i<=5; i++) document.getElementById('d'+i).className = 'sq';
                } else {
                    document.getElementById('tk').innerText = `SEARCHING TRAFFIC... TEMP: ${w.temp} • VIS: ${w.vis} • ${w.sky}`;
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
        function hideUI() { document.getElementById('ui').classList.add('hide'); update(); setInterval(update, 20000); }
        navigator.geolocation.getCurrentPosition(p => { pos = {lat:p.coords.latitude, lon:p.coords.longitude}; hideUI(); }, null);
    </script>
</body>
</html>
''')

if __name__ == '__main__':
    app.run(debug=True)
