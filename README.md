# ICA Project Management Auto Workflow

This repository contains a set of Python scripts and GitHub Actions workflows designed to help **automate parts of ICA project management**, including day‑level calculations and schedule visualization (such as Gantt charts).

> Note: This README is written based on the current repository layout and file names.  
> Please refer to the actual Python code for full implementation details.

---

## Features

- Automate routine ICA project management calculations using Python.
- Support for **day‑level / dynamic** project calculations (e.g., task date calculations).
- Generate or update **Gantt charts** to visualize project progress.
- Integrate with **GitHub Actions** for automated execution on a schedule or on code changes.

---

## Repository Structure

```text
ICA_Project_Management_Auto_Workflow/
├─ .github/
│  └─ workflows/          # GitHub Actions workflow configuration files
├─ docs/                  # Additional documentation / examples (to be extended)
├─ Auto_Work_flow.py      # Main automation workflow script
├─ Day_Dynamic_Computing.py  # Script for day-based / dynamic calculations
├─ Gantt_Chart.py         # Script for generating / updating Gantt charts
└─ README.md              # Project documentation
```

If you are unsure about a script’s exact behavior or I/O format, open the corresponding `.py` file and check the code and comments.

---

## Requirements

- **Python 3.x**
- Recommended: a virtual environment (`venv`, `conda`, etc.)

Third‑party dependencies (if any) are imported directly in the Python scripts. Install them as needed, for example:

```bash
pip install <dependency-name>
```

You may want to create a `requirements.txt` later to formalize the dependency list.

---

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/binbingwu/ICA_Project_Management_Auto_Workflow.git
   cd ICA_Project_Management_Auto_Workflow
   ```

2. **(Optional) Create and activate a virtual environment**

   ```bash
   python -m venv .venv

   # On Windows
   .venv\Scriptsctivate

   # On macOS / Linux
   source .venv/bin/activate
   ```

3. **Install dependencies**

   If you have created a `requirements.txt`:

   ```bash
   pip install -r requirements.txt
   ```

   Or install libraries manually according to the imports inside each script.

---

## Usage

> The commands below are examples.  
> Adjust arguments, config paths, and I/O files based on how you implement the scripts.

### 1. Run the main automation workflow

```bash
python Auto_Work_flow.py
```

Typical responsibilities you might implement here:

- Read project plan data (e.g., Excel, CSV, database, or API).
- Call the daily / dynamic calculation module.
- Call the Gantt chart generation module.
- Write results back to files, databases, or report folders.

---

### 2. Day‑based dynamic calculations

```bash
python Day_Dynamic_Computing.py
```

This script is intended for logic such as:

- Date calculations (start / end dates).
- Remaining duration / progress by day.
- Daily updates to task or project status.

You can expose configuration through:

- Command‑line arguments,
- A configuration file (e.g., YAML/JSON),
- Or environment variables.

---

### 3. Gantt chart generation

```bash
python Gantt_Chart.py
```

Suggested responsibilities:

- Load project/task data from your chosen source.
- Use a plotting/visualization library (for example `matplotlib`) to create Gantt charts.
- Export the chart as an image (e.g., `PNG`, `JPG`, `SVG`) for reporting or dashboards.

---

## GitHub Actions Automation

The `.github/workflows` directory contains **GitHub Actions** configuration files.

With them, you can:

- Run project calculations automatically on **push** or **pull requests**.
- Schedule periodic runs (e.g., daily or weekly) using the `schedule` trigger.
- Automatically generate and upload artifacts (e.g., reports or chart images).

To modify the automation behavior:

1. Open the YAML files in `.github/workflows/`.
2. Update the triggers (e.g., `on: push`, `on: schedule`) and the commands used to run your scripts.
3. Commit and push the changes.

---

## Recommended Improvements

If you plan to evolve this project further, consider:

- Adding detailed documentation in the `docs/` folder:
  - Project background and ICA business context
  - Example inputs and outputs
  - Data format specifications
- Adding docstrings and type hints to key functions and classes.
- Adding:
  - `requirements.txt` or `pyproject.toml`,
  - Unit tests for core calculation logic,
  - Example datasets for demos.

---

## Contributing

Contributions are welcome!

You can:

- Open an **Issue** to report bugs or propose features.
- Create a **Pull Request** to improve code, documentation, or workflows.

Before submitting, please:

1. Keep the code style consistent (e.g., follow PEP 8 for Python).
2. Ensure that important scripts run successfully in your local environment.

---

## License

No explicit open‑source license file has been identified in this repository.  
Before using this project in production or redistributing it, please **confirm licensing terms with the repository owner**.

---

## Contact

For questions, suggestions, or collaboration, please contact the repository owner via GitHub:

- GitHub profile: https://github.com/binbingwu

