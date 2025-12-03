import os
import json
import math
import pandas as pd
from datetime import datetime
from arcgis.gis import GIS
from arcgis.features import FeatureLayer

# --- Configuration ---
ARCGIS_USERNAME = os.environ.get("ARCGIS_USERNAME")
ARCGIS_PASSWORD = os.environ.get("ARCGIS_PASSWORD")
ARCGIS_URL = "https://www.arcgis.com"

PROJECT_URL = "https://services.arcgis.com/FsUQjymePMCjUecp/arcgis/rest/services/ICA_bbw/FeatureServer/0"
OBJECT_URL  = "https://services.arcgis.com/FsUQjymePMCjUecp/arcgis/rest/services/ICA_bbw/FeatureServer/9"
TASK_URL    = "https://services.arcgis.com/FsUQjymePMCjUecp/arcgis/rest/services/ICA_bbw/FeatureServer/6"
WS_URL      = "https://services.arcgis.com/FsUQjymePMCjUecp/arcgis/rest/services/ICA_bbw/FeatureServer/5"

def fl_to_df(url):
    try:
        fl = FeatureLayer(url)
        q = fl.query(where="1=1", out_fields="*")
        feats = q.features or []
        return pd.DataFrame([f.attributes for f in feats]) if feats else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def to_dt_ms(val):
    try:
        if val is None or (isinstance(val, float) and math.isnan(val)): return pd.NaT
        return pd.to_datetime(int(val), unit="ms", errors="coerce")
    except: return pd.NaT

def safe_date_str(dt):
    return dt.strftime("%Y-%m-%d") if pd.notna(dt) else "2025-01-01"

def get_color(level):
    colors = {"project": "#4CAF50", "object": "#2196F3", "task": "#FC0BB3", "ws": "#FF9800", "delayed": "#F44336"}
    return colors.get(level, "#9E9E9E")

def day_diff(d1, d2):
    if pd.isna(d1) or pd.isna(d2): return 1
    return max(1, (d2.normalize() - d1.normalize()).days)

def parse_dependencies(val):
    if pd.isna(val) or val == "": return []
    return [x.strip() for x in str(val).split(";") if x.strip()]

# --- Main Logic ---
def generate_gantt():
    print("\n[MODULE] Starting Gantt_Chart generation...")
    
    # Optional Login (Good practice, even if reading public layers)
    if ARCGIS_USERNAME and ARCGIS_PASSWORD:
        try:
            GIS(ARCGIS_URL, ARCGIS_USERNAME, ARCGIS_PASSWORD)
        except Exception as e:
            print(f"⚠️ Login warning (continuing anonymously if allowed): {e}")

    try:
        print("   📥 Fetching fresh data...")
        project_pd = fl_to_df(PROJECT_URL)
        object_pd  = fl_to_df(OBJECT_URL)
        task_pd    = fl_to_df(TASK_URL)
        ws_pd      = fl_to_df(WS_URL)

        # Date Conversions
        for df, cols in [
            (object_pd, ["ObjStartDate", "ObjEndDate", "ObjActStartDate", "ObjActEndDate"]),
            (task_pd, ["TaskStartDate", "TaskEndDate", "TaskActStartDate", "TaskActEndDate"]),
            (ws_pd, ["WsStartDate", "WsEndDate", "WsActStartDate", "WsActEndDate"])
        ]:
            if not df.empty:
                for c in cols:
                    if c in df.columns: df[c] = df[c].apply(to_dt_ms)

        gantt_data = []
        gantt_links = []
        link_cnt = 1

        # --- Nodes Generation ---
        for _, prj in project_pd.iterrows():
            prj_id = prj["PrjID"]
            objs = object_pd[object_pd["O_PrjID"] == prj_id] if not object_pd.empty else pd.DataFrame()
            
            # Simple Project Node
            start = objs["ObjStartDate"].min() if not objs.empty else pd.NaT
            end   = max(objs["ObjActEndDate"].max(), objs["ObjEndDate"].max()) if not objs.empty else pd.NaT
            
            gantt_data.append({
                "id": prj_id, "text": prj.get("PrjName", prj_id),
                "start_date": safe_date_str(start), "duration": day_diff(start, end),
                "open": True, "color": get_color("project"), "progress": 0.5 
            })

            # Objects
            for _, obj in objs.iterrows():
                obj_id = obj["ObjID"]
                s_act, e_act = obj.get("ObjActStartDate"), obj.get("ObjActEndDate")
                s_plan = obj.get("ObjStartDate")
                
                # Check Delay
                color = get_color("object")
                is_late = False
                if all(pd.notna(x) for x in [s_plan, e_plan, s_act, e_act]):
                    delay_start_days = (s_act.normalize() - s_plan.normalize()).days
                    delay_end_days = (e_act.normalize() - e_plan.normalize()).days
                    if delay_start_days >= 1 and delay_end_days >= 1:
                        color = get_color("delayed")

                gantt_data.append({
                    "id": obj_id, "text": obj.get("ObjName", obj_id),
                    "start_date": safe_date_str(s_act or s_plan),
                    "duration": day_diff(s_act or s_plan, e_act or obj.get("ObjEndDate")),
                    "parent": prj_id, "color": color, "progress": 0.0
                })

                # Tasks
                t_group = task_pd[task_pd["T_ObjID"] == obj_id] if not task_pd.empty else pd.DataFrame()
                for _, t in t_group.iterrows():
                    t_id = t["TaskID"]
                    ts, te = t.get("TaskActStartDate") or t.get("TaskStartDate"), t.get("TaskActEndDate") or t.get("TaskEndDate")
                    gantt_data.append({
                        "id": t_id, "text": t.get("TaskName", t_id),
                        "start_date": safe_date_str(ts), "duration": day_diff(ts, te),
                        "parent": obj_id, "color": get_color("task")
                    })

                # WS
                w_group = ws_pd[ws_pd["Ws_ObjID"] == obj_id] if not ws_pd.empty else pd.DataFrame()
                for _, w in w_group.iterrows():
                    w_id = w.get("WsID")
                    ws, we = w.get("WsActStartDate") or w.get("WsStartDate"), w.get("WsActEndDate") or w.get("WsEndDate")
                    gantt_data.append({
                        "id": w_id, "text": w.get("WsName", w_id),
                        "start_date": safe_date_str(ws), "duration": day_diff(ws, we),
                        "parent": obj_id, "color": get_color("ws")
                    })

        # --- Links Generation ---
        # Task Links
        if not task_pd.empty:
            for _, row in task_pd.iterrows():
                target = row.get("TaskID")
                for src in parse_dependencies(row.get("T_PreTaskID")) + parse_dependencies(row.get("T_PreWsID")):
                    gantt_links.append({"id": f"L{link_cnt}", "source": src, "target": target, "type": "0"})
                    link_cnt += 1
        # WS Links
        if not ws_pd.empty:
            for _, row in ws_pd.iterrows():
                target = row.get("WsID")
                for src in parse_dependencies(row.get("Ws_PreTaskID")) + parse_dependencies(row.get("Ws_PreWsID")):
                    gantt_links.append({"id": f"L{link_cnt}", "source": src, "target": target, "type": "0"})
                    link_cnt += 1

        # Export
        os.makedirs("docs", exist_ok=True)
        payload = {"generated_at": datetime.utcnow().isoformat() + "Z", "data": gantt_data, "links": gantt_links}
        with open("docs/data.json", "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        
        print(f"   ✅ JSON generated: {len(gantt_data)} items.")
        return True

    except Exception as e:
        print(f"❌ Error in Gantt Generation: {e}")
        return False

if __name__ == "__main__":
    generate_gantt()
