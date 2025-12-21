# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, render_template_string
import requests
import math
import random
from datetime import datetime, timedelta

app = Flask(__name__)

# Config V116 - Full Code Restoration (320+ Lines) - Military Audio & Pure Ticker
RADIUS_KM = 190 
DEFAULT_LAT = -22.9068
DEFAULT_LON = -43.1729

def get_time_local():
    """Retorna o tempo local ajustado para GMT-3."""
    return datetime.utcnow() - timedelta(hours=3)

def get_weather_data(lat, lon):
    """Busca telemetria meteorológica completa para o sistema."""
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,visibility,weather_code"
        r = requests.get(url, timeout=5).json()["current"]
        return {
            "temp": f"{int(r['temperature_2m'])}C",
            "vis": f"{int(r['visibility']/1000)}KM",
            "code": r['weather_code']
        }
    except Exception:
        return {"temp": "N/A", "vis": "N/A", "code": 0}

def fetch_adsb_data(lat, lon):
    """Busca dados de voo com tratamento de erro e redundância."""
    # Lista de mirrors para garantir que o sinal não caia por timeout do servidor
    endpoints = [
        f"https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/250",
        f"https://opendata.adsb.fi/api/v2/lat/{lat}/lon/{lon}/dist/250"
    ]
    for url in endpoints:
        try:
            r = requests.get(url, headers={'User-Agent': 'RadarSystemV116/1.0'}, timeout=5)
            if r.status_code == 200:
                return r.json().get('aircraft', [])
        except Exception:
            continue
    return []

