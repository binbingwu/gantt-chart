📅 ArcGIS Dynamic Schedule & Automated Gantt Visualization📖 OverviewThis repository hosts an automated pipeline designed to synchronize, calculate, and visualize complex construction schedules stored in ArcGIS Feature Layers.The system performs three critical functions automatically every day:Data Integrity & Logic Cleaning: Detects and removes "time-travel" paradoxes in dependencies (e.g., a predecessor starting after its successor).Dynamic Scheduling (DAG): Uses a Directed Acyclic Graph algorithm to propagate delays. If a task is delayed, all downstream tasks are automatically shifted in the ArcGIS database.Visualization: Generates a hierarchical Gantt chart JSON dataset (docs/data.json) to be rendered on the project website.🏗 System ArchitectureThe workflow is orchestrated by a central controller that ensures data consistency before visualization.graph TD
    A[GitHub Actions Daily Trigger] -->|Runs| B(Auto_Workflow.py)
    B -->|Step 1: Compute| C{Day_Dynamic_Computing.py}
    C <-->|Read/Write| D[(ArcGIS Feature Layers)]
    C -->|Success| E[Step 2: Generate]
    C -->|Failure| X[Abort Pipeline]
    E -->|Runs| F{Gantt_Chart.py}
    F <-->|Read Only| D
    F -->|Output| G[docs/data.json]
    G -->|Commit & Push| H[GitHub Pages / Web UI]

📂 Script Modules1. Auto_Workflow.py (The Orchestrator)Role: The Entry Point.This script acts as the master controller for the CI/CD pipeline. It manages the dependencies between the calculation module and the visualization module.Logic: It executes Day_Dynamic_Computing.py first.Safety: If the computing phase fails (e.g., API errors, logic crashes), the pipeline aborts immediately. This prevents the system from generating a Gantt chart based on stale or corrupt data.Extensibility: Designed to easily accommodate future modules (e.g., Email Reporting, Cost Analysis) by adding them to the pipeline sequence.2. Day_Dynamic_Computing.py (The Engine)Role: Logic Processing & Database Writing.This is the core algorithmic engine. It connects to ArcGIS with write permissions to update schedules.Conflict Resolution: Scans for invalid dependencies (e.g., Task B depends on Task A, but Task A starts after Task B). These invalid links are automatically removed from the database to ensure graph integrity.DAG Propagation:Constructs a memory graph of all Tasks and Work Stations (WS).Performs a Topological Sort to determine the correct calculation order.Rule: New ActStart = Max(PlanStart, Predecessor ActEnd).Write-Back: If a task's dates change by more than 60 seconds, the new dates are committed back to the ArcGIS Feature Layer, ensuring the database is always up-to-date with reality.3. Gantt_Chart.py (The Visualizer)Role: Data Formatting & Export.This script reads the processed data and formats it for the frontend.Hierarchy: Structures data into Project -> Object -> Task / WS.Delay Detection: Compares Actual Start vs. Planned Start. If a task starts late, it is visually flagged.Color Coding:🟢 Project🔵 Object🟣 Task🟠 Work Station (WS)🔴 Delayed ItemOutput: Produces docs/data.json, which is consumed by the frontend HTML engine.🤖 Automation (GitHub Actions)The workflow is defined in .github/workflows/schedule.yml.Trigger:Daily: Runs automatically at 02:00 UTC every day.Manual: Can be triggered manually via the "Run workflow" button in the GitHub Actions tab.Environment: Runs on ubuntu-latest with Python 3.10.Security: Uses GitHub Secrets to store ArcGIS credentials. No passwords are hardcoded.Deployment: Automatically commits the generated data.json to the main branch and triggers a GitHub Pages rebuild.🚀 Setup & ConfigurationPrerequisitesPython 3.10+pandas, arcgis libraries.Local Installationgit clone [https://github.com/YOUR_REPO.git](https://github.com/YOUR_REPO.git)
cd YOUR_REPO
pip install pandas arcgis

Environment VariablesFor the scripts to function (locally or on GitHub), you must set the following environment variables:Variable NameDescriptionARCGIS_USERNAMEYour ArcGIS Online username.ARCGIS_PASSWORDYour ArcGIS Online password.Running LocallyTo test the full pipeline on your machine:# Linux/Mac
export ARCGIS_USERNAME="your_user"
export ARCGIS_PASSWORD="your_password"
python Auto_Workflow.py

# Windows (PowerShell)
$env:ARCGIS_USERNAME="your_user"
$env:ARCGIS_PASSWORD="your_password"
python Auto_Workflow.py

🧩 Algorithm DetailsThe "Time-Travel" Clean-upBefore calculating the schedule, the engine checks every dependency link.Logic: If Predecessor.PlanStart > Current.PlanStart, the link is invalid.Action: The link is removed from the PreIDs list in ArcGIS to prevent logic loops and schedule corruption.The "Cascade" EffectWhen a task is delayed:User updates the ActStart of "Task A" in ArcGIS (or it remains empty and defaults to Plan).Day_Dynamic_Computing.py runs.It sees "Task A" finishes later than expected.It finds "Task B", which depends on "Task A".It forces "Task B" to start no earlier than "Task A" finishes.This ripple effect continues down the entire chain.📄 LicenseMIT License (or your preferred license)
