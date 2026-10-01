import csv, glob, gzip, hashlib, hmac, json, os, sys, zipfile, collections
import pandas as pd
EV = {"dep", "ars"}
def read_hour(f):
    fh = gzip.open(f, "rt")
    while True:
        try: l = fh.readline()
        except (EOFError, OSError): return
        if not l: return
        try: d = json.loads(l)
        except Exception: continue
        parts = d["t"].split("/")
        if len(parts) < 7 or parts[5] not in EV: continue
        p = next(iter(d["p"].values()))
        if p.get("stop") is None or p.get("route") is None or p.get("veh") is None or p.get("start") is None: continue
        yield (p["oday"], str(p["route"]), int(p["dir"]), p["start"], int(p["oper"]), int(p["veh"]), parts[6], parts[5], int(p["stop"]), p["tst"], p.get("ttdep") if parts[5] == "dep" else p.get("ttarr"))
COLS = ["oday", "route", "dir", "start", "oper", "veh", "mode", "ev", "stop", "tst", "tt"]
def build(raw_dir, oday, start, cut):
    rows = []
    for f in sorted(glob.glob(os.path.join(raw_dir, "hfp_*.jsonl.gz"))):
        rows += [r for r in read_hour(f) if r[0] == oday]
    df = pd.DataFrame(rows, columns=COLS)
    if df.empty: return None, None
    df["t"] = pd.to_datetime(df.tst, utc=True).astype("int64") // 10**6 / 1000.0
    df = df[(df.t >= start) & (df.t < cut)].copy()
    df["s"] = pd.to_datetime(df.tt, utc=True, errors="coerce").astype("int64") // 10**6 / 1000.0
    df.loc[df.tt.isna(), "s"] = float("nan")
    df = df.sort_values(["t", "stop", "ev"], kind="mergesort").drop_duplicates(["oday", "route", "dir", "start", "oper", "veh", "ev", "stop"], keep="first")
    key = ["oday", "route", "dir", "start", "oper", "veh", "mode"]
    ev = df.pivot_table(index=key + ["stop"], columns="ev", values="t", aggfunc="min").reset_index()
    sc = df.pivot_table(index=key + ["stop"], columns="ev", values="s", aggfunc="min").reset_index().rename(columns={"dep": "s_dep", "ars": "s_ars"})
    ev = ev.merge(sc, on=key + ["stop"], how="left")
    ev["tref"] = ev["dep"].fillna(ev.get("ars"))
    ev["sref"] = ev["s_dep"].fillna(ev.get("s_ars")) if "s_dep" in ev else ev.get("s_ars")
    ev = ev.sort_values(key + ["tref", "stop"], kind="mergesort")
    ev["seq"] = ev.groupby(key).cumcount()
    J = ev.groupby(key).agg(t0=("tref", "min"), t1=("tref", "max"), n_stops=("stop", "size"), first_stop=("stop", "first"), last_stop=("stop", "last"),
                            s1=("sref", "last")).reset_index()
    J = J[(J.n_stops >= 3) & J.s1.notna()].sort_values(["t0", "oper", "veh", "route", "start"], kind="mergesort").reset_index(drop=True)
    J["next_idx"] = -1
    for (o, v), g in J.groupby(["oper", "veh"]):
        idx = g.sort_values(["t0", "start", "route"], kind="mergesort").index.tolist()
        for a, b in zip(idx, idx[1:]):
            if J.at[b, "t0"] - J.at[a, "t1"] < 3 * 3600 and J.at[b, "t0"] >= J.at[a, "t1"] - 600: J.at[a, "next_idx"] = b
    return J, ev

if __name__ == '__main__':
    KEY = open("SECRET_DO_NOT_SHARE.txt").read().strip().encode()
    def kid(prefix, *parts): return prefix + hmac.new(KEY, "|".join(map(str, parts)).encode(), hashlib.sha256).hexdigest()[:10]
    raw_dir, gtfs_zip, oday, start_utc, cut_utc = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), float(sys.argv[5])
    OUT = sys.argv[6] if len(sys.argv) > 6 else "release"; os.makedirs(OUT, exist_ok=True)
    J, ev = build(raw_dir, oday, start_utc, cut_utc)
    J = J[J["mode"] == "bus"].copy()
    z = zipfile.ZipFile(gtfs_zip); ALL = pd.read_csv(z.open("stops.txt"))
    J = J[J.first_stop.isin(set(ALL.stop_id)) & J.last_stop.isin(set(ALL.stop_id))].copy()
    mid = pd.Timestamp(oday, tz="Europe/Helsinki").timestamp()
    J["journey_id"] = [kid("j_", r.oday, r.route, r.dir, r.start, r.oper, r.veh) for r in J.itertuples()]
    J["vehicle_id"] = [kid("v_", r.oper, r.veh) for r in J.itertuples()]
    nxt = {}
    for i, r in J.iterrows():
        b = r.next_idx
        nxt[r.journey_id] = J.at[b, "journey_id"] if b in J.index and b >= 0 else "none"
    out = pd.DataFrame({"journey_id": J.journey_id, "vehicle_id": J.vehicle_id, "operator": ["o%d" % x for x in J.oper], "route": ["r" + str(x) for x in J.route], "direction": J.dir,
                        "scheduled_start": J.start, "first_stop": ["s%d" % x for x in J.first_stop], "last_stop": ["s%d" % x for x in J.last_stop], "start_s": (J.t0 - mid).round().astype(int),
                        "end_s": (J.t1 - mid).round().astype(int), "n_stops": J.n_stops, "scheduled_end_s": (J.s1 - mid).round().astype(int)}).sort_values("journey_id")
    out.to_csv(os.path.join(OUT, "journeys.csv"), index=False)
    pd.DataFrame({"journey_id": list(nxt), "next_journey_id": list(nxt.values())}).sort_values("journey_id").to_csv(os.path.join(OUT, "next_trips.csv"), index=False)
    st = ALL
    used = {int(x[1:]) for x in set(out.first_stop) | set(out.last_stop)}
    st = st[st.stop_id.isin(used)][["stop_id", "stop_name", "stop_lat", "stop_lon"]].rename(columns={"stop_name": "name", "stop_lat": "lat", "stop_lon": "lon"}).sort_values("stop_id")
    st["stop_id"] = ["s%d" % x for x in st.stop_id]
    st.to_csv(os.path.join(OUT, "stops.csv"), index=False)
    print("journeys", len(out), "vehicles", out.vehicle_id.nunique(), "with next", sum(v != "none" for v in nxt.values()), "stops", len(st), "missing stop coords", len(used - {int(x[1:]) for x in st.stop_id}))
    print(out.operator.value_counts().to_dict())
