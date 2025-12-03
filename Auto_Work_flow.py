import sys
import time
from datetime import datetime

# Import modules (files must be in the same directory)
import Day_Dynamic_Computing
import Gantt_Chart

def run_pipeline():
    """
    Master workflow controller.
    Executes modules in sequence. Stops if a critical module fails.
    """
    start_time = time.time()
    print(f"🤖 Auto_Workflow triggered at {datetime.now().isoformat()}")
    print("="*50)

    # --- Step 1: Dynamic Computing (Critical) ---
    print("\n>>> STEP 1: Running Dynamic Schedule Computing...")
    try:
        success = Day_Dynamic_Computing.run_scheduler()
        if not success:
            print("🛑 Step 1 Failed. Aborting pipeline to prevent bad data propagation.")
            sys.exit(1) # Return non-zero exit code so GitHub Actions marks it as 'Failed'
    except Exception as e:
        print(f"💥 Unhandled exception in Step 1: {e}")
        sys.exit(1)
    sleep(10)
    # --- Step 2: Gantt Chart Generation (Visualization) ---
    print("\n>>> STEP 2: Generating Gantt Chart JSON...")
    try:
        success = Gantt_Chart.generate_gantt()
        if not success:
            print("⚠️ Step 2 Failed. The chart data might be stale.")
            # We might not want to exit(1) here if we want the rest to continue, 
            # but usually, this is the last step.
            sys.exit(1)
    except Exception as e:
        print(f"💥 Unhandled exception in Step 2: {e}")
        sys.exit(1)

    # --- Step 3: Future Modules (Example) ---
    # import Email_Reporter
    # Email_Reporter.send_daily_summary()

    elapsed = time.time() - start_time
    print("\n" + "="*50)
    print(f"✅ Workflow completed successfully in {elapsed:.2f} seconds.")
    print("="*50)

if __name__ == "__main__":
    run_pipeline()
