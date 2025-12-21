# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, render_template_string
import requests
import math
import random
from datetime import datetime, timedelta

app = Flask(__name__)

# Configurações V100.0 - Full Restoration & Integrity
RADIUS_KM = 190 
DEFAULT_LAT = -22.9068
DEFAULT_LON = -43.1729

def get_time_local():
    """Retorna o tempo local ajustado para GMT-3 (Brasília)."""
    return datetime.utcnow() - timedelta(hours=3)

def get_weather_desc(code):
    """Mapeamento rigoroso de códigos meteorológicos WMO."""
    mapping = {
        0: "CLEAR SKY", 1: "FEW CLOUDS", 2: "SCATTERED", 3: "OVERCAST", 
        45: "FOG", 48: "RIME FOG", 51: "LIGHT DRIZZLE", 53: "DRIZZLE",
        61: "LIGHT RAIN", 63: "RAIN", 80: "SHOWERS", 95: "STORM"
    }
    return mapping.get(code, "CONDITIONS OK")

def get_weather(lat, lon):
    """Busca telemetria meteorológica de precisão via Open-Meteo."""
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code,visibility"
        resp = requests.get(url, timeout=5).json()
        if 'current' not in resp: return {"temp": "--C", "sky": "OFFLINE", "vis": "--KM"}
        curr = resp['current']
        vis_km = int(curr.get('visibility', 10000) / 1000)
        return {
            "temp": f"{int(curr['temperature_2m'])}C", 
            "sky": get_weather_desc(curr['weather_code']), 
            "vis": f"{vis_km}KM"
        }
    except Exception as e:
        print(f"Weather Error: {e}")
        return {"temp": "--C", "sky": "METAR ON", "vis": "--KM"}

def fetch_aircrafts(lat, lon):
    """Busca dados de voo com failover entre múltiplos provedores ADSB."""
    endpoints = [
        f"https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/200",
        f"https://opendata.adsb.fi/api/v2/lat/{lat}/lon/{lon}/dist/200"
    ]
    headers = {'User-Agent': 'Mozilla/5.0 (RadarV100)', 'Accept': 'application/json'}
    random.shuffle(endpoints)
    for url in endpoints:
        try:
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200: 
                data = r.json().get('aircraft', [])
                if data: return data
        except Exception:
            continue
    return []

