import tempfile
import os
import shutil
import subprocess
import sqlite3
import json
import csv
from typing import Optional
from models import DataJanitorAction, DataJanitorObservation, EnvResponse, ActionType
from tasks import grade_easy_task, grade_medium_task, grade_hard_task


class DataJanitorEnv:
    def __init__(self, task_level: str, max_steps: int = 10):
        if task_level not in ["easy", "medium", "hard"]:
            raise ValueError("task_level must be one of: easy, medium, hard")
        
        self.task_level = task_level
        self.max_steps = max_steps
        self.workspace: Optional[str] = None
        self.db_path: Optional[str] = None
        self.previous_score = 0.001
        self.current_step = 0
        self.task_desc = ""

    def reset(self) -> EnvResponse:
        # Create temp workspace
        self.workspace = tempfile.mkdtemp(prefix="data-janitor-")
        self.db_path = os.path.join(self.workspace, "output.db")
        
        # Initialize empty database
        conn = sqlite3.connect(self.db_path)
        conn.close()
        
        # Generate task data
        if self.task_level == "easy":
            self._generate_easy_data()
            self.task_desc = "Load the users.csv file into a SQLite database table named 'users'. The file contains 10 rows with columns: id, name, email."
        elif self.task_level == "medium":
            self._generate_medium_data()
            self.task_desc = "Clean the sales.csv file and save to 'clean_sales' table with standardized date format YYYY-MM-DD. The file contains 20 rows with mixed date formats."
        elif self.task_level == "hard":
            self._generate_hard_data()
            self.task_desc = "Calculate lifetime value (LTV) for users who opted into marketing. Filter users from users.json, merge with purchases.csv, group by user_id and sum amounts. Save to 'ltv_report' table."
        
        self.previous_score = 0.001
        self.current_step = 0
        
        observation = DataJanitorObservation(
            task_description=self.task_desc,
            files_in_workspace=self._list_files(),
            database_info=self._get_db_info(),
            current_score=0.001
        )
        
        return EnvResponse(observation=observation, reward=0.001, done=False)

    def _generate_easy_data(self):
        users_data = [
            [1, "Alice Johnson", "alice@example.com"],
            [2, "Bob Smith", "bob@example.com"],
            [3, "Charlie Brown", "charlie@example.com"],
            [4, "Diana Prince", "diana@example.com"],
            [5, "Eve Wilson", "eve@example.com"],
            [6, "Frank Miller", "frank@example.com"],
            [7, "Grace Lee", "grace@example.com"],
            [8, "Henry Davis", "henry@example.com"],
            [9, "Ivy Chen", "ivy@example.com"],
            [10, "Jack Taylor", "jack@example.com"]
        ]
        
        with open(os.path.join(self.workspace, "users.csv"), "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name", "email"])
            writer.writerows(users_data)

    def _generate_medium_data(self):
        sales_data = [
            [1, "2024-01-15", 100.50],
            [2, "01/16/2024", 200.75],
            [3, "17-01-2024", 150.25],
            [4, "2024/01/18", 300.00],
            [5, "2024-01-19", 75.50],
            [6, "01/20/2024", 125.00],
            [7, "21-01-2024", 180.75],
            [8, "2024/01/22", 250.25],
            [9, "2024-01-23", 90.00],
            [10, "01/24/2024", 175.50],
            [11, "25-01-2024", 220.00],
            [12, "2024/01/26", 135.75],
            [13, "2024-01-27", 160.25],
            [14, "01/28/2024", 195.00],
            [15, "29-01-2024", 110.50],
            [16, "2024/01/30", 280.75],
            [17, "2024-01-31", 145.25],
            [18, "01/02/2024", 210.00],
            [19, "03-01-2024", 95.50],
            [20, "2024/01/04", 185.75]
        ]
        
        with open(os.path.join(self.workspace, "sales.csv"), "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "date", "amount"])
            writer.writerows(sales_data)

    def _generate_hard_data(self):
        users_data = [
            {"user_id": 1, "name": "Alice", "marketing_opt_in": True},
            {"user_id": 2, "name": "Bob", "marketing_opt_in": False},
            {"user_id": 3, "name": "Charlie", "marketing_opt_in": True},
            {"user_id": 4, "name": "Diana", "marketing_opt_in": True}
        ]
        
        with open(os.path.join(self.workspace, "users.json"), "w") as f:
            json.dump(users_data, f, indent=2)
        
        purchases_data = [
            [1, 1, 50.00],  # user 1
            [2, 1, 100.50], # user 1 -> total 150.50
            [3, 3, 200.00], # user 3
            [4, 3, 300.00], # user 3 -> total 500.00
            [5, 4, 10.25],  # user 4 -> total 10.25
            [6, 2, 75.00],  # user 2 (not opted in)
            [7, 2, 25.00]   # user 2 (not opted in)
        ]
        
        with open(os.path.join(self.workspace, "purchases.csv"), "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "user_id", "amount"])
            writer.writerows(purchases_data)

    def step(self, action: DataJanitorAction) -> EnvResponse:
        self.current_step += 1
        
        stdout, stderr = "", ""
        
        if action.action_type == ActionType.RUN_PYTHON:
            stdout, stderr = self._execute_python(action.python_code)
        elif action.action_type == ActionType.LIST_FILES:
            stdout = "\n".join(self._list_files())
        elif action.action_type == ActionType.READ_FILE:
            try:
                with open(os.path.join(self.workspace, action.file_path), "r") as f:
                    stdout = f.read()
            except Exception as e:
                stderr = str(e)
        
        current_score = self._get_current_score()
        reward = current_score - self.previous_score
        self.previous_score = current_score
        
        done = (current_score >= 0.99) or (self.current_step >= self.max_steps)
        
        observation = DataJanitorObservation(
            task_description=self.task_desc,
            stdout=stdout,
            stderr=stderr,
            files_in_workspace=self._list_files(),
            database_info=self._get_db_info(),
            current_score=current_score
        )
        
        return EnvResponse(observation=observation, reward=reward, done=done)

    def _execute_python(self, code: str) -> tuple[str, str]:
        script_path = os.path.join(self.workspace, "agent_script.py")
        with open(script_path, "w") as f:
            f.write(code)
        
        try:
            result = subprocess.run(
                ["python", "agent_script.py"],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return "", "Execution timed out"
        except Exception as e:
            return "", str(e)

    def _get_current_score(self) -> float:
        if not os.path.exists(self.db_path):
            return 0.001
        
        if self.task_level == "easy":
            score, _ = grade_easy_task(self.db_path)
        elif self.task_level == "medium":
            score, _ = grade_medium_task(self.db_path)
        elif self.task_level == "hard":
            score, _ = grade_hard_task(self.db_path)
        else:
            score = 0.001
        
        return score

    def _list_files(self) -> list[str]:
        if not self.workspace:
            return []
        return [f for f in os.listdir(self.workspace) if os.path.isfile(os.path.join(self.workspace, f))]

    def _get_db_info(self) -> dict:
        if not self.db_path or not os.path.exists(self.db_path):
            return {}
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            return {"tables": tables}
        except:
            return {}

    def cleanup(self):
        if self.workspace and os.path.exists(self.workspace):
            try:
                shutil.rmtree(self.workspace)
            except Exception:
                pass  # Ignore cleanup errors