# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, render_template_string
import requests
import math
import random
from datetime import datetime, timedelta

app = Flask(__name__)

# Configurações V120 - Military Heritage & High-Density Logic
RADIUS_KM = 190 
DEFAULT_LAT = -22.9068
DEFAULT_LON = -43.1729

def get_time_local():
    """Retorna o tempo local ajustado para GMT-3."""
    return datetime.utcnow() - timedelta(hours=3)

def get_weather_desc(code):
    """Mapeamento completo de códigos meteorológicos WMO."""
    mapping = {0: "CLEAR SKY", 1: "FEW CLOUDS", 2: "SCATTERED", 3: "OVERCAST", 
               45: "FOG", 48: "DEPOSITIONS FOG", 51: "LIGHT DRIZZLE", 61: "RAIN", 80: "SHOWERS"}
    return mapping.get(code, "CONDITIONS OK")

def get_weather_data(lat, lon):
    """Busca telemetria meteorológica detalhada com tratamento de erro robusto."""
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,visibility,weather_code"
        r = requests.get(url, timeout=5).json()["current"]
        vis_km = int(r.get('visibility', 10000) / 1000)
        return {
            "temp": f"{int(r['temperature_2m'])}C",
            "vis": f"{vis_km}KM",
            "sky": get_weather_desc(r['weather_code'])
        }
    except Exception:
        return {"temp": "N/A", "vis": "N/A", "sky": "METAR ON"}

def fetch_adsb_data(lat, lon):
    """Busca dados de voo com rotação de endpoints e tratamento de timeout."""
    endpoints = [
        f"https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/250",
        f"https://opendata.adsb.fi/api/v2/lat/{lat}/lon/{lon}/dist/250"
    ]
    headers = {'User-Agent': 'RadarSystem_V120/Military_Edition', 'Accept': 'application/json'}
    random.shuffle(endpoints)
    for url in endpoints:
        try:
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                return r.json().get('aircraft', [])
        except Exception:
            continue
    return []