@app.route('/api/radar')
def radar():
    """Endpoint principal de processamento de radar."""
    try:
        lat = float(request.args.get('lat', DEFAULT_LAT))
        lon = float(request.args.get('lon', DEFAULT_LON))
        test = request.args.get('test', 'false').lower() == 'true'
        
        local_now = get_time_local()
        now_date = local_now.strftime("%d %b %Y").upper()
        now_time = local_now.strftime("%H.%M")
        w = get_weather(lat, lon)
        
        # Lógica de Teste / Simulação
        if test:
            return jsonify({
                "flight": {
                    "icao": "E4953E", "reg": "PT-MDS", "call": "TEST777", "airline": "LOCAL TEST", 
                    "color": "#34a8c9", "dist": 12.4, "alt": 35000, "spd": 850, "hd": 120, 
                    "date": now_date, "time": now_time, "route": "GIG-MIA", "eta": 2, 
                    "kts": 459, "vrate": 1500
                }, 
                "weather": w, "date": now_date, "time": now_time
            })
        
        data = fetch_aircrafts(lat, lon)
        found = None
        if data:
            proc = []
            for s in data:
                slat, slon = s.get('lat'), s.get('lon')
                if slat and slon:
                    # Cálculo de distância via Haversine
                    d = 6371 * 2 * math.asin(math.sqrt(math.sin(math.radians(slat-lat)/2)**2 + 
                        math.cos(math.radians(lat)) * math.cos(math.radians(slat)) * math.sin(math.radians(slon-lon)/2)**2))
                    
                    if d <= RADIUS_KM:
                        call = (s.get('flight') or s.get('call') or 'N/A').strip()
                        airline, color = "PRIVATE", "#444"
                        
                        # Identificação de operadoras brasileiras
                        if call.startswith(("TAM", "JJ", "LA")): airline, color = "LATAM", "#E6004C"
                        elif call.startswith(("GLO", "G3")): airline, color = "GOL", "#FF6700"
                        elif call.startswith(("AZU", "AD")): airline, color = "AZUL", "#004590"
                        
                        spd_kts = int(s.get('gs', 0))
                        spd_kmh = int(spd_kts * 1.852)
                        
                        # Tratamento de Ground / Altitude
                        baro_alt = s.get('alt_baro')
                        alt_val = 0 if baro_alt == "ground" else int(baro_alt or 0)
                        
                        proc.append({
                            "icao": str(s.get('hex', 'UNK')).upper(),
                            "reg": str(s.get('r', 'N/A')).upper(),
                            "call": call,
                            "airline": airline,
                            "color": color,
                            "dist": round(d, 1),
                            "alt": alt_val,
                            "spd": spd_kmh,
                            "kts": spd_kts,
                            "hd": int(s.get('track', 0)),
                            "date": now_date,
                            "time": now_time,
                            "route": s.get('route', "--- ---"),
                            "eta": round((d / (spd_kmh or 1)) * 60),
                            "vrate": int(s.get('baro_rate', 0))
                        })
            if proc: 
                found = sorted(proc, key=lambda x: x['dist'])[0]
                
        return jsonify({"flight": found, "weather": w, "date": now_date, "time": now_time})
    except Exception as e:
        print(f"Radar Logic Error: {e}")
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
    <title>RADAR V100</title>
    <style>
        :root { --gold: #FFD700; --bg: #0b0e11; --brand: #444; --blue-txt: #34a8c9; }
        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body { background: var(--bg); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100dvh; margin: 0; perspective: 1500px; overflow: hidden; }
        
        #ui { width: 280px; display: flex; gap: 6px; margin-bottom: 12px; z-index: 1000; transition: 0.8s cubic-bezier(0.4, 0, 0.2, 1); }
        #ui.hide { opacity: 0; pointer-events: none; transform: translateY(-20px); }
        input { flex: 1; padding: 14px; border-radius: 14px; border: none; background: #1a1d21; color: #fff; font-size: 11px; outline: none; box-shadow: inset 0 2px 4px rgba(0,0,0,0.3); }
        button { background: #fff; border: none; padding: 0 18px; border-radius: 14px; font-weight: 900; cursor: pointer; transition: 0.2s; }
        button:active { transform: scale(0.95); background: #eee; }
        
        .scene { width: 310px; height: 480px; position: relative; transform-style: preserve-3d; transition: transform 0.8s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
        .scene.flipped { transform: rotateY(180deg); }
        
        .face { position: absolute; width: 100%; height: 100%; backface-visibility: hidden; border-radius: 24px; background: #fff; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 30px 60px rgba(0,0,0,0.6); }
        .face.back { transform: rotateY(180deg); background: #f8f9fa; padding: 18px; }
        
        .stub { height: 32%; background: var(--brand); color: #fff; padding: 22px; display: flex; flex-direction: column; justify-content: center; transition: background 0.6s ease; }
        .dots-container { display: flex; gap: 5px; margin-top: 10px; }
        .sq { width: 12px; height: 12px; border: 1.5px solid rgba(255,255,255,0.25); background: rgba(0,0,0,0.2); border-radius: 3px; transition: 0.4s; }
        .sq.on { background: var(--gold); border-color: var(--gold); box-shadow: 0 0 12px var(--gold); }
        
        .perfor { height: 4px; border-top: 6px dotted #ddd; position: relative; background: #fff; }
        .perfor::before, .perfor::after { content:""; position:absolute; width:34px; height:34px; background:var(--bg); border-radius:50%; top:-17px; }
        .perfor::before { left:-28px; } .perfor::after { right:-28px; }
        
        .main { flex: 1; padding: 22px; display: flex; flex-direction: column; justify-content: space-between; }
        .flap { font-family: "Courier New", Courier, monospace; font-size: 19px; font-weight: 900; color: #000; height: 26px; display: flex; gap: 1.5px; }
        .char { width: 15px; height: 24px; background: #ececec; border-radius: 3px; display: flex; align-items: center; justify-content: center; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); }
        
        .ticker { width: 320px; height: 36px; background: #000; border-radius: 8px; margin-top: 20px; display: flex; align-items: center; justify-content: center; color: var(--gold); font-family: monospace; font-size: 12px; letter-spacing: 1px; white-space: pre; overflow: hidden; border: 1px solid #222; }
        
        /* Ajustes para modo paisagem (Landscape) */
        @media (orientation: landscape) { 
            .scene { width: 580px; height: 280px; } 
            .face { flex-direction: row !important; } 
            .stub { width: 30% !important; height: 100% !important; } 
            .perfor { width: 4px !important; height: 100% !important; border-left: 6px dotted #ddd !important; border-top: none !important; } 
            .main { width: 70% !important; } 
            .ticker { width: 580px; } 
        }
    </style>
</head>
<body onclick="handleFlip(event)">
    <div id="ui">
        <input type="text" id="in" placeholder="ENTER LOCATION (OR 'TEST')">
        <button onclick="startSearch()">SCAN</button>
    </div>
    
    <div class="scene" id="card">
        <div class="face front">
            <div class="stub" id="stb">
                <div style="font-size:8px; font-weight:900; opacity:0.8; letter-spacing:1px;">RADAR ACTIVE</div>
                <div style="font-size:11px; font-weight:900; margin-top:6px; overflow:hidden; white-space:nowrap;" id="airl">WAITING DATA...</div>
                <div style="font-size:68px; font-weight:900; letter-spacing:-5px; margin:4px 0;">19A</div>
                <div class="dots-container">
                    <div id="d1" class="sq"></div><div id="d2" class="sq"></div><div id="d3" class="sq"></div><div id="d4" class="sq"></div><div id="d5" class="sq"></div>
                </div>
            </div>
            
            <div class="perfor"></div>
            
            <div class="main">
                <div style="color: #333; font-weight: 900; font-size: 12px; border: 2px solid #333; padding: 4px 12px; border-radius: 6px; align-self: flex-start; letter-spacing: 1px;">BOARDING PASS</div>
                
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:15px;">
                    <div><span id="icao-label" style="font-size:7px; font-weight:900; color:#aaa;">AIRCRAFT ICAO</span><div id="f-icao" class="flap"></div></div>
                    <div><span id="dist-label" style="font-size:7px; font-weight:900; color:#aaa;">DISTANCE</span><div id="f-dist" class="flap" style="color:#555"></div></div>
                    <div><span style="font-size:7px; font-weight:900; color:#aaa;">FLIGHT IDENTIFICATION</span><div id="f-call" class="flap"></div></div>
                    <div><span style="font-size:7px; font-weight:900; color:#aaa;">ROUTE (AT-TO)</span><div id="f-route" class="flap"></div></div>
                </div>
                
                <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-top:10px;">
                    <div id="arr" style="font-size:50px; transition:2s cubic-bezier(0.1, 0, 0.1, 1);">✈</div>
                    <div style="text-align:right; color:var(--blue-txt); font-weight:900;">
                        <div id="f-line1" style="font-size:10px;">-- --- ----</div>
                        <div id="f-line2" style="font-size:26px; line-height:1;">--.--</div>
                        <img id="bc" src="https://bwipjs-api.metafloor.com/?bcid=code128&text=WAITING" style="width:115px; height:38px; opacity:0.2; cursor:pointer; margin-top:5px;" onclick="openMap(event)">
                    </div>
                </div>
            </div>
        </div>
        
        <div class="face back">
            <div style="height:100%; border:1.5px dashed #d1d1d1; border-radius:20px; padding:22px; display:flex; flex-direction:column; justify-content:space-between;">
                <div style="display:flex; justify-content:space-between;">
                    <div><span style="font-size:8px; font-weight:900; color:#aaa;">ALTITUDE (FT)</span><div id="b-alt" class="flap"></div></div>
                    <div><span id="spd-label" style="font-size:8px; font-weight:900; color:#aaa;">GROUND SPEED</span><div id="b-spd" class="flap"></div></div>
                </div>
                
                <div style="border:4px double var(--blue-txt); color:var(--blue-txt); padding:15px; border-radius:12px; transform:rotate(-8deg); align-self:center; text-align:center; font-weight:900; width: 80%;">
                    <div style="font-size:9px; letter-spacing:2px;">SECURITY CHECKED</div>
                    <div id="b-date-line1" style="font-size:11px; margin:4px 0;">-- --- ----</div>
                    <div id="b-date-line2" style="font-size:28px; line-height:1;">--.--</div>
                    <div style="font-size:8px; margin-top:6px; opacity:0.8;">RADAR CONTACT V100.0</div>
                </div>
                
                <div style="font-size:7px; color:#ccc; text-align:center; font-weight:bold;">ADS-B DATA STREAM SOURCE: OPEN-SKY / ADSB-LOL</div>
            </div>
        </div>
    </div>
    
    <div class="ticker" id="tk">INITIALIZING RADAR SYSTEM...</div>

    <script>
        let pos = null, act = null, prevDist = null, isTest = false, weather = null;
        let toggleState = true, isGhost = false, tickerMsg = [], tickerIdx = 0;
        const chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ.- ";

        // Função de Flap Mecânico com Parada Estocástica (Aleatória)
        function applyFlap(id, text, isTicker = false) {
            const container = document.getElementById(id); if(!container) return;
            const limit = isTicker ? 32 : 8;
            const target = text.toUpperCase().padEnd(limit, ' ');
            container.innerHTML = '';
            
            [...target].forEach((char) => {
                const span = document.createElement('span');
                if(!isTicker) span.className = 'char';
                span.innerHTML = '&nbsp;';
                container.appendChild(span);
                
                let count = 0;
                // Cada letra decide seu próprio tempo de rotação entre 15 e 65 ciclos
                let maxIterations = 15 + Math.floor(Math.random() * 50); 
                
                const interval = setInterval(() => {
                    span.innerText = chars[Math.floor(Math.random() * chars.length)];
                    if (count++ >= maxIterations) { 
                        clearInterval(interval); 
                        span.innerHTML = (char === ' ') ? '&nbsp;' : char; 
                    }
                }, 35); 
            });
        }

        async function update() {
            if(!pos) return;
            try {
                const r = await fetch(`/api/radar?lat=${pos.lat}&lon=${pos.lon}&test=${isTest}&_=${Date.now()}`);
                const d = await r.json(); 
                if(!d) return;
                weather = d.weather;
                
                if(d.flight) {
                    const f = d.flight; 
                    isGhost = false;
                    document.getElementById('stb').style.background = f.color;
                    
                    // Lógica de Proximidade
                    let proximity = "MAINTAINING";
                    if(prevDist !== null) {
                        if(f.dist < prevDist - 0.04) proximity = "CLOSING IN";
                        else if(f.dist > prevDist + 0.04) proximity = "MOVING AWAY";
                    }
                    prevDist = f.dist;

                    // Atualiza campos se a aeronave mudar
                    if(!act || act.icao !== f.icao) {
                        document.getElementById('airl').innerText = f.airline;
                        applyFlap('f-call', f.call); 
                        applyFlap('f-route', f.route);
                        applyFlap('f-icao', f.icao); 
                        applyFlap('f-dist', f.dist + " KM");
                        document.getElementById('bc').src = `https://bwipjs-api.metafloor.com/?bcid=code128&text=${f.icao}&scale=2`;
                    }
                    
                    // Updates estáticos (sem animação flap para evitar poluição visual)
                    document.getElementById('f-line1').innerText = f.date; 
                    document.getElementById('f-line2').innerText = f.time;
                    document.getElementById('b-date-line1').innerText = f.date; 
                    document.getElementById('b-date-line2').innerText = f.time;
                    
                    // Radar Dots
                    for(let i=1; i<=5; i++) {
                        const threshold = 190 - (i-1)*40;
                        document.getElementById('d'+i).className = f.dist <= threshold ? 'sq on' : 'sq';
                    }
                    
                    if(!act || act.alt !== f.alt) applyFlap('b-alt', f.alt + " FT");
                    document.getElementById('arr').style.transform = `rotate(${f.hd-45}deg)`;
                    act = f;

                    tickerMsg = [
                        `V.RATE: ${f.vrate} FPM`, 
                        proximity, 
                        `TEMP: ${weather.temp} | ${weather.sky}`,
                        `VISIBILITY: ${weather.vis}`
                    ];
                } else if(act) {
                    // MODO GHOST: Aeronave sumiu do radar mas mantemos o registro
                    isGhost = true; 
                    document.getElementById('stb').style.background = "var(--brand)";
                    tickerMsg = ["SIGNAL LOST / GHOST MODE", "SEARCHING TRAFFIC...", `LOCAL: ${weather.sky}`];
                    for(let i=1; i<=5; i++) document.getElementById('d'+i).className = 'sq';
                }
            } catch(e) { console.error("Update Error", e); }
        }

        function updateTicker() { 
            if (tickerMsg.length > 0) { 
                applyFlap('tk', tickerMsg[tickerIdx], true); 
                tickerIdx = (tickerIdx + 1) % tickerMsg.length; 
            } 
        }
        
        setInterval(updateTicker, 9000);
        
        // Alternância de Informação Lateral
        setInterval(() => {
            if(act && !isGhost) {
                toggleState = !toggleState;
                document.getElementById('icao-label').innerText = toggleState ? "AIRCRAFT ICAO" : "REGISTRATION";
                applyFlap('f-icao', toggleState ? act.icao : act.reg);
                document.getElementById('dist-label').innerText = toggleState ? "DISTANCE" : "CONTACT ETA";
                applyFlap('f-dist', toggleState ? act.dist + " KM" : act.eta + " MIN");
            }
        }, 18000);

        function startSearch() {
            const v = document.getElementById('in').value.toUpperCase();
            if(v === "TEST") { isTest = true; pos = {lat:-22.9, lon:-43.1}; hideUI(); }
            else { 
                fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${v}`)
                .then(r=>r.json()).then(d=>{ 
                    if(d[0]) { pos = {lat:parseFloat(d[0].lat), lon:parseFloat(d[0].lon)}; hideUI(); } 
                }); 
            }
        }
        
        function handleFlip(e) { 
            if(!e.target.closest('#ui') && !e.target.closest('#bc')) 
                document.getElementById('card').classList.toggle('flipped'); 
        }
        
        function openMap(e) { 
            e.stopPropagation(); 
            if(act) window.open(`https://globe.adsbexchange.com/?icao=${act.icao}`, '_blank'); 
        }
        
        function hideUI() { 
            document.getElementById('ui').classList.add('hide'); 
            setTimeout(() => { update(); setInterval(update, 15000); }, 800); 
        }

        // Auto-localização inicial
        navigator.geolocation.getCurrentPosition(
            p => { pos = {lat:p.coords.latitude, lon:p.coords.longitude}; hideUI(); }, 
            () => { applyFlap('tk', 'ENTER LOCATION TO START', true); }, 
            { timeout: 6000 }
        );
    </script>
</body>
</html>
''')

if __name__ == '__main__':
    app.run(debug=True)
