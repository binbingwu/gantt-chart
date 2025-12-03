import os
import pandas as pd
from collections import defaultdict, deque
from datetime import datetime
from arcgis.gis import GIS
from arcgis.features import FeatureLayer

# --- Configuration ---
ARCGIS_URL = "https://www.arcgis.com"
# Credentials from Environment Variables
ARCGIS_USERNAME = os.environ.get("ARCGIS_USERNAME")
ARCGIS_PASSWORD = os.environ.get("ARCGIS_PASSWORD")

# Feature Layer URLs
TASK_URL = "https://services.arcgis.com/FsUQjymePMCjUecp/arcgis/rest/services/ICA_bbw/FeatureServer/6"
WS_URL   = "https://services.arcgis.com/FsUQjymePMCjUecp/arcgis/rest/services/ICA_bbw/FeatureServer/5"

class ScheduleEngine:
    def __init__(self, nodes_df, task_fl, ws_fl):
        self.nodes_df = nodes_df
        self.task_fl = task_fl
        self.ws_fl = ws_fl
        self.updates_task = []
        self.updates_ws = []
        
        self.node_map = {row["NodeID"]: row for _, row in nodes_df.iterrows()}
        self.adj = defaultdict(list)
        self.rev_adj = defaultdict(list)

    def parse_and_clean_dependencies(self):
        """Identifies and removes time-conflicting dependencies (Time Travel prevention)."""
        print("🧹 Cleaning time-conflicting dependencies...")
        for index, row in self.nodes_df.iterrows():
            curr_id = row["NodeID"]
            curr_plan_start = row["PlanStart"]
            raw_pre_ids = row["PreIDs"]
            valid_pre_ids = []
            dirty = False 

            for pid in raw_pre_ids:
                if pid not in self.node_map: continue
                
                pre_node = self.node_map[pid]
                pre_plan_start = pre_node["PlanStart"]

                # Conflict Check: Predecessor Plan Start > Current Plan Start
                if pre_plan_start and curr_plan_start and pre_plan_start > curr_plan_start:
                    print(f"   ✂️ Removing Conflict: {pid} -> {curr_id}")
                    dirty = True
                else:
                    valid_pre_ids.append(pid)
                    self.adj[pid].append(curr_id)
                    self.rev_adj[curr_id].append(pid)
            
            if dirty:
                self.nodes_df.at[index, "PreIDs"] = valid_pre_ids
                self._queue_dependency_update(row, valid_pre_ids)

    def _queue_dependency_update(self, row, valid_ids):
        """Queues clean dependency strings for upload."""
        new_pre_tasks = [x for x in valid_ids if not x.startswith("WS_")]
        new_pre_ws = [x for x in valid_ids if x.startswith("WS_")]
        
        upd = {"attributes": {"OBJECTID": row["OBJECTID"]}}
        if row["Type"] == "Task":
            upd["attributes"]["T_PreTaskID"] = ";".join(new_pre_tasks)
            upd["attributes"]["T_PreWsID"] = ";".join(new_pre_ws)
            self.updates_task.append(upd)
        else:
            upd["attributes"]["Ws_PreTaskID"] = ";".join(new_pre_tasks)
            upd["attributes"]["Ws_PreWsID"] = ";".join(new_pre_ws)
            self.updates_ws.append(upd)

    def propagate_delays(self):
        """DAG topological sort and delay propagation."""
        print("🔄 Calculating schedule propagation...")
        in_degree = {u: 0 for u in self.node_map}
        for u in self.adj:
            for v in self.adj[u]:
                in_degree[v] += 1
        
        queue = deque([u for u in in_degree if in_degree[u] == 0])
        topo_order = []

        while queue:
            u = queue.popleft()
            topo_order.append(u)
            for v in self.adj[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)
        
        for curr_id in topo_order:
            curr_node = self.node_map[curr_id]
            curr_act_start = curr_node["ActStart"]
            curr_plan_start = curr_node["PlanStart"]
            
            # Determine Duration
            if pd.notna(curr_node["ActEnd"]) and pd.notna(curr_act_start):
                duration = curr_node["ActEnd"] - curr_act_start
            else:
                duration = curr_node["PlanEnd"] - curr_node["PlanStart"]

            # Check upstream constraints
            predecessors = self.rev_adj[curr_id]
            max_pre_finish = None
            if predecessors:
                valid_finishes = [self.node_map[p]["ActEnd"] for p in predecessors if pd.notna(self.node_map[p]["ActEnd"])]
                if valid_finishes:
                    max_pre_finish = max(valid_finishes)

            # Calculate New Start
            new_act_start = curr_plan_start
            if max_pre_finish and max_pre_finish > new_act_start:
                new_act_start = max_pre_finish
            
            # Respect Manual Input if it's even later
            if pd.notna(curr_act_start) and curr_act_start > new_act_start:
                new_act_start = curr_act_start

            new_act_end = new_act_start + duration

            # Update if changed (> 60s)
            old_ts = curr_node["ActStart"].timestamp() if pd.notna(curr_node["ActStart"]) else 0
            if abs(new_act_start.timestamp() - old_ts) > 60:
                print(f"   🌊 Cascade: {curr_id} pushed -> {new_act_start}")
                self.node_map[curr_id]["ActStart"] = new_act_start
                self.node_map[curr_id]["ActEnd"]   = new_act_end
                
                upd = {"attributes": {"OBJECTID": curr_node["OBJECTID"]}}
                start_ms = int(new_act_start.timestamp() * 1000)
                end_ms   = int(new_act_end.timestamp() * 1000)
                
                if curr_node["Type"] == "Task":
                    upd["attributes"]["TaskActStartDate"] = start_ms
                    upd["attributes"]["TaskActEndDate"] = end_ms
                    self.updates_task.append(upd)
                else:
                    upd["attributes"]["WsActStartDate"] = start_ms
                    upd["attributes"]["WsActEndDate"] = end_ms
                    self.updates_ws.append(upd)

    def commit_updates(self):
        """Batched commits to ArcGIS."""
        if self.updates_task:
            try:
                self.task_fl.edit_features(updates=self.updates_task)
                print(f"   ✅ Committed {len(self.updates_task)} Task updates.")
            except Exception as e:
                print(f"   ❌ Task Update Failed: {e}")

        if self.updates_ws:
            try:
                self.ws_fl.edit_features(updates=self.updates_ws)
                print(f"   ✅ Committed {len(self.updates_ws)} WS updates.")
            except Exception as e:
                print(f"   ❌ WS Update Failed: {e}")

