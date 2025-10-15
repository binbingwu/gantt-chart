import os
import json
import math
from datetime import datetime
import pandas as pd

from arcgis.gis import GIS
from arcgis.features import FeatureLayer
# login in ArcGIS Online
gis = GIS("https://www.arcgis.com", os.getenv("ARCGIS_USERNAME"), os.getenv("ARCGIS_PASSWORD"))

PROJECT_URL = "https://services.arcgis.com/FsUQjymePMCjUecp/arcgis/rest/services/ICA_PM_Test/FeatureServer/0"
OBJECT_URL  = "https://services.arcgis.com/FsUQjymePMCjUecp/arcgis/rest/services/ICA_PM_Test/FeatureServer/2"
TASK_URL    = "https://services.arcgis.com/FsUQjymePMCjUecp/arcgis/rest/services/ICA_PM_Test/FeatureServer/4"



# Utility functions

def fl_to_df(url: str) -> pd.DataFrame:
    """Query a FeatureLayer and convert it to a pandas DataFrame"""
    fl = FeatureLayer(url)
    q = fl.query(where="1=1", out_fields="*")
    feats = q.features or []
    return pd.DataFrame([f.attributes for f in feats]) if feats else pd.DataFrame()


def to_dt_ms(val):
    """Convert milliseconds timestamp to pandas datetime"""
    try:
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return pd.NaT
        return pd.to_datetime(int(val), unit="ms", errors="coerce")
    except Exception:
        return pd.NaT


def safe_date_str(dt):
    """Return a formatted date string (default to 2025-01-01 if NaT)"""
    return dt.strftime("%Y-%m-%d") if pd.notna(dt) else "2025-01-01"


def get_color(level: str) -> str:
    """Color mapping by task level"""
    colors = {
        "project": "#4CAF50",  # green
        "object": "#2196F3",   # blue
        "task": "#FFEB3B",     # yellow
        "delayed": "#F44336"   # red
    }
    return colors.get(level, "#9E9E9E")


def same_day(d1, d2):
    """Compare only year, month, and day"""
    if pd.isna(d1) or pd.isna(d2):
        return False
    return (d1.year == d2.year) and (d1.month == d2.month) and (d1.day == d2.day)


def day_diff(d1, d2):
    """Calculate day difference between two dates (min = 1)"""
    if pd.isna(d1) or pd.isna(d2):
        return 1
    return max(1, (d2.normalize() - d1.normalize()).days)



#  Progress calculation

def compute_progress_task(row: pd.Series) -> float:
    """If TaskStatus == 3 → complete"""
    try:
        return 1.0 if int(row.get("TaskStatus", 0) or 0) == 3 else 0.0
    except Exception:
        return 0.0


def compute_progress_object(obj_id: str, task_df: pd.DataFrame) -> float:
    """Object progress = average completion rate of its tasks"""
    related = task_df[task_df["T_ObjID"] == obj_id]
    if related.empty:
        return 0.0
    return related.apply(compute_progress_task, axis=1).mean()


def compute_progress_project(prj_id: str, obj_df: pd.DataFrame, task_df: pd.DataFrame) -> float:
    """Project progress = average completion rate of its objects"""
    related_objs = obj_df[obj_df["O_PrjID"] == prj_id]
    if related_objs.empty:
        return 0.0
    vals = [compute_progress_object(o["ObjID"], task_df) for _, o in related_objs.iterrows()]
    return sum(vals) / len(vals)


#  Main logic

