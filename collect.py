import gzip, json, os, ssl, sys, time
import paho.mqtt.client as mqtt
OUT = sys.argv[1] if len(sys.argv) > 1 else "raw"
os.makedirs(OUT, exist_ok=True)
EVENTS = ["arr", "dep", "ars", "pde", "doo", "doc", "pas"]
state = {"hour": None, "fh": None, "n": 0}
def fh():
    h = time.strftime("%Y%m%dT%H", time.gmtime())
    if h != state["hour"]:
        if state["fh"]: state["fh"].close()
        state["fh"] = gzip.open(os.path.join(OUT, "hfp_%s.jsonl.gz" % h), "at"); state["hour"] = h
    return state["fh"]
def on_connect(c, u, f, rc, props=None):
    for e in EVENTS: c.subscribe("/hfp/v2/journey/ongoing/%s/#" % e, qos=0)
def on_message(c, u, m):
    fh().write(json.dumps({"t": m.topic, "r": round(time.time(), 3), "p": json.loads(m.payload)}, separators=(",", ":")) + "\n"); state["n"] += 1
c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
c.tls_set(cert_reqs=ssl.CERT_REQUIRED); c.on_connect = on_connect; c.on_message = on_message
c.reconnect_delay_set(1, 60); c.connect("mqtt.hsl.fi", 8883, keepalive=60)
dur = float(os.environ.get("DURATION_S", "0"))
c.loop_start(); t0 = time.time()
while dur == 0 or time.time() - t0 < dur:
    time.sleep(30); print(time.strftime("%H:%M:%S"), "messages", state["n"], flush=True)
c.loop_stop(); state["fh"].close()
