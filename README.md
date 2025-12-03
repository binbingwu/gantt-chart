# 📅 ArcGIS Dynamic Schedule & Automated Gantt Visualization

📘 **Pipeline:**  
ArcGIS Feature Layer ⇄ Logic Cleaning & DAG Scheduling → generate docs/data.json → visualize on GitHub Pages.

---

# 📖 Introduction

This system is an automated controller for complex construction schedules. It ensures data stored in ArcGIS is logically sound and visually accessible.

- **Clean:** Automatically removes "time-travel" paradoxes (predecessor > successor).  
- **Calculate:** Propagates delays downstream using DAG (Directed Acyclic Graph) logic.  
- **Visualize:** Generates a hierarchical Gantt chart for the project website.

---

# 🧱 Repository Structure

ArcGIS_Scheduler/
│
├── Auto_Workflow.py # 🎮 Orchestrator: Master Controller (Entry Point)
├── Day_Dynamic_Computing.py # ⚙️ Engine: Logic Cleaning & DAG Calculation
├── Gantt_Chart.py # 📊 Visualizer: JSON Generator
├── docs/
│ ├── index.html # Frontend visualization
│ └── data.json # Generated Gantt data (Do not edit manually)
└── .github/
└── workflows/
└── schedule.yml # 🤖 Automation: Daily Trigger (02:00 UTC)

yaml
复制代码

---

# 🗺️ Architecture / Data Flow

GitHub Actions (Daily Trigger)
│
▼
[ Auto_Workflow.py ] ──(Safety Check)──┐
│ │
├─► Step 1: Compute ──────────►│
│ ▼
│ { Day_Dynamic_Computing.py }
│ │
│ (Read/Write Sync - Clean Logic)
│ ▼
│ [( ArcGIS Feature Layers )]
│ ▲
├─► Step 2: Generate ──────────┘
│ │
│ ▼
│ { Gantt_Chart.py } ──(Read Only)──► docs/data.json
│ │
└────────────────────────────────────────────┼──► Commit & Push
│
▼
GitHub Pages / Web UI

yaml
复制代码

---

# ⚡ Quick Start (Local)

```bash
# 1) Install Dependencies
pip install pandas arcgis

# 2) Set Credentials (Environment Variables)
# Linux/Mac
export ARCGIS_USERNAME="your_username"
export ARCGIS_PASSWORD="your_password"

# Windows (PowerShell)
$env:ARCGIS_USERNAME="your_username"
$env:ARCGIS_PASSWORD="your_password"

# 3) Run Pipeline
python Auto_Workflow.py
✅ On success, logic errors are fixed in ArcGIS, dates are shifted, and docs/data.json is regenerated.

⚙️ Workflow (CI/CD)
File: .github/workflows/schedule.yml
Goal: Daily synchronization of schedule logic and visualization.

🗓️ Triggers
Schedule: 0 2 * * * (Every day at 02:00 UTC)

Manual: workflow_dispatch button

🧱 Runner
ubuntu-latest (Python 3.10)

🛡️ Safety
Pipeline aborts immediately if the computing phase fails to prevent visualizing corrupt data.

🔐 Configuration & Secrets
To run this pipeline, configure the following GitHub Secrets:

Variable Name	Description
ARCGIS_USERNAME	Your ArcGIS Online username
ARCGIS_PASSWORD	Your ArcGIS Online password

⚠️ Security Note: Never hardcode passwords in scripts. Always use environment variables.

🧩 Algorithm Details
1. The “Time-Travel” Clean-up
Goal: Prevent logic loops.
Check:
Is Predecessor.PlanStart > Current.PlanStart?
Action: If true, the dependency link is deleted from ArcGIS PreIDs.

2. The “Cascade” Effect (DAG)
Goal: Keep schedule realistic.

Trigger: A task is delayed (Actual Start > Planned Start).

Rule:

sql
复制代码
New Start = Max(Planned Start, Predecessor Finish)
Write-Back: Updates are committed to ArcGIS only if dates shift by > 60 seconds.

🗃️ Visualization Output
Gantt_Chart.py generates a JSON file structured for the frontend.

Color Coding Strategy
🟢 Project (Root Level)

🔵 Object (Group Level)

🟣 Task (Leaf Level)

🔴 Delayed Item (Visual Flag)

🧪 Validation Checklist
 ArcGIS Permissions: Does the account have Edit rights on the Feature Layer?

 Secrets: Are ARCGIS_USERNAME and ARCGIS_PASSWORD set?

 Data Integrity: Are there circular dependencies?

 Timezone: GitHub Actions runs in UTC.

📄 License
MIT License

复制代码
