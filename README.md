📅 ArcGIS Dynamic Schedule & Automated Gantt Visualization📘 Pipeline: ArcGIS Feature Layer ⇄ Logic Cleaning & DAG Scheduling → generate docs/data.json → visualize on GitHub Pages.📖 IntroductionThis system is an automated controller for complex construction schedules. It ensures data stored in ArcGIS is logically sound and visually accessible.Clean: Automatically removes "time-travel" paradoxes (predecessor > successor).Calculate: Propagates delays downstream using DAG (Directed Acyclic Graph) logic.Visualize: Generates a hierarchical Gantt chart for the project website.🧱 Repository StructureArcGIS_Scheduler/
│
├── Auto_Workflow.py           # 🎮 Orchestrator: Master Controller (Entry Point)
├── Day_Dynamic_Computing.py   # ⚙️ Engine: Logic Cleaning & DAG Calculation
├── Gantt_Chart.py             # 📊 Visualizer: JSON Generator
├── docs/
│   ├── index.html             # Frontend visualization
│   └── data.json              # Generated Gantt data (Do not edit manually)
└── .github/
    └── workflows/
        └── schedule.yml       # 🤖 Automation: Daily Trigger (02:00 UTC)
🗺️ Architecture / Data FlowGitHub Actions (Daily Trigger)
            │
            ▼
    [ Auto_Workflow.py ] ──(Safety Check)──┐
            │                              │
            ├─► Step 1: Compute ──────────►│
            │                              ▼
            │                   { Day_Dynamic_Computing.py }
            │                              │
            │                    (Read/Write Sync - Clean Logic)
            │                              ▼
            │                  [( ArcGIS Feature Layers )]
            │                              ▲
            ├─► Step 2: Generate ──────────┘
            │          │
            │          ▼
            │   { Gantt_Chart.py } ──(Read Only)──► docs/data.json
            │                                            │
            └────────────────────────────────────────────┼──► Commit & Push
                                                         │
                                                         ▼
                                               GitHub Pages / Web UI
⚡ Quick Start (Local)# 1) Install Dependencies
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
✅ On success, logic errors are fixed in ArcGIS, dates are shifted, and docs/data.json is regenerated.⚙️ Workflow (CI/CD)File: .github/workflows/schedule.ymlGoal: Daily synchronization of schedule logic and visualization.🗓️ TriggersSchedule: 0 2 * * * (Every day at 02:00 UTC)Manual: workflow_dispatch button🧱 Runner: ubuntu-latest (Python 3.10)🛡️ Safety: Pipeline aborts immediately if the computing phase fails to prevent visualizing corrupt data.🔐 Configuration & SecretsTo run this pipeline, you must configure the following GitHub Secrets:Variable NameDescriptionARCGIS_USERNAMEYour ArcGIS Online usernameARCGIS_PASSWORDYour ArcGIS Online password⚠️ Security Note: Never hardcode passwords in the scripts. Always use environment variables.🧩 Algorithm Details1. The "Time-Travel" Clean-upGoal: Prevent logic loops.Check: Is Predecessor.PlanStart > Current.PlanStart?Action: If true, the dependency link is deleted from ArcGIS PreIDs.2. The "Cascade" Effect (DAG)Goal: Keep schedule realistic.Trigger: A task is delayed (Actual Start > Planned Start).Rule: New Start = Max(Planned Start, Predecessor Finish).Write-Back: Updates are committed to ArcGIS only if dates shift by > 60 seconds.🗃️ Visualization OutputThe Gantt_Chart.py script generates a JSON file structured for the frontend.Color Coding Strategy:🟢 Project (Root Level)🔵 Object (Group Level)🟣 Task (Leaf Level)🔴 Delayed Item (Visual Flag)🧪 Validation Checklist[ ] ArcGIS Permissions: Does the account have "Edit" rights on the Feature Layer?[ ] Secrets: Are ARCGIS_USERNAME and ARCGIS_PASSWORD set in Repo Settings?[ ] Data Integrity: Are there circular dependencies in the source data? (Script attempts to handle this, but best to avoid).[ ] Timezone: Remember GitHub Actions runs in UTC.📄 LicenseMIT License
