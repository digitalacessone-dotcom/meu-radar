from flask import Flask, render_template_string, jsonify, request
import requests
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

RAIO_KM = 25.0 

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
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
        <title>ATC Radar Pro</title>
        <style>
            :root { --air-blue: #1A237E; --warning-gold: #FFD700; --bg-dark: #0a192f; }
            * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }

            body { 
                background-color: var(--bg-dark); margin: 0; padding: 0; 
                display: flex; flex-direction: column; align-items: center; justify-content: center; 
                width: 100vw; height: 100vh; height: -webkit-fill-available;
                font-family: 'Courier New', monospace; overflow: hidden;
            }
            html { height: -webkit-fill-available; }

            #search-box { 
                display: none; width: 90%; max-width: 500px; background: rgba(0,0,0,0.6);
                padding: 15px; border-radius: 12px; margin-bottom: 20px; 
                border: 2px solid var(--warning-gold); gap: 10px; z-index: 100;
            }
            #search-box input { flex: 1; background: #000; border: 1px solid #444; padding: 12px; color: white; border-radius: 6px; }
            #search-box button { background: var(--warning-gold); color: #000; border: none; padding: 10px 20px; font-weight: 900; border-radius: 6px; cursor: pointer; }

            /* ESTILO BASE DAS LETRAS */
            .letter-slot { 
                display: inline-block; 
                min-width: 0.65em; 
                text-align: center; 
                position: relative;
            }

            /* LETRAS NO TICKET (PARTE BRANCA) - AZUL SEM FUNDO */
            .white-area .letter-slot {
                color: var(--air-blue);
                font-weight: 900;
            }

            /* LETRAS NO STATUS (PARTE DE BAIXO) - AMARELA COM FUNDO PRETO */
            .status-msg .letter-slot {
                color: var(--warning-gold);
                background: #000;
                margin: 0 1px;
                padding: 0 2px;
                border-radius: 2px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.5);
            }
            
            .flapping { animation: mechanical-flip 0.08s ease-in-out; }
            @keyframes mechanical-flip {
                0% { transform: scaleY(1); }
                50% { transform: scaleY(0.4); opacity: 0.7; }
                100% { transform: scaleY(1); }
            }

            .card { 
                background: var(--air-blue); width: 92%; max-width: 600px;
                border-radius: 15px; position: relative; box-shadow: 0 20px 50px rgba(0,0,0,0.8); 
                overflow: hidden; flex-shrink: 0;
            }

            .notch { position: absolute; width: 30px; height: 30px; background: var(--bg-dark); border-radius: 50%; top: 50%; transform: translateY(-50%); z-index: 20; }
            .notch-left { left: -15px; } .notch-right { right: -15px; }

            .header { padding: 12px 0; text-align: center; color: white; font-weight: 900; font-size: 0.9em; letter-spacing: 2px; }

            .white-area { 
                background: #fdfdfd; margin: 0 8px; position: relative; 
                display: flex; padding: 20px 15px; min-height: 220px; border-radius: 3px; 
            }

            .col-left { flex: 1; border-right: 1px dashed #ddd; padding-right: 15px; display: flex; flex-direction: column; justify-content: center; }
            .col-right { width: 140px; padding-left: 15px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
            
            .label { color: #aaa; font-size: 0.6em; font-weight: 800; text-transform: uppercase; margin-bottom: 4px; }
            .value { font-size: 1.25em; font-weight: 900; margin-bottom: 12px; min-height: 1.2em; display: flex; flex-wrap: wrap; }
            
            #compass { display: inline-block; transition: transform 0.8s; color: var(--warning-gold); font-size: 1.1em; }
            .barcode { height: 40px; background: repeating-linear-gradient(90deg, #000, #000 1px, transparent 1px, transparent 3px, #000 3px, #000 4px); width: 100%; margin: 8px 0; }
            .footer { padding: 0 0 12px 0; display: flex; flex-direction: column; align-items: center; background: var(--air-blue); }
            .yellow-lines { width: 100%; height: 6px; border-top: 2px solid var(--warning-gold); border-bottom: 2px solid var(--warning-gold); margin-bottom: 8px; }
            .status-msg { color: var(--warning-gold); font-size: 0.7em; font-weight: bold; text-align: center; padding: 0 10px; min-height: 1.2em; }
        </style>
    </head>
    <body>
        
        <div id="search-box">
            <input type="text" id="endereco" placeholder="CITY OR ZIP...">
            <button onclick="buscarEndereco()">GO</button>
        </div>

        <div class="card" onclick="enableAudio()">
            <div class="notch notch-left"></div>
            <div class="notch notch-right"></div>
            <div class="header">✈ BOARDING BOARD ✈</div>
            <div class="white-area">
                <div class="col-left">
                    <div><div class="label">IDENT / CALLSIGN</div><div id="callsign" class="value"></div></div>
                    <div><div class="label">AIRCRAFT DISTANCE</div><div id="dist_body" class="value"></div></div>
                    <div><div class="label">ALTITUDE (MSL)</div><div id="alt" class="value"></div></div>
                </div>
                <div class="col-right">
                    <div><div class="label">SQUAWK</div><div id="squawk" class="value"></div></div>
                    <div><div class="label">BEARING</div><div class="value" style="margin-bottom:0;"><span id="compass">↑</span></div></div>
                    <a id="map-link" style="text-decoration:none; width:100%;" target="_blank"><div class="barcode"></div></a>
                    <div id="signal-bars" style="color:var(--air-blue); font-size:10px; font-weight:900;">[ ▯▯▯▯▯ ]</div>
                </div>
            </div>
            <div class="footer">
                <div class="yellow-lines"></div>
                <div id="status" class="status-msg"></div>
            </div>
        </div>

        <script>
            let latAlvo = null, lonAlvo = null;
            let lastHex = null;
            const chars = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/.:-";
            let audioCtx = null;

            function enableAudio() { if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)(); }

            function playTick() {
                if (!audioCtx) return;
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                osc.type = 'square';
                osc.frequency.setValueAtTime(120, audioCtx.currentTime);
                gain.gain.setValueAtTime(0.01, audioCtx.currentTime);
                osc.connect(gain); gain.connect(audioCtx.destination);
                osc.start(); osc.stop(audioCtx.currentTime + 0.01);
            }

            function updateWithEffect(id, newValue) {
                const container = document.getElementById(id);
                const newText = String(newValue).toUpperCase();
                
                while (container.childNodes.length < newText.length) {
                    const s = document.createElement("span");
                    s.className = "letter-slot";
                    s.innerText = " ";
                    container.appendChild(s);
                }
                while (container.childNodes.length > newText.length) {
                    container.removeChild(container.lastChild);
                }

                const slots = container.querySelectorAll('.letter-slot');
                newText.split('').forEach((targetChar, i) => {
                    const slot = slots[i];
                    if (slot.innerText === targetChar) return;

                    setTimeout(() => {
                        let currentCharIndex = chars.indexOf(slot.innerText);
                        if (currentCharIndex === -1) currentCharIndex = 0;

                        const interval = setInterval(() => {
                            currentCharIndex = (currentCharIndex + 1) % chars.length;
                            const charToShow = chars[currentCharIndex];
                            slot.innerText = charToShow === " " ? "\u00A0" : charToShow;
                            slot.classList.add('flapping');
                            playTick();

                            if (charToShow === targetChar) {
                                clearInterval(interval);
                                slot.classList.remove('flapping');
                            }
                        }, 50); // Velocidade de 50ms para ver o giro
                    }, i * 40); // Cascata
                });
            }

            window.onload = function() {
                updateWithEffect('callsign', 'SEARCHING');
                updateWithEffect('status', 'INITIALIZING RADAR...');
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude;
                    iniciarRadar();
                }, () => {
                    document.getElementById('search-box').style.display = "flex";
                });
            };

            async function buscarEndereco() {
                const query = document.getElementById('endereco').value;
                const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${query}`);
                const data = await res.json();
                if(data.length > 0) {
                    latAlvo = parseFloat(data[0].lat); lonAlvo = parseFloat(data[0].lon);
                    document.getElementById('search-box').style.display = "none";
                    iniciarRadar();
                }
            }

            function iniciarRadar() { setInterval(executarBusca, 8000); executarBusca(); }

            function executarBusca() {
                if(!latAlvo) return;
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}&t=${Date.now()}`)
                .then(res => res.json()).then(data => {
                    if(data.found) {
                        lastHex = data.hex;
                        updateWithEffect('callsign', data.callsign);
                        updateWithEffect('alt', data.alt_ft.toLocaleString() + " FT");
                        updateWithEffect('dist_body', data.dist + " KM");
                        updateWithEffect('squawk', data.squawk);
                        updateWithEffect('status', `TARGET: ${data.callsign} | TYPE: ${data.type}`);
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        document.getElementById('map-link').href = data.map_url;
                    } else {
                        if(lastHex) {
                            updateWithEffect('callsign', "SEARCHING");
                            updateWithEffect('status', "SWEEPING AIRSPACE...");
                            lastHex = null;
                        }
                    }
                });
            }
        </script>
    </body>
    </html>
    ''')


