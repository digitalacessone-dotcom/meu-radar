from flask import Flask, render_template_string, jsonify, request
import requests
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

RAIO_KM = 50.0 

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
                min-height: 100vh; font-family: 'Courier New', monospace; overflow: hidden;
            }

            .card { 
                background: var(--air-blue); width: 92%; max-width: 580px;
                border-radius: 20px; position: relative; 
                box-shadow: 0 40px 80px rgba(0,0,0,0.8); 
                overflow: hidden; 
            }

            /* MEIA-LUA GRANDE E MARCADA */
            .notch { 
                position: absolute; 
                width: 60px; height: 60px; 
                background: var(--bg-dark); 
                border-radius: 50%; 
                top: 50%; 
                transform: translateY(-50%); 
                z-index: 20; 
                box-shadow: inset 0 0 15px rgba(0,0,0,0.5);
            }
            .notch-left { left: -30px; } 
            .notch-right { right: -30px; }

            .header { padding: 15px 0; text-align: center; color: white; font-weight: 900; font-size: 0.85em; letter-spacing: 2px; }

            /* ÁREA BRANCA MAIS FINA E ELEGANTE */
            .white-area { 
                background: #fdfdfd; 
                margin: 0; /* Ocupa a largura toda para o recorte funcionar visualmente */
                display: flex; 
                padding: 25px 40px; 
                min-height: 200px; 
                border-top: 1px solid rgba(0,0,0,0.05);
                border-bottom: 1px solid rgba(0,0,0,0.05);
            }

            .col-left { flex: 1.5; border-right: 1.5px dashed #ccc; padding-right: 20px; display: flex; flex-direction: column; justify-content: center; }
            .col-right { flex: 1; padding-left: 25px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
            
            .label { color: #999; font-size: 0.55em; font-weight: 800; text-transform: uppercase; margin-bottom: 3px; }
            .value { font-size: 1.2em; font-weight: 900; color: var(--air-blue); margin-bottom: 12px; min-height: 1.2em; display: flex; flex-wrap: wrap; }
            
            #compass { display: inline-block; transition: transform 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275); color: var(--warning-gold); font-size: 1.6em; }
            
            .footer { padding: 15px 0 25px 0; display: flex; flex-direction: column; align-items: center; background: var(--air-blue); }
            .yellow-lines { width: 100%; height: 4px; border-top: 1px solid var(--warning-gold); border-bottom: 1px solid var(--warning-gold); margin-bottom: 15px; opacity: 0.7; }
            
            .status-msg { padding: 4px 10px; min-height: 1.6em; }
            .status-msg .letter-slot {
                color: var(--warning-gold); background: #000; margin: 0 1px; padding: 0 4px;
                border-radius: 2px; font-size: 0.8em; font-weight: 900; border: 1px solid #333;
            }

            .letter-slot { display: inline-block; min-width: 0.65em; text-align: center; position: relative; vertical-align: bottom; }
            .flapping { animation: flap-anim 0.06s ease-in-out; }
            @keyframes flap-anim { 0% { transform: scaleY(1); } 50% { transform: scaleY(0.5); opacity: 0.7; } 100% { transform: scaleY(1); } }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="notch notch-left"></div>
            <div class="notch notch-right"></div>
            
            <div class="header">SYSTEM RADAR BOARDING</div>
            
            <div class="white-area">
                <div class="col-left">
                    <div><div class="label">IDENT / CALLSIGN</div><div id="callsign" class="value"></div></div>
                    <div><div class="label">DISTANCE</div><div id="dist_body" class="value"></div></div>
                    <div><div class="label">ALTITUDE</div><div id="alt" class="value"></div></div>
                </div>
                <div class="col-right">
                    <div class="label">TYPE</div><div id="type_id" class="value">----</div>
                    <div class="label">BEARING</div><div class="value"><span id="compass">↑</span></div>
                    <div style="height:30px; width:100%; background:repeating-linear-gradient(90deg, #000, #000 1px, transparent 1px, transparent 5px); opacity: 0.1;"></div>
                </div>
            </div>

            <div class="footer">
                <div class="yellow-lines"></div>
                <div id="status" class="status-msg"></div>
            </div>
        </div>

        <script>
            // O restante do script permanece o mesmo da sua versão funcional
            // apenas ajustando as chamadas de efeito e timers conforme conversamos.
            let latAlvo = null, lonAlvo = null;
            let currentTarget = null;
            let statusIndex = 0;
            const chars = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/.:->";

            function updateWithEffect(id, newValue) {
                const container = document.getElementById(id);
                const newText = String(newValue).toUpperCase();
                while (container.childNodes.length < newText.length) {
                    const s = document.createElement("span"); s.className = "letter-slot"; s.innerHTML = "&nbsp;"; container.appendChild(s);
                }
                while (container.childNodes.length > newText.length) { container.removeChild(container.lastChild); }
                const slots = container.querySelectorAll('.letter-slot');
                newText.split('').forEach((targetChar, i) => {
                    const slot = slots[i];
                    if (slot.innerText === targetChar) return;
                    let cycles = 0;
                    const interval = setInterval(() => {
                        slot.innerText = chars[Math.floor(Math.random() * chars.length)];
                        slot.classList.add('flapping');
                        if (++cycles >= 10 + i) {
                            clearInterval(interval);
                            slot.innerText = targetChar === " " ? "\u00A0" : targetChar;
                            slot.classList.remove('flapping');
                        }
                    }, 60);
                });
            }

            window.onload = function() {
                updateWithEffect('callsign', 'SEARCHING');
                updateWithEffect('status', 'LOADING ATC...');
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude;
                    iniciarRadar();
                }, () => { alert("Favor permitir GPS"); });
                
                setInterval(() => {
                    if(!currentTarget) {
                        const envMsgs = ["RADAR SWEEP ACTIVE", "TEMP: 24C / SKY CLEAR", "VISIBILITY: 10KM+"];
                        updateWithEffect('status', envMsgs[statusIndex % envMsgs.length]);
                        statusIndex++;
                    } else {
                        const flightMsgs = [
                            `FLT: ${currentTarget.callsign}`,
                            `PATH: ${currentTarget.origin} > ${currentTarget.dest}`,
                            `SPEED: ${currentTarget.speed} KTS`,
                            "VISIBILITY: 10KM+"
                        ];
                        updateWithEffect('status', flightMsgs[statusIndex % flightMsgs.length]);
                        statusIndex++;
                    }
                }, 10000);
            };

            function iniciarRadar() { setInterval(executarBusca, 8000); executarBusca(); }

            function executarBusca() {
                if(!latAlvo) return;
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}&t=${Date.now()}`)
                .then(res => res.json()).then(data => {
                    if(data.found) {
                        currentTarget = data;
                        updateWithEffect('callsign', data.callsign);
                        updateWithEffect('type_id', data.type);
                        updateWithEffect('alt', data.alt_ft.toLocaleString() + " FT");
                        updateWithEffect('dist_body', data.dist + " KM");
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                    }
                });
            }
        </script>
    </body>
    </html>
    ''')

# O restante das rotas Python se mantém igual.