def main():
    print("🔄 Fetching ArcGIS data...")

    project_pd = fl_to_df(PROJECT_URL)
    object_pd  = fl_to_df(OBJECT_URL)
    task_pd    = fl_to_df(TASK_URL)

    # Convert timestamps
    for c in ["Obj_StartDate", "Obj_EndDate", "Obj_ActStartDa", "Obj_ActEndDa"]:
        if c in object_pd.columns:
            object_pd[c] = object_pd[c].apply(to_dt_ms)
        else:
            print(f"⚠️ Missing column: {c}")
    for c in ["Task_StartDate", "Task_EndDate"]:
        if c in task_pd.columns:
            task_pd[c] = task_pd[c].apply(to_dt_ms)

    gantt_data = []
    gantt_links = []
    link_id = 1

    for _, prj in project_pd.iterrows():
        prj_id = prj["PrjID"]
        prj_name = prj.get("PrjName", prj_id)
        progress = compute_progress_project(prj_id, object_pd, task_pd)
        objs = object_pd[object_pd["O_PrjID"] == prj_id]

        start = objs["Obj_StartDate"].min() if not objs.empty else pd.NaT
        end   = max(objs["Obj_ActEndDa"].max(), objs["Obj_EndDate"].max()) if not objs.empty else pd.NaT
        duration = day_diff(start, end)

        gantt_data.append({
            "id": prj_id,
            "text": prj_name,
            "start_date": safe_date_str(start),
            "duration": duration,
            "progress": round(float(progress), 2),
            "open": True,
            "color": get_color("project")
        })

        prev_obj_blue = None
        for _, obj in objs.sort_values("Obj_StartDate").iterrows():
            obj_id = obj["ObjID"]
            obj_name = obj.get("ObjName", obj_id)
            s_plan, e_plan = obj.get("Obj_StartDate"), obj.get("Obj_EndDate")
            s_act, e_act = obj.get("Obj_ActStartDa"), obj.get("Obj_ActEndDa")

            has_all_dates = all(pd.notna(x) for x in [s_plan, e_plan, s_act, e_act])
            print(obj_name, s_plan, e_plan, s_act, e_act)

            if has_all_dates:
                # ✅ Delay only if actual start is 1 or more days later than planned
                is_late = False
                try:
                    delay_start_days = (s_act.normalize() - s_plan.normalize()).days if (pd.notna(s_act) and pd.notna(s_plan)) else 0
                    if delay_start_days >= 1:
                        is_late = True
                    # If actual end < planned start → not considered delay
                    if pd.notna(e_act) and pd.notna(s_plan) and (e_act < s_plan):
                        is_late = False
                except Exception:
                    is_late = False

                if is_late:
                    # 🟥 Red = planned task (delayed)
                    gantt_data.append({
                        "id": f"{obj_id}_plan",
                        "text": f"{obj_name} (Planned)",
                        "start_date": safe_date_str(s_plan),
                        "duration": day_diff(s_plan, e_plan),
                        "parent": prj_id,
                        "color": get_color("delayed")
                    })
                    # 🟦 Blue = actual
                    gantt_data.append({
                        "id": f"{obj_id}_actual",
                        "text": f"{obj_name} (Actual)",
                        "start_date": safe_date_str(s_act),
                        "duration": day_diff(s_act, e_act),
                        "parent": prj_id,
                        "progress": round(float(compute_progress_object(obj_id, task_pd)), 2),
                        "open": True,
                        "color": get_color("object")
                    })
                    # 🟥→🟦 Start-to-Start link
                    gantt_links.append({
                        "id": f"link_{link_id}",
                        "source": f"{obj_id}_plan",
                        "target": f"{obj_id}_actual",
                        "type": "1"
                    })
                    link_id += 1

                    # Link between blue bars
                    if prev_obj_blue:
                        gantt_links.append({
                            "id": f"link_{link_id}",
                            "source": prev_obj_blue,
                            "target": f"{obj_id}_actual",
                            "type": "0"
                        })
                        link_id += 1
                    prev_obj_blue = f"{obj_id}_actual"

                    # 🟨 Yellow subtasks (under blue actual)
                    task_group = task_pd[task_pd["T_ObjID"] == obj_id].sort_values("Task_StartDate")
                    prev_task = None
                    for _, t in task_group.iterrows():
                        t_id = t["TaskID"]
                        s_t, e_t = t.get("Task_StartDate"), t.get("Task_EndDate")
                        gantt_data.append({
                            "id": t_id,
                            "text": t.get("TaskName", t_id),
                            "start_date": safe_date_str(s_t),
                            "duration": day_diff(s_t, e_t),
                            "parent": f"{obj_id}_actual",
                            "color": get_color("task")
                        })
                        if prev_task:
                            gantt_links.append({
                                "id": f"link_{link_id}",
                                "source": prev_task,
                                "target": t_id,
                                "type": "0"
                            })
                            link_id += 1
                        prev_task = t_id

                else:
                    # 🔵 Normal (no delay)
                    gantt_data.append({
                        "id": obj_id,
                        "text": obj_name,
                        "start_date": safe_date_str(s_act or s_plan),
                        "duration": day_diff(s_act or s_plan, e_act or e_plan),
                        "parent": prj_id,
                        "progress": round(float(compute_progress_object(obj_id, task_pd)), 2),
                        "open": True,
                        "color": get_color("object")
                    })
                    if prev_obj_blue:
                        gantt_links.append({
                            "id": f"link_{link_id}",
                            "source": prev_obj_blue,
                            "target": obj_id,
                            "type": "0"
                        })
                        link_id += 1
                    prev_obj_blue = obj_id

                    # 🟨 Yellow subtasks
                    task_group = task_pd[task_pd["T_ObjID"] == obj_id].sort_values("Task_StartDate")
                    prev_task = None
                    for _, t in task_group.iterrows():
                        t_id = t["TaskID"]
                        s_t, e_t = t.get("Task_StartDate"), t.get("Task_EndDate")
                        gantt_data.append({
                            "id": t_id,
                            "text": t.get("TaskName", t_id),
                            "start_date": safe_date_str(s_t),
                            "duration": day_diff(s_t, e_t),
                            "parent": obj_id,
                            "color": get_color("task")
                        })
                        if prev_task:
                            gantt_links.append({
                                "id": f"link_{link_id}",
                                "source": prev_task,
                                "target": t_id,
                                "type": "0"
                            })
                            link_id += 1
                        prev_task = t_id

            else:
                # ❗ Missing date fields → use planned dates (blue)
                gantt_data.append({
                    "id": obj_id,
                    "text": obj_name,
                    "start_date": safe_date_str(s_plan),
                    "duration": day_diff(s_plan, e_plan),
                    "parent": prj_id,
                    "progress": round(float(compute_progress_object(obj_id, task_pd)), 2),
                    "open": True,
                    "color": get_color("object")
                })
                if prev_obj_blue:
                    gantt_links.append({
                        "id": f"link_{link_id}",
                        "source": prev_obj_blue,
                        "target": obj_id,
                        "type": "0"
                    })
                    link_id += 1
                prev_obj_blue = obj_id

                # 🟨 Yellow subtasks
                task_group = task_pd[task_pd["T_ObjID"] == obj_id].sort_values("Task_StartDate")
                prev_task = None
                for _, t in task_group.iterrows():
                    t_id = t["TaskID"]
                    s_t, e_t = t.get("Task_StartDate"), t.get("Task_EndDate")
                    gantt_data.append({
                        "id": t_id,
                        "text": t.get("TaskName", t_id),
                        "start_date": safe_date_str(s_t),
                        "duration": day_diff(s_t, e_t),
                        "parent": obj_id,
                        "color": get_color("task")
                    })
                    if prev_task:
                        gantt_links.append({
                            "id": f"link_{link_id}",
                            "source": prev_task,
                            "target": t_id,
                            "type": "0"
                        })
                        link_id += 1
                    prev_task = t_id

    
    # Export JSON for Gantt chart

    os.makedirs("site", exist_ok=True)
    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "data": gantt_data,
        "links": gantt_links
    }
    with open("site/data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"✅ Wrote site/data.json with {len(gantt_data)} tasks and {len(gantt_links)} links.")


if __name__ == "__main__":
    main()