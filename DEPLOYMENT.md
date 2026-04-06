# 🚀 DataJanitorEnv - Deployment & Execution Guide

## Quick Start (2 minutes)

### ✅ Option 1: Run Locally (Recommended for Testing)

**Step 1: Install Dependencies**
```bash
cd data-janitor-env
pip install -r requirements.txt
```

**Step 2: Run Mock Agent (No API key required)**
```bash
python mock_agent.py
```

**Expected Output:**
```
[START] EASY TASK
[STEP 1] Action: list_files
[STEP 2] Action: run_python
Code executed successfully
Reward: +1.00
[END] Task completed! Final Score: 1.00

[START] MEDIUM TASK
[STEP 1] Action: list_files
[STEP 2] Action: run_python
Code executed successfully
Reward: +1.00
[END] Task completed! Final Score: 1.00

[START] HARD TASK
[STEP 1] Action: list_files
[STEP 2] Action: run_python
Code executed successfully
Reward: +1.00
[END] Task completed! Final Score: 1.00
```

**Total Score: 3.0/3.0** ✅

---

### 🤖 Option 2: Run with GPT-4 Agent (Requires API Key)

**Step 1: Get OpenAI API Key**
- Go to [OpenAI Platform](https://platform.openai.com/api-keys)
- Create/copy your secret key (format: `sk-...`)

**Step 2: Set Environment Variable**

**On Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY = "sk-your-api-key-here"
```

**On Windows (Command Prompt):**
```cmd
set OPENAI_API_KEY=sk-your-api-key-here
```

**On macOS/Linux/WSL:**
```bash
export OPENAI_API_KEY="sk-your-api-key-here"
```

**Or use .env file:**
```bash
cp .env.example .env
# Edit .env and add your key:
# OPENAI_API_KEY=sk-your-api-key-here
```

**Step 3: Run GPT-4 Agent**
```bash
python inference.py
```

**Expected Output:**
```
✅ OpenAI API key found!
🚀 Starting GPT-4 agent inference on all 3 tasks...

============================================================
[START] EASY TASK (GPT-4)
============================================================
Task: Load the users.csv file into a SQLite database table named 'users'.
Initial Files: users.csv, output.db
Database: {'tables': []}

[STEP 1] Action: run_python
  └─ Reward: +1.000 (Total Score: 1.000)

============================================================
[END] Task: EASY | Final Score: 1.000 | Steps: 1
============================================================

... (medium and hard tasks) ...

============================================================
📊 FINAL RESULTS: Total Score: 3.000 / 3.0
============================================================
```

---

## 🐳 Docker Deployment

### Option 1: Build and Run Locally

**Build Docker Image:**
```bash
docker build -t data-janitor-env:latest .
```

**Run with Mock Agent (Default):**
```bash
docker run --rm data-janitor-env:latest
```

**Run with GPT-4 Agent:**
```bash
docker run --rm \
  -e OPENAI_API_KEY="sk-your-api-key-here" \
  data-janitor-env:latest \
  python inference.py
```

### Option 2: Push to Docker Registry (For Competition)

**Tag Image:**
```bash
docker tag data-janitor-env:latest your-username/data-janitor-env:latest
```

**Login to Docker Hub:**
```bash
docker login
```

**Push Image:**
```bash
docker push your-username/data-janitor-env:latest
```

**Run from Registry:**
```bash
docker run --rm your-username/data-janitor-env:latest
```

---

## 📋 File Structure & Purpose

```
data-janitor-env/
├── models.py              # Pydantic data schemas (Action, Observation, Response)
├── tasks.py               # Graders for 3 difficulty levels
├── env.py                 # Core environment (reset, step, reward logic)
├── mock_agent.py          # Test agent (solves all tasks, no API key)
├── inference.py           # GPT-4 agent (optional, requires API key)
├── openenv.yaml           # OpenEnv framework config
├── Dockerfile             # Container specification
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variable template
├── setup.py               # Package configuration
└── README.md              # Detailed documentation
```

---

## 🎯 Understanding the Tasks

### Easy Task (Score 0.0 - 1.0)
- **Input**: `users.csv` (10 rows: id, name, email)
- **Goal**: Load into SQLite table named `users`
- **Scoring**: `score = min(rows_loaded / 10.0, 1.0)`

### Medium Task (Score 0.0 - 1.0)
- **Input**: `sales.csv` (20 rows with mixed date formats)
- **Goal**: Clean dates to YYYY-MM-DD format, save to `clean_sales` table
- **Scoring**: `score = min(correct_dates / 20.0, 1.0)`

### Hard Task (Score 0.0 - 1.0)
- **Input**: `users.json` (with marketing_opt_in field) + `purchases.csv`
- **Goal**: Filter opted-in users, merge data, calculate LTV, save to `ltv_report`
- **Expected Users**: {1: 150.50, 3: 500.00, 4: 10.25}
- **Scoring**: `score = min(correct_matches / 3.0, 1.0)`

---

## 🔧 Configuration Options

### Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `OPENAI_API_KEY` | GPT-4 API authentication (optional) | `sk-...` |
| `TASK_LEVEL` | Run single task instead of all 3 | `easy`, `medium`, `hard` |
| `MAX_STEPS` | Max steps per task | `10` (default), `20`, etc. |
| `PYTHONUNBUFFERED` | Real-time output | `1` |

### Using .env File

Create `.env`:
```bash
OPENAI_API_KEY=sk-your-api-key-here
TASK_LEVEL=easy
MAX_STEPS=15
PYTHONUNBUFFERED=1
```

Load in Python:
```python
from dotenv import load_dotenv
load_dotenv()  # Loads from .env
```

---

## 🧪 Testing & Validation

### 1. Test Models Import
```bash
python -c "from models import DataJanitorAction, DataJanitorObservation, EnvResponse; print('✅ Models OK')"
```

### 2. Test Environment
```python
from env import DataJanitorEnv
env = DataJanitorEnv("easy")
obs = env.reset()
print(f"Task: {obs.observation.task_description}")
print(f"Files: {obs.observation.files_in_workspace}")
env.cleanup()
```

### 3. Test Graders
```python
from tasks import grade_easy_task, grade_medium_task, grade_hard_task
score, msg = grade_easy_task("./output.db")
print(f"Score: {score}, Message: {msg}")
```

### 4. Run Specific Task
```bash
# Edit mock_agent.py to run only one task:
for task_level in ["easy"]:  # Change this line
    agent = MockAgent(task_level)
    await agent.run()
```

---

## 📊 Performance Benchmarks

| Method | Time | Score | API Cost |
|--------|------|-------|----------|
| Mock Agent (all 3) | ~2 seconds | 3.0 | $0 |
| GPT-4 Agent (all 3) | ~30-60 seconds | 2.5-3.0 | ~$0.10 |
| Docker (mock agent) | ~3 seconds | 3.0 | $0 |

---

## 🚨 Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'pydantic'"
**Solution:**
```bash
pip install -r requirements.txt
```

### Issue: "OPENAI_API_KEY not set or invalid"
**Solution:**
```bash
export OPENAI_API_KEY="sk-your-key"
# OR
python -c "import os; os.environ['OPENAI_API_KEY']='sk-your-key'; exec(open('inference.py').read())"
```

### Issue: Docker build fails
**Solution:**
```bash
docker build --no-cache -t data-janitor-env:latest .
```

### Issue: Agent times out (subprocess running >30 seconds)
**Solution:**
- Edit `env.py` line with `timeout=30` → increase to `timeout=60`
- Or simplify the Python code the agent is running

### Issue: "output.db" not found in grader
**Solution:**
- Make sure agent's Python code creates the database
- Check `_execute_python()` in `env.py` runs in correct workspace

---

## 🎓 Development Tips

### 1. Debug Agent's Code
In `mock_agent.py`, add print statements:
```python
def _easy_step(self, step_num, obs):
    if step_num == 2:
        code = """
import pandas as pd
df = pd.read_csv('users.csv')
print(f"Loaded {len(df)} rows")  # Add debugging
df.to_sql('users', sqlite3.connect('output.db'), if_exists='replace')
"""
        return DataJanitorAction(action_type=ActionType.RUN_PYTHON, python_code=code)
```

### 2. Inspect Database
```python
import sqlite3
conn = sqlite3.connect('output.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM users LIMIT 5;")
print(cursor.fetchall())
conn.close()
```

### 3. Test Grader Directly
```python
from tasks import grade_easy_task
score, message = grade_easy_task('/path/to/output.db')
print(f"Score: {score}, Details: {message}")
```

### 4. View Generated Data
```python
from env import DataJanitorEnv
env = DataJanitorEnv("easy")
env.reset()
# Check workspace
import os
print(os.listdir(env.workspace))
# Read generated CSV
with open(os.path.join(env.workspace, "users.csv")) as f:
    print(f.read())
```

---

## 📝 Competition Submission Checklist

- [ ] All files present: models.py, env.py, tasks.py, mock_agent.py, inference.py
- [ ] Mock agent runs: `python mock_agent.py` → Score 3.0
- [ ] Docker builds: `docker build -t data-janitor-env .`
- [ ] Docker runs: `docker run data-janitor-env:latest` → Score 3.0
- [ ] openenv.yaml is valid YAML
- [ ] All imports work: `python -c "from models import *; from env import *; from tasks import *"`
- [ ] .env.example template provided
- [ ] README.md complete with architecture
- [ ] No hardcoded API keys in code
- [ ] Timeout protection in place (30s default)
- [ ] All graders return 0.0-1.0 range

---

## 🎉 Success!

Your DataJanitorEnv project is **production-ready**! You can now:
1. ✅ Run locally with mock agent (instant, free)
2. ✅ Test with GPT-4 (requires API key, ~$0.10)
3. ✅ Deploy in Docker (reproducible, portable)
4. ✅ Submit to competition

**Next Step**: Run the mock agent and verify everything works:
```bash
python mock_agent.py
```

Good luck! 🚀