@app.route('/api/radar')
def radar_engine():
    """Motor de processamento de alvos com detecção de raridades e modo militar."""
    try:
        lat = float(request.args.get('lat', DEFAULT_LAT))
        lon = float(request.args.get('lon', DEFAULT_LON))
        is_test = request.args.get('test', 'false').lower() == 'true'
        
        local_dt = get_time_local()
        date_str = local_dt.strftime("%d %b %Y").upper()
        time_str = local_dt.strftime("%H.%M")
        weather = get_weather_data(lat, lon)

        if is_test:
            # Simulador de Voo Militar (SR-71 Blackbird)
            return jsonify({
                "flight": {
                    "icao": "AFE231", "reg": "61-7972", "call": "BLACKBIRD", "airline": "MILITARY OPS",
                    "color": "#000000", "dist": 4.2, "alt": 85000, "spd": 3529, "hd": 350,
                    "date": date_str, "time": time_str, "route": "CLASSIFIED", "eta": 1,
                    "kts": 1900, "vrate": 5000, "mil": True
                }, "weather": weather, "is_test": True
            })

        aircraft_list = fetch_adsb_data(lat, lon)
        processed = []
        for a in aircraft_list:
            alat, alon = a.get('lat'), a.get('lon')
            if alat and alon:
                # Haversine Formula para Precisão Geográfica
                d = 6371 * 2 * math.asin(math.sqrt(math.sin(math.radians(alat-lat)/2)**2 + 
                    math.cos(math.radians(lat)) * math.cos(math.radians(alat)) * math.sin(math.radians(alon-lon)/2)**2))
                
                if d <= RADIUS_KM:
                    call = (a.get('flight') or a.get('call') or 'N/A').strip()
                    is_mil = a.get('military', False) or any(m in call for m in ["FORCA", "NAVY", "AF1", "RCH", "BRS"])
                    
                    airline, color = ("MILITARY OPS", "#000") if is_mil else ("PRIVATE", "#444")
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
                        "vrate": a.get('baro_rate', 0), "mil": is_mil
                    })
        
        target = sorted(processed, key=lambda x: x['dist'])[0] if processed else None
        return jsonify({"flight": target, "weather": weather, "is_test": False})
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
        :root { --gold: #D4AF37; --bg: #0b0e11; --brand: #444; --blue-txt: #34a8c9; }
        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body { background: var(--bg); font-family: -apple-system, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100dvh; margin: 0; perspective: 1500px; overflow: hidden; }
        
        #ui { width: 300px; display: flex; gap: 6px; margin-bottom: 12px; z-index: 1000; transition: 0.5s; }
        #ui.hide { opacity: 0; pointer-events: none; transform: translateY(-20px); }
        input { flex: 1; padding: 14px; border-radius: 12px; border: 1px solid #333; background: #1a1d21; color: #fff; font-size: 12px; outline: none; }
        button { background: #fff; border: none; padding: 0 20px; border-radius: 12px; font-weight: 900; cursor: pointer; }
        
        .scene { width: 320px; height: 480px; position: relative; transform-style: preserve-3d; transition: transform 0.8s cubic-bezier(0.4, 0, 0.2, 1); }
        .flipped { transform: rotateY(180deg); }
        .face { position: absolute; width: 100%; height: 100%; backface-visibility: hidden; border-radius: 20px; background: #fff; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 25px 60px rgba(0,0,0,0.6); }
        .face.back { transform: rotateY(180deg); background: #fdfdfd; padding: 20px; }
        
        .stub { height: 32%; background: var(--brand); color: #fff; padding: 25px; display: flex; flex-direction: column; justify-content: center; position: relative; transition: 0.5s; }
        .stub.mil { background: #000; color: var(--gold); border-bottom: 2px solid var(--gold); }
        .dots { display: flex; gap: 5px; margin-top: 10px; }
        .sq { width: 12px; height: 12px; border: 1.5px solid rgba(255, 255, 255, 0.3); border-radius: 2px; transition: 0.4s; }
        .sq.on { background: var(--gold); box-shadow: 0 0 12px var(--gold); border: none; }
        
        .main { flex: 1; padding: 25px; display: flex; flex-direction: column; justify-content: space-between; position: relative; }
        .flap-row { display: flex; gap: 1px; font-family: 'Courier New', monospace; font-weight: 900; margin-top: 2px; }
        .char { width: 15px; height: 24px; background: #f0f0f0; color: #000; display: flex; align-items: center; justify-content: center; border-radius: 3px; font-size: 16px; border-bottom: 1px solid #ddd; }
        
        .gold-seal { position: absolute; right: 20px; bottom: 80px; width: 85px; height: 85px; border: 2px double var(--gold); border-radius: 50%; display: none; align-items: center; justify-content: center; text-align: center; color: var(--gold); font-weight: 900; font-size: 9px; transform: rotate(15deg); background: rgba(212, 175, 55, 0.05); z-index: 5; line-height: 1; }
        
        .ticker { width: 320px; min-height: 38px; background: #000; color: var(--gold); font-family: monospace; font-size: 11px; padding: 10px; margin-top: 15px; border-radius: 8px; text-align: center; letter-spacing: 1px; text-transform: uppercase; border: 1px solid #333; }
        #bc { width: 110px; opacity: 0.2; filter: grayscale(1); cursor: pointer; margin-top: 5px; }

        @media (orientation: landscape) { .scene { width: 580px; height: 280px; } .face { flex-direction: row; } .stub { width: 30%; height: 100%; border-bottom: none; border-right: 2px solid var(--gold); } .main { width: 70%; } .ticker { width: 580px; } }
    </style>
</head>
<body onclick="handleFlip(event)">
    <div id="ui">
        <input type="text" id="in" placeholder="LOCATING STATION...">
        <button onclick="startSearch()">SCAN</button>
    </div>
    
    <div class="scene" id="card">
        <div class="face front">
            <div class="stub" id="stb">
                <div style="font-size:8px; font-weight:900;">RADAR TELEMETRY</div>
                <div id="airl" style="font-weight:900; font-size:14px; margin: 4px 0;">SCANNING...</div>
                <div style="font-size:68px; font-weight:900; margin:0; letter-spacing:-4px;">19A</div>
                <div class="dots">
                    <div id="d1" class="sq"></div><div id="d2" class="sq"></div><div id="d3" class="sq"></div><div id="d4" class="sq"></div><div id="d5" class="sq"></div>
                </div>
            </div>
            <div class="main">
                <div style="border: 1.5px solid #000; padding: 2px 10px; font-weight: 900; width: fit-content; font-size: 12px; border-radius: 4px;">BOARDING PASS</div>
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 10px;">
                    <div><small id="l-label" style="font-size:8px; color:#bbb; font-weight:800;">AIRCRAFT ICAO</small><div id="f-l" class="flap-row"></div></div>
                    <div><small id="r-label" style="font-size:8px; color:#bbb; font-weight:800;">DISTANCE</small><div id="f-r" class="flap-row"></div></div>
                    <div><small style="font-size:8px; color:#bbb; font-weight:800;">FLIGHT IDENT</small><div id="f-call" class="flap-row"></div></div>
                    <div><small style="font-size:8px; color:#bbb; font-weight:800;">OP. STATUS</small><div id="f-route" class="flap-row"></div></div>
                </div>
                <div style="display:flex; justify-content: space-between; align-items: flex-end;">
                    <div id="arr" style="font-size:48px; transition: 1.5s;">✈</div>
                    <div style="text-align:right">
                        <div id="f-date" style="font-weight:bold; color: var(--blue-txt); font-size:13px;">-- --- ----</div>
                        <div id="f-time" style="font-size:26px; font-weight:900; color: var(--blue-txt);">--.--</div>
                        <img id="bc" src="https://bwipjs-api.metafloor.com/?bcid=code128&text=WAITING" onclick="openMap(event)">
                    </div>
                </div>
            </div>
        </div>
        <div class="face back">
            <div class="gold-seal" id="seal">TOP SECRET<br>RARE ASSET</div>
            <div style="border: 1px dashed #ccc; height:100%; padding: 20px; border-radius: 12px; display:flex; flex-direction:column; justify-content:space-between;">
                <div>
                    <small style="font-size:8px; color:#bbb; font-weight:800;">ALTITUDE (BARO)</small><div id="b-alt" class="flap-row"></div>
                    <small style="font-size:8px; color:#bbb; font-weight:800; margin-top:15px; display:block;">GROUND SPEED</small><div id="b-spd" class="flap-row"></div>
                </div>
                <div style="text-align:center; border: 4px double var(--blue-txt); color:var(--blue-txt); padding:15px; transform: rotate(-8deg); font-weight:900; border-radius: 10px;">
                    <div style="font-size:10px">SECURITY CHECKED</div>
                    <div id="b-date">-- --- ----</div>
                    <div id="b-time" style="font-size:24px;">--.--</div>
                    <div style="font-size:8px; margin-top:4px; opacity:0.6;">SYSTEM V120 SECURE</div>
                </div>
            </div>
        </div>
    </div>
    <div class="ticker" id="tk">INITIALIZING RADAR...</div>

    <script>
        const chars = " 0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ.-";
        let pos = null, act = null, isTest = false, toggle = true, tickIdx = 0, prevDist = null;
        let isGhost = false;

        function applyFlap(id, text) {
            const container = document.getElementById(id); if(!container) return;
            const target = text.toUpperCase().padEnd(8, ' ').substring(0, 8);
            if(container.children.length !== 8) {
                container.innerHTML = '';
                for(let i=0; i<8; i++) {
                    const s = document.createElement('span'); s.className = 'char'; s.innerText = ' ';
                    container.appendChild(s);
                }
            }
            [...target].forEach((letter, i) => {
                const slot = container.children[i];
                if(slot.innerText !== letter) {
                    let iterations = 0;
                    const timer = setInterval(() => {
                        slot.innerText = chars[Math.floor(Math.random() * chars.length)];
                        if(iterations++ > 15) { slot.innerText = letter; clearInterval(timer); }
                    }, 40);
                }
            });
        }

        async function update() {
            if(!pos) return;
            try {
                const r = await fetch(`/api/radar?lat=${pos.lat}&lon=${pos.lon}&test=${isTest}&_=${Date.now()}`);
                const d = await r.json();
                
                if(d.flight) {
                    const f = d.flight;
                    isGhost = false;
                    let proximity = "MAINTAINING";
                    if(prevDist) {
                        if(f.dist < prevDist - 0.05) proximity = "CLOSING IN";
                        else if(f.dist > prevDist + 0.05) proximity = "MOVING AWAY";
                    }
                    prevDist = f.dist;

                    if(!act || act.icao !== f.icao) {
                        document.getElementById('airl').innerText = f.airline;
                        document.getElementById('stb').className = f.mil ? 'stub mil' : 'stub';
                        document.getElementById('stb').style.background = f.mil ? '#000' : f.color;
                        applyFlap('f-call', f.call); 
                        applyFlap('f-route', f.mil ? "MILITARY" : "EN ROUTE");
                        document.getElementById('f-date').innerText = f.date; 
                        document.getElementById('f-time').innerText = f.time;
                        document.getElementById('b-date').innerText = f.date; 
                        document.getElementById('b-time').innerText = f.time;
                        document.getElementById('bc').src = `https://bwipjs-api.metafloor.com/?bcid=code128&text=${f.icao}`;
                        document.getElementById('seal').style.display = f.mil ? 'flex' : 'none';
                        if(f.mil && !d.is_test) {
                            let h = JSON.parse(localStorage.getItem('mil_history') || '[]');
                            if(!h.includes(f.icao)) { h.push(f.icao); localStorage.setItem('mil_history', JSON.stringify(h)); }
                        }
                    }
                    
                    toggle = !toggle;
                    document.getElementById('l-label').innerText = toggle ? "AIRCRAFT ICAO" : "REGISTRATION";
                    applyFlap('f-l', toggle ? f.icao : f.reg);
                    document.getElementById('r-label').innerText = toggle ? "DISTANCE" : "CONTACT ETA";
                    applyFlap('f-r', toggle ? f.dist + " KM" : f.eta + " MIN");
                    applyFlap('b-alt', f.alt + " FT");
                    applyFlap('b-spd', f.spd + " KMH");
                    
                    document.getElementById('arr').style.transform = `rotate(${f.hd-45}deg)`;
                    [190, 150, 110, 70, 30].forEach((v, i) => document.getElementById('d'+(i+1)).className = f.dist <= v ? 'sq on' : 'sq');
                    
                    const msgs = [`V.RATE: ${f.vrate} FPM`, proximity, `TEMP: ${d.weather.temp} | VIS: ${d.weather.vis}`];
                    document.getElementById('tk').innerText = msgs[tickIdx % 3];
                    tickIdx++; act = f;
                } else if(act) {
                    isGhost = true;
                    document.getElementById('tk').innerText = "SIGNAL LOST / GHOST MODE";
                    for(let i=1; i<=5; i++) document.getElementById('d'+i).className = 'sq';
                }
            } catch(e){}
        }

        function startSearch() {
            const v = document.getElementById('in').value.toUpperCase();
            if(v === "TEST") { isTest = true; pos = {lat:-22.9, lon:-43.1}; hideUI(); }
            else { fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${v}`).then(r=>r.json()).then(d=>{ if(d[0]){ pos={lat:parseFloat(d[0].lat), lon:parseFloat(d[0].lon)}; hideUI(); }}); }
        }
        function hideUI() { document.getElementById('ui').classList.add('hide'); update(); setInterval(update, 10000); }
        function handleFlip(e) { if(!e.target.closest('#ui') && !e.target.closest('#bc')) document.getElementById('card').classList.toggle('flipped'); }
        function openMap(e) { e.stopPropagation(); if(act) window.open(`https://globe.adsbexchange.com/?icao=${act.icao}`); }
        navigator.geolocation.getCurrentPosition(p => { pos={lat:p.coords.latitude, lon:p.coords.longitude}; hideUI(); }, null);
    </script>
</body>
</html>
''')

if __name__ == '__main__':
    app.run(debug=True)