@app.route('/api/radar')
def radar_engine():
    """Motor principal de processamento de alvos e filtragem militar."""
    try:
        lat = float(request.args.get('lat', DEFAULT_LAT))
        lon = float(request.args.get('lon', DEFAULT_LON))
        is_test = request.args.get('test', 'false').lower() == 'true'
        
        local_dt = get_time_local()
        date_str = local_dt.strftime("%d %b %Y").upper()
        time_str = local_dt.strftime("%H.%M")
        weather = get_weather_data(lat, lon)

        if is_test:
            return jsonify({
                "flight": {
                    "icao": "AFE231", "reg": "MIL-777", "call": "RCH777", "airline": "MILITARY",
                    "color": "#1a3a1a", "dist": 42.1, "alt": 28500, "spd": 820, "hd": 240,
                    "date": date_str, "time": time_str, "route": "BUNKER ALPHA", "eta": 4,
                    "kts": 442, "v_rate": -1500, "sqk": "7700", "mil": True
                }, "weather": weather
            })

        aircraft_list = fetch_adsb_data(lat, lon)
        if not aircraft_list:
            return jsonify({"flight": None, "weather": weather})

        processed = []
        for a in aircraft_list:
            alat, alon = a.get('lat'), a.get('lon')
            if alat and alon:
                # Cálculo de distância Haversine
                d = 6371 * 2 * math.asin(math.sqrt(math.sin(math.radians(alat-lat)/2)**2 + 
                    math.cos(math.radians(lat)) * math.cos(math.radians(alat)) * math.sin(math.radians(alon-lon)/2)**2))
                
                if d <= RADIUS_KM:
                    call = (a.get('flight') or a.get('call') or 'N/A').strip()
                    # Detecção de aeronave militar
                    is_mil = a.get('military', False) or any(m in call for m in ["FORCA", "MIL", "NAVY", "AF1", "RCH", "BRS"])
                    
                    airline, color = ("MILITARY", "#1a3a1a") if is_mil else ("PRIVATE", "#444")
                    if call.startswith(("TAM", "JJ", "LA")): airline, color = "LATAM", "#E6004C"
                    elif call.startswith(("GLO", "G3")): airline, color = "GOL", "#FF6700"
                    elif call.startswith(("AZU", "AD")): airline, color = "AZUL", "#004590"

                    processed.append({
                        "icao": str(a.get('hex', 'UNK')).upper(), "reg": str(a.get('r', 'N/A')).upper(),
                        "call": call, "airline": airline, "color": color, "dist": round(d, 1),
                        "alt": int(a.get('alt_baro', 0) if a.get('alt_baro') != "ground" else 0),
                        "spd": int(a.get('gs', 0) * 1.852), "kts": int(a.get('gs', 0)),
                        "hd": int(a.get('track', 0)), "date": date_str, "time": time_str,
                        "route": a.get('route', "EN ROUTE"), "eta": round((d / ((a.get('gs', 1)*1.852) or 1)) * 60),
                        "v_rate": a.get('baro_rate', 0), "sqk": a.get('squawk', '0000'), "mil": is_mil
                    })
        
        target = sorted(processed, key=lambda x: x['dist'])[0] if processed else None
        return jsonify({"flight": target, "weather": weather})
    except Exception as e:
        return jsonify({"flight": None, "error": str(e)})

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
        :root { --gold: #FFD700; --bg: #0b0e11; --brand: #555; }
        body { background: var(--bg); font-family: -apple-system, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100dvh; margin: 0; perspective: 1200px; }
        #ui { width: 340px; display: flex; gap: 5px; margin-bottom: 10px; z-index: 1000; }
        #ui.hide { display: none; }
        input { flex: 1; padding: 12px; border-radius: 8px; border: none; background: #222; color: #fff; font-size: 14px; border: 1px solid #333; }
        button { background: #fff; border: none; padding: 12px; border-radius: 8px; font-weight: bold; cursor: pointer; }
        
        .scene { width: 340px; height: 500px; position: relative; transform-style: preserve-3d; transition: transform 0.8s; }
        .flipped { transform: rotateY(180deg); }
        .face { position: absolute; width: 100%; height: 100%; backface-visibility: hidden; border-radius: 20px; background: #fff; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 15px 35px rgba(0,0,0,0.5); }
        .face.back { transform: rotateY(180deg); background: #eee; padding: 20px; }
        
        .stub { height: 30%; background: var(--brand); color: #fff; padding: 20px; display: flex; flex-direction: column; justify-content: center; transition: background 0.5s; }
        .dots { display: flex; gap: 5px; margin-top: 10px; }
        .sq { width: 14px; height: 14px; border: 1.5px solid rgba(255,255,255,0.2); border-radius: 2px; }
        .sq.on { background: var(--gold); box-shadow: 0 0 8px var(--gold); border: none; }
        
        .main { flex: 1; padding: 20px; display: flex; flex-direction: column; justify-content: space-between; }
        .flap-row { display: flex; gap: 1px; font-family: 'Courier New', monospace; font-weight: 900; }
        .char { width: 16px; height: 26px; background: #333; color: #fff; display: flex; align-items: center; justify-content: center; border-radius: 2px; font-size: 18px; border-bottom: 2px solid #000; }
        
        .ticker { width: 340px; min-height: 48px; background: #000; color: var(--gold); font-family: monospace; font-size: 11px; padding: 10px; margin-top: 15px; border-radius: 5px; text-align: center; border: 1px solid #333; display: flex; align-items: center; justify-content: center; text-transform: uppercase; letter-spacing: 0.5px; }
        #bc { width: 130px; cursor: pointer; opacity: 0.8; margin-top: 5px; }
        small { font-size: 9px; color: #777; text-transform: uppercase; display: block; margin-bottom: 2px; }

        @media (orientation: landscape) { .scene { width: 600px; height: 300px; } .face { flex-direction: row; } .stub { width: 30%; height: 100%; } .main { width: 70%; } .ticker { width: 600px; } }
    </style>
</head>
<body onclick="handleFlip(event)">
    <div id="ui">
        <input type="text" id="in" placeholder="STATION CITY">
        <button onclick="startSearch()">SCAN</button>
    </div>
    
    <div class="scene" id="card">
        <div class="face front">
            <div class="stub" id="stb">
                <div style="font-size:8px; opacity:0.7;">RADAR SIGNAL</div>
                <div id="airl" style="font-weight:900; font-size:16px; margin: 2px 0;">IDLE</div>
                <h1 style="font-size:60px; margin:0; letter-spacing:-2px;">19A</h1>
                <div class="dots">
                    <div id="d1" class="sq"></div><div id="d2" class="sq"></div><div id="d3" class="sq"></div><div id="d4" class="sq"></div><div id="d5" class="sq"></div>
                </div>
            </div>
            <div class="main">
                <div style="border: 2px solid #000; padding: 2px 8px; font-weight: 900; width: fit-content; font-size: 11px; margin-bottom: 5px;">BOARDING PASS</div>
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                    <div><small id="l-label">AIRCRAFT ICAO</small><div id="f-l" class="flap-row"></div></div>
                    <div><small id="r-label">DISTANCE</small><div id="f-r" class="flap-row"></div></div>
                    <div><small>FLIGHT IDENT</small><div id="f-call" class="flap-row"></div></div>
                    <div><small>ROUTE / STATUS</small><div id="f-route" class="flap-row"></div></div>
                </div>
                <div style="display:flex; justify-content: space-between; align-items: flex-end;">
                    <div id="arr" style="font-size:50px; transition: 0.5s;">✈</div>
                    <div style="text-align:right">
                        <div id="f-date" style="font-weight:bold; color: #34a8c9; font-size:14px;">-- --- ----</div>
                        <div id="f-time" style="font-size:28px; font-weight:900; color: #34a8c9;">--.--</div>
                        <img id="bc" src="https://bwipjs-api.metafloor.com/?bcid=code128&text=WAITING" onclick="openMap(event)">
                    </div>
                </div>
            </div>
        </div>
        <div class="face back">
            <div style="border: 1px dashed #999; height:100%; padding: 20px; border-radius: 10px; display:flex; flex-direction:column; justify-content:space-between;">
                <div style="display:flex; justify-content:space-between">
                    <div><small>ALTITUDE (FT)</small><div id="b-alt" class="flap-row"></div></div>
                    <div><small id="b-label">GROUND SPD</small><div id="b-spd" class="flap-row"></div></div>
                </div>
                <div style="text-align:center; border: 4px double #34a8c9; color:#34a8c9; padding:15px; transform: rotate(-5deg); font-weight:900;">
                    <div style="font-size:12px">SECURITY CHECKED</div>
                    <div id="b-date">-- --- ----</div>
                    <div id="b-time" style="font-size:26px;">--.--</div>
                    <div style="font-size:8px; margin-top:5px; opacity:0.6;">V116 SYSTEM SECURE</div>
                </div>
            </div>
        </div>
    </div>
    <div class="ticker" id="tk">WAITING FOR NETWORK...</div>

    <script>
        const chars = " 0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ.-";
        let pos = null, act = null, isTest = false, toggle = true, lastDist = 999, tickIdx = 0;
        let audioCtx = null;

        function playSound(type) {
            try {
                if(!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const o = audioCtx.createOscillator(); const g = audioCtx.createGain();
                if(type === 'mil') {
                    o.type = 'sine'; o.frequency.setValueAtTime(70, audioCtx.currentTime);
                    g.gain.setValueAtTime(0.15, audioCtx.currentTime);
                    g.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.7);
                    o.connect(g); g.connect(audioCtx.destination); o.start(); o.stop(audioCtx.currentTime + 0.7);
                } else {
                    o.type = 'triangle'; o.frequency.setValueAtTime(120 + Math.random() * 40, audioCtx.currentTime);
                    g.gain.setValueAtTime(0.03, audioCtx.currentTime);
                    g.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.05);
                    o.connect(g); g.connect(audioCtx.destination); o.start(); o.stop(audioCtx.currentTime + 0.05);
                }
            } catch(e){}
        }

        function applyFlap(id, text) {
            const container = document.getElementById(id); if(!container) return;
            const size = 9; const target = text.toUpperCase().padEnd(size, ' ').substring(0, size);
            if(container.children.length !== size) {
                container.innerHTML = '';
                for(let i=0; i<size; i++) {
                    const s = document.createElement('span'); s.className = 'char'; s.innerText = ' ';
                    container.appendChild(s);
                }
            }
            [...target].forEach((letter, i) => {
                const slot = container.children[i];
                let curIdx = chars.indexOf(slot.innerText);
                if(slot.innerText !== letter) {
                    const timer = setInterval(() => {
                        curIdx = (curIdx + 1) % chars.length; slot.innerText = chars[curIdx];
                        playSound('tick');
                        if(chars[curIdx] === letter) clearInterval(timer);
                    }, 25 + (i * 8)); 
                }
            });
        }

        async function update() {
            if(!pos) return;
            try {
                const r = await fetch(`/api/radar?lat=${pos.lat}&lon=${pos.lon}&test=${isTest}&_=${Date.now()}`);
                const d = await r.json();
                const tkEl = document.getElementById('tk');
                
                if(d.flight) {
                    const f = d.flight;
                    if(!act || act.icao !== f.icao) {
                        document.getElementById('stb').style.background = f.color;
                        document.getElementById('airl').innerText = f.airline;
                        applyFlap('f-call', f.call); applyFlap('f-route', f.route);
                        document.getElementById('f-date').innerText = f.date; document.getElementById('f-time').innerText = f.time;
                        document.getElementById('b-date').innerText = f.date; document.getElementById('b-time').innerText = f.time;
                        document.getElementById('bc').src = `https://bwipjs-api.metafloor.com/?bcid=code128&text=${f.icao}`;
                        if(f.mil) playSound('mil');
                    }
                    
                    toggle = !toggle;
                    document.getElementById('l-label').innerText = toggle ? "AIRCRAFT ICAO" : "REGISTRATION";
                    applyFlap('f-l', toggle ? f.icao : f.reg);
                    document.getElementById('r-label').innerText = toggle ? "DISTANCE" : "CONTACT ETA";
                    applyFlap('f-r', toggle ? f.dist + " KM" : f.eta + " MIN");
                    document.getElementById('b-label').innerText = toggle ? "GROUND SPEED" : "AIRSPEED KTS";
                    applyFlap('b-spd', toggle ? f.spd + " KMH" : f.kts + " KTS");
                    applyFlap('b-alt', f.alt + " FT");
                    
                    document.getElementById('arr').style.transform = `rotate(${f.hd-45}deg)`;
                    [190, 150, 110, 70, 30].forEach((v, i) => document.getElementById('d'+(i+1)).className = f.dist <= v ? 'sq on' : 'sq');
                    
                    let trend = f.dist < lastDist ? "APPROACHING" : "DEPARTING";
                    const msgs = ["CONTACT ESTABLISHED", trend, `ALTITUDE: ${f.alt} FT` ];
                    tkEl.innerText = msgs[tickIdx % 3];
                    tickIdx++; lastDist = f.dist; act = f;
                } else if (act) {
                    tkEl.innerText = "SIGNAL LOST / GHOST MODE ACTIVE";
                } else {
                    tkEl.innerText = "SEARCHING TRAFFIC...";
                }
            } catch(e){}
        }

        function startSearch() {
            const v = document.getElementById('in').value.toUpperCase();
            if(v === "TEST") { isTest = true; pos = {lat:-22.9, lon:-43.1}; hideUI(); }
            else { fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${v}`).then(r=>r.json()).then(d=>{ if(d[0]){ pos={lat:parseFloat(d[0].lat), lon:parseFloat(d[0].lon)}; hideUI(); }}); }
        }
        function hideUI() { document.getElementById('ui').classList.add('hide'); update(); setInterval(update, 8000); }
        function handleFlip(e) { if(!e.target.closest('#ui') && !e.target.closest('#bc')) document.getElementById('card').classList.toggle('flipped'); }
        function openMap(e) { e.stopPropagation(); if(act) window.open(`https://globe.adsbexchange.com/?icao=${act.icao}`); }
        
        navigator.geolocation.getCurrentPosition(p => { pos={lat:p.coords.latitude, lon:p.coords.longitude}; hideUI(); }, null);
    </script>
</body>
</html>
''')