# --- Utilities ---
def fl_to_df(url):
    try:
        fl = FeatureLayer(url)
        q = fl.query(where="1=1", out_fields="*")
        return pd.DataFrame([f.attributes for f in q.features]) if q.features else pd.DataFrame()
    except Exception as e:
        print(f"❌ Fetch Error: {e}")
        return pd.DataFrame()

def parse_dependencies(val):
    if pd.isna(val) or val == "": return []
    return [x.strip() for x in str(val).split(";") if x.strip()]

def ms_to_datetime(ms):
    if pd.isna(ms) or ms == "": return None
    try: return datetime.fromtimestamp(ms / 1000.0)
    except: return None

# --- Main Entry Point ---
def run_scheduler():
    print("\n[MODULE] Starting Day_Dynamic_Computing...")
    
    if not ARCGIS_USERNAME or not ARCGIS_PASSWORD:
        print("❌ Error: Credentials not found.")
        return False

    try:
        gis = GIS(ARCGIS_URL, ARCGIS_USERNAME, ARCGIS_PASSWORD)
        task_fl = FeatureLayer(TASK_URL)
        ws_fl = FeatureLayer(WS_URL)
        
        task_df = fl_to_df(TASK_URL)
        ws_df   = fl_to_df(WS_URL)
        
        if task_df.empty and ws_df.empty:
            print("⚠️ No data found.")
            return True # Not an error, just empty

        # Data Standardization
        all_nodes_list = []
        # (Processing Task DF)
        if not task_df.empty:
            for _, row in task_df.iterrows():
                p_start = ms_to_datetime(row.get("TaskStartDate"))
                p_end   = ms_to_datetime(row.get("TaskEndDate"))
                a_start = ms_to_datetime(row.get("TaskActStartDate")) or p_start
                a_end   = ms_to_datetime(row.get("TaskActEndDate")) or p_end
                
                all_nodes_list.append({
                    "NodeID": str(row["TaskID"]).strip(),
                    "OBJECTID": row["OBJECTID"],
                    "Type": "Task",
                    "ComCode": str(row.get("T_ComCode", "")).strip(),
                    "PlanStart": p_start, "PlanEnd": p_end, "ActStart": a_start, "ActEnd": a_end,
                    "PreIDs": parse_dependencies(row.get("T_PreTaskID")) + parse_dependencies(row.get("T_PreWsID"))
                })
        # (Processing WS DF)
        if not ws_df.empty:
            for _, row in ws_df.iterrows():
                ws_id = str(row.get("WsID", f"WS_{row['OBJECTID']}")).strip()
                p_start = ms_to_datetime(row.get("WsStartDate"))
                p_end   = ms_to_datetime(row.get("WsEndDate"))
                a_start = ms_to_datetime(row.get("WsActStartDate")) or p_start
                a_end   = ms_to_datetime(row.get("WsActEndDate")) or p_end

                all_nodes_list.append({
                    "NodeID": ws_id,
                    "OBJECTID": row["OBJECTID"],
                    "Type": "WS",
                    "ComCode": str(row.get("Ws_ComCode", "")).strip(),
                    "PlanStart": p_start, "PlanEnd": p_end, "ActStart": a_start, "ActEnd": a_end,
                    "PreIDs": parse_dependencies(row.get("Ws_PreTaskID")) + parse_dependencies(row.get("Ws_PreWsID"))
                })

        full_df = pd.DataFrame(all_nodes_list)
        full_df = full_df[full_df["ComCode"] != ""]
        full_df = full_df.dropna(subset=["PlanStart", "PlanEnd"])
        
        unique_codes = full_df["ComCode"].unique()
        for code in unique_codes:
            print(f"   Processing Group: {code}")
            group_df = full_df[full_df["ComCode"] == code].copy()
            engine = ScheduleEngine(group_df, task_fl, ws_fl)
            engine.parse_and_clean_dependencies()
            engine.propagate_delays()
            engine.commit_updates()
            
        return True

    except Exception as e:
        print(f"❌ Critical Error in Scheduler: {e}")
        return False

if __name__ == "__main__":
    run_scheduler()
