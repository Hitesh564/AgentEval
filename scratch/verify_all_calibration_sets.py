import sys
import os

sys.path.insert(0, os.path.abspath("."))

from examples.simple_rag_agent import run_calibration_dataset as run_linear
from examples.parallel_research_agent import run_calibration_dataset as run_branching
from examples.retry_agent import run_calibration_dataset as run_retry
from examples.multi_agent_pipeline import run_calibration_dataset as run_multi_agent

def main():
    db_path = "agenteval.db"
    
    print("==========================================================================")
    print("           RE-RUNNING ALL 4 CALIBRATION DATASETS FOR VERIFICATION        ")
    print("==========================================================================")
    
    print("\n--- 1. LINEAR DATASET (45 cases) ---")
    run_linear(db_path=db_path, version="calib")
    run_linear(db_path=db_path, version="fixed")
    
    print("\n--- 2. BRANCHING DATASET (8 cases) ---")
    run_branching(db_path=db_path, version="calib")
    run_branching(db_path=db_path, version="fixed")

    print("\n--- 3. RETRY DATASET (9 cases) ---")
    run_retry(db_path=db_path, version="calib")
    run_retry(db_path=db_path, version="fixed")

    print("\n--- 4. MULTI-AGENT DATASET (10 cases) ---")
    run_multi_agent(db_path=db_path, version="calib")
    run_multi_agent(db_path=db_path, version="fixed")
    
    print("\n==========================================================================")
    print("               VERIFICATION RUN COMPLETED SUCCESSFULLY                   ")
    print("==========================================================================")

if __name__ == "__main__":
    main()
