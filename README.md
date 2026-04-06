# Data Janitor Environment 🧹

A complete, production-grade local Python environment for training AI agents to clean messy data and perform data engineering tasks. The system generates progressive tasks (Easy, Medium, Hard) with deterministic grading, allowing agents to learn incrementally through **delta rewards** (score improvements). Perfect for testing data cleaning logic **without needing Docker or API dependencies** (except optional GPT-4).

## 📋 What This Project Does

This is a **reinforcement learning environment** (similar to OpenAI Gym) where:
- **Agents** interact by sending **actions** (run Python code, list files, read files)
- **Environment** executes actions in isolated temp workspaces and returns **observations** (task descriptions, code output, file listings, database info)
- **Reward system** uses **delta rewards**: Score = current_score - previous_score (agents learn by making progress, not just completing tasks)
- **3 Progressive Tasks**: Easy (load CSV to DB), Medium (standardize date formats), Hard (merge JSON+CSV, compute LTV)
- **Deterministic grading**: Same input → same score every time (perfect for testing)
- **Mock agent included**: Solves all tasks perfectly without AI/API keys (proves environment works)
- **Optional GPT-4 integration**: Test real LLMs by setting `OPENAI_API_KEY`

**Use case**: Train/test data engineering agents, debug data pipelines, validate data cleaning logic locally.

---

## 🏗️ How Everything Works Together

### System Architecture Flow

```
Agent (Mock or GPT-4)
    ↓
Calls: env.reset() → Get initial task, workspace, mock data
    ↓
Loop: Agent chooses action → env.step(action) → Execute & compute reward
    ↓
Environment (env.py):
  ├─ Creates isolated temp workspace (tempfile.mkdtemp)
  ├─ Generates mock data (_generate_*_data in env.py)
  ├─ Runs agent's Python code via subprocess (isolated, timeout=30s)
  ├─ Creates/updates SQLite output.db
  ├─ Calls graders (tasks.py) to compute score
  ├─ Calculates reward = current_score - previous_score
  └─ Returns: observation, reward, done flag
    ↓
Agent checks: done? (score >= 0.99 OR steps >= max_steps)
    ↓
If done → End task, cleanup workspace ✅
```

### File-by-File Breakdown

#### 📄 `models.py` (Data Schemas)
**Purpose**: Define strict Pydantic data types for type safety and validation.

| Class | What It Does |
|-------|-------------|
| `DataJanitorAction` | Represents what agent wants to do: `action_type` ("run_python", "list_files", "read_file"), `python_code`, `file_path` |
| `DataJanitorObservation` | What agent "sees": `task_description`, `stdout`/`stderr`, `files_in_workspace`, `database_info` |
| `EnvResponse` | Environment's response: `observation`, `reward` (float), `done` (bool), `info` (dict) |

**Key features**: All fields validated (e.g., action_type must be in allowed list). Prevents invalid data early.

---

#### 🎯 `tasks.py` (Grading & Scoring)
**Purpose**: Inspect SQLite database and return scores (0.0-1.0) based on task completion.

| Grader Function | What It Checks |
|-----------------|---------------|
| `grade_easy_task()` | Does 'users' table exist? Count rows. Score = rows / 10.0 (partial credit) |
| `grade_medium_task()` | Does 'clean_sales' table exist? Check dates match YYYY-MM-DD regex. Score = correct_dates / 20.0 |
| `grade_hard_task()` | Does 'ltv_report' table exist? Compare against ground truth: {user_id: 1→150.50, 3→500.00, 4→10.25}. Score = correct_rows / 3.0 |

**Key features**: 
- Deterministic (same DB = same score always)
- Handles errors gracefully (returns 0.0 + error message)
- Uses regex for validation (`^\d{4}-\d{2}-\d{2}$` for dates)

**Example**:
```python
score, message = grade_easy_task('./output.db')
# If 'users' has 5 rows → score = 0.5, message = "Loaded 5/10 rows"
# If 'users' not found → score = 0.0, message = "Table 'users' not found"
```

---

#### 🌍 `env.py` (Core Environment)
**Purpose**: Manage the simulation (workspaces, data generation, action execution, rewards).

**Key Methods**:

| Method | What It Does |
|--------|-------------|
| `__init__(task_level, max_steps)` | Initialize: validate task_level ∈ ["easy","medium","hard"], set max_steps (default 10) |
| `reset()` | Create temp workspace, generate mock data, init output.db, return initial observation |
| `_generate_easy_data()` | Create `users.csv`: 10 rows (id, name, email) |
| `_generate_medium_data()` | Create `sales.csv`: 20 rows with mixed date formats ("2024-01-15", "01/15/2024", etc.) |
| `_generate_hard_data()` | Create `users.json` (4 users, 2 with marketing_opt_in=True) + `purchases.csv` (7 transactions) |
| `step(action)` | Execute action, compute new score, calculate reward, check if done |
| `_execute_python(code)` | Write code to file, run via subprocess (timeout=30s), capture stdout/stderr |
| `_get_current_score()` | Call appropriate grader, return float 0.0-1.0 |
| `cleanup()` | Delete temp workspace folder |

**Key features**:
- Isolated workspaces (tempfile.mkdtemp) → no side effects
- Subprocess execution (safe, timeout protected)
- Delta rewards (current_score - previous_score)
- Done when: score ≥ 0.99 OR steps ≥ max_steps

**Example flow**:
```python
env = DataJanitorEnv("easy", max_steps=10)
obs_init = env.reset()  # Workspace created, users.csv generated, output.db initialized
print(obs_init.task_description)  # "Load users.csv into output.db as 'users' table"

action = DataJanitorAction(action_type="run_python", python_code="import pandas as pd; ...")
response = env.step(action)
print(response.reward)  # +0.5 if 5/10 rows loaded
print(response.done)    # False (score 0.5 < 0.99)

env.cleanup()  # Delete workspace
```

---

#### 🤖 `mock_agent.py` (Test Agent)
**Purpose**: Deterministic test agent that solves all tasks perfectly in 2 steps each (without AI).

**Key Methods**:

| Method | What It Does |
|--------|-------------|
| `_easy_step(step_num, obs)` | Step 1: list_files. Step 2: Run pandas code to load CSV → DB. Step 3+: None (done) |
| `_medium_step(step_num, obs)` | Step 1: list_files. Step 2: Parse mixed date formats, standardize to YYYY-MM-DD, save to DB. Step 3+: None |
| `_hard_step(step_num, obs)` | Step 1: list_files. Step 2: JSON load → DataFrame, merge with CSV, filter opt-in users, groupby LTV, save to DB. Step 3+: None |
| `async run()` | Reset env, loop through steps, print progress, check done, cleanup |
| `async main()` | Run all 3 tasks sequentially (easy → medium → hard) |

**Key features**:
- No external API calls (no OpenAI key needed)
- Achieves perfect 1.0 scores (proves environment works)
- Async/await for future scalability
- Print statements show progress

**Example output**:
```
[START] EASY TASK
[STEP 1] Action: list_files
[STEP 2] Action: run_python
Code executed successfully
Reward: +1.00
[END] Task completed! Final Score: 1.00
```

---

#### 🚀 `inference.py` (Real LLM Agent)
**Purpose**: Test with real LLM (GPT-4, Claude, or custom OpenAI-compatible endpoint).

**Environment Variables (REQUIRED)**:
```bash
HF_TOKEN=hf_...                              # Hugging Face token OR
OPENAI_API_KEY=sk_...                        # OpenAI API key

API_BASE_URL=https://api.openai.com/v1       # Optional, LLM endpoint (default: OpenAI)
MODEL_NAME=gpt-4                             # Optional, model name (default: gpt-4)
```

**Structured Logging Format**:
Inference script emits structured logs for evaluation:
```
[START] {task_level}
[STEP] {step_num} {action_type} reward={reward:.3f} score={score:.3f}
[STEP] {step_num} error {error_type}
[END] {task_level} score={final_score:.3f} steps={step_num}
```

**How it works**:
- Reads environment variables (API_BASE_URL, MODEL_NAME, HF_TOKEN/OPENAI_API_KEY)
- Creates configurable AsyncOpenAI client (supports custom endpoints)
- System prompt tells LLM to respond with JSON only
- Loop: Send task observation → parse JSON → execute action → add results to conversation
- Emits structured logs on stdout for validator parsing

**Setup**:
```bash
# Copy example config
cp .env.example .env

# Edit .env with your credentials
# HF_TOKEN=hf_your_token_here
# or OPENAI_API_KEY=sk_your_key_here

# Run inference
python inference.py
```

**Note**: Mock agent is primary (no API key needed); inference.py is optional for real LLM testing.

---

#### 📦 `requirements.txt`
Dependencies:
```
pandas==2.0.3        # Data manipulation
numpy==1.24.3        # Numerical computing
pydantic==2.0.0      # Data validation
openai==1.3.0        # GPT-4 integration (optional)
python-dotenv==1.0.0 # Load .env for API keys
```

---

#### ⚙️ `setup.py`
Standard Python package setup for distribution. Includes dependencies from requirements.txt.

---

## 🚀 Quick Start

### 1. Clone or Create Repository

**First time? Initialize Git locally**:
```bash
cd "c:\Users\Satya Sheel Shekhar\OneDrive\Desktop\meta hack"
git init
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

### 2. Create .gitignore
Create a `.gitignore` file to exclude unnecessary files:
```bash
# Create .gitignore
echo "venv/
__pycache__/
*.pyc
*.pyo
*.sqlite
*.db
.env
.DS_Store
*.egg-info/
dist/
build/" > .gitignore
```

### 3. Setup & Test Locally

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run mock agent (test everything works)
python mock_agent.py
```

**Expected output** (all 3 tasks with 1.00 scores):
```
[START] EASY TASK
[STEP 1] Action: list_files
[STEP 2] Action: run_python
Code executed successfully
Reward: +1.00
[END] Task completed! Final Score: 1.00

[START] MEDIUM TASK
...
[END] Task completed! Final Score: 1.00

[START] HARD TASK
...
[END] Task completed! Final Score: 1.00
```

### 4. Push to GitHub

**Step 1: Create GitHub Repository**
- Go to https://github.com/new
- Name: `data-janitor-env`
- Description: "Local AI agent training environment for data engineering tasks"
- Choose: Public or Private
- **Do NOT initialize** with README (we have one)
- Click "Create repository"

**Step 2: Add Remote & Push**
```bash
# Add GitHub as remote (replace YOUR_USERNAME and YOUR_REPO_NAME)
git remote add origin https://github.com/YOUR_USERNAME/data-janitor-env.git

# Stage all files
git add .

# First commit
git commit -m "Initial commit: Data Janitor Environment with 3 tasks and mock agent"

# Push to GitHub (may prompt for GitHub credentials)
git branch -M main
git push -u origin main
```

**Step 3: Verify**
- Go to your repo URL: `https://github.com/YOUR_USERNAME/data-janitor-env`
- Should see all files: `models.py`, `tasks.py`, `env.py`, `mock_agent.py`, `README.md`, etc.

---

## 📚 How to Understand the Code (Complete Guide)

### Step 1: Understand Data Flow
Start by reading in this order:
1. **`models.py`**: Understand data schemas (Action, Observation, Response)
2. **`tasks.py`**: See how grading works (each grader function)
3. **`env.py`**: Trace the main loop (reset → step → reward)
4. **`mock_agent.py`**: See how agent uses env

### Step 2: Run & Inspect Docker-Free

**Run with debug prints**:
1. Open `mock_agent.py`
2. In `async run()`, add after `env.reset()`:
   ```python
   print(f"Workspace: {env.workspace}")
   print(f"Files: {os.listdir(env.workspace)}")
   ```
3. Run: `python mock_agent.py`
4. Note the temp path (e.g., `C:\Users\...\Temp\data-janitor-abc123`)
5. **Before cleanup**, explore that folder with File Explorer or:
   ```bash
   # In PowerShell
   ls "C:\Users\...\Temp\data-janitor-abc123"  # See .csv, .json files
   sqlite3 "C:\Users\...\Temp\data-janitor-abc123\output.db" ".tables"  # See DB tables
   ```

### Step 3: Test Individual Components

**Test a grader**:
```python
from tasks import grade_easy_task
import sqlite3

# Create test DB with 5 rows
conn = sqlite3.connect('test.db')
conn.execute("CREATE TABLE users (id INT, name TEXT)")
conn.execute("INSERT INTO users VALUES (1, 'User 1')")
# ... insert 4 more rows
conn.commit()

# Grade it
score, msg = grade_easy_task('test.db')
print(f"Score: {score}, Message: {msg}")  # Output: Score: 0.5, Message: Loaded 5/10 rows
```

**Modify a grader & re-run**:
1. Open `tasks.py`
2. In `grade_easy_task()`, change `10.0` to `20.0`
3. Run `python mock_agent.py`
4. Observe: Final Score: 0.5 (instead of 1.0)
5. Revert change, re-run to confirm it goes back to 1.0

### Step 4: Trace Execution with Debugger (VS Code)

1. Open VS Code
2. Open `mock_agent.py`
3. Set breakpoint on line: `response = await env.step(action)` (F9)
4. Press F5 → "Run & Debug"
5. Step through (F10: line-by-line, F11: into function)
6. Inspect variables (hover or Debug Console)

---

## 🎯 Tasks Explained in Detail

### Easy Task: Load User Data
**What agent must do**:
1. List files (find `users.csv`)
2. Read CSV (pandas)
3. Write to SQLite `users` table
4. Done?

**How grader scores**:
- Check if 'users' table exists
- Count rows
- Score = rows / 10.0 (so 10 rows = 1.0, 5 rows = 0.5)

**Mock agent solution**:
```python
import pandas as pd
df = pd.read_csv('users.csv')
df.to_sql('users', 'sqlite:///output.db', if_exists='replace', index=False)
```

---

### Medium Task: Standardize Date Formats
**What agent must do**:
1. List files (find `sales.csv`)
2. Read CSV with mixed date formats ("2024-01-15", "01/15/2024", "15-01-2024", etc.)
3. Parse all to datetime, standardize to YYYY-MM-DD
4. Write to SQLite `clean_sales` table
5. Done?

**How grader scores**:
- Check if 'clean_sales' table exists
- Read 'date' column
- Count how many match regex `^\d{4}-\d{2}-\d{2}$` (YYYY-MM-DD format)
- Score = correct_dates / 20.0

**Mock agent solution**:
```python
import pandas as pd
df = pd.read_csv('sales.csv')
# Try multiple date formats
for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d']:
    try:
        df['date'] = pd.to_datetime(df['date'], format=fmt)
        break
    except: pass
df['date'] = df['date'].dt.strftime('%Y-%m-%d')
df.to_sql('clean_sales', 'sqlite:///output.db', if_exists='replace', index=False)
```

---

### Hard Task: Compute Lifetime Value (LTV)
**What agent must do**:
1. List files (find `users.json` and `purchases.csv`)
2. Load `users.json` → filter where `marketing_opt_in == True`
3. Read `purchases.csv`
4. Merge users & purchases on user_id
5. Group by user_id, sum amounts (LTV)
6. Write to SQLite `ltv_report` table
7. Done?

**How grader scores**:
- Check if 'ltv_report' table exists
- Compare against ground truth: {1: 150.50, 3: 500.00, 4: 10.25}
- Count matching rows
- Score = correct_rows / 3.0 (so all 3 correct = 1.0)

**Mock agent solution**:
```python
import json, pandas as pd
with open('users.json') as f:
    users = json.load(f)
users_df = pd.DataFrame(users)
users_df = users_df[users_df['marketing_opt_in'] == True]

purchases = pd.read_csv('purchases.csv')
merged = users_df.merge(purchases, on='user_id')
ltv = merged.groupby('user_id')['amount'].sum().reset_index()
ltv.columns = ['user_id', 'total_ltv']
ltv.to_sql('ltv_report', 'sqlite:///output.db', if_exists='replace', index=False)
```

---

## 🧪 How Testing Works

**The mock agent acts as an automated test**:
1. Runs all 3 tasks
2. Solves each perfectly (1.0 score each)
3. Proves: Environment works, graders are correct, edge cases handled
4. Output confirms: Rewards, done flags, workflow

**If mock agent gets 1.0 scores → System is working correctly ✅**

---

## 📊 Example: Reward Progression

**Easy Task step-by-step**:
```
Step 1: list_files
  → Action: Get file list
  → Reward: +0.0 (score still 0.0)
  
Step 2: run_python (load CSV to DB)
  → Action: Execute pandas code
  → New score: 1.0 (all 10 rows loaded)
  → Reward: +1.0 (delta: 1.0 - 0.0)

Task complete: Final Score 1.00 ✅
```

This delta reward system lets agents learn incrementally—they're not just graded pass/fail, but rewarded for progress.

---

## 🔧 Optional: GPT-4 Integration

**Setup**:
```bash
# Set API key (Windows PowerShell)
$env:OPENAI_API_KEY = "sk-..."

# Or create .env file
echo 'OPENAI_API_KEY=sk-...' > .env

# Run real LLM agent
python inference.py
```

**Note**: Mock agent is fully functional without this. inference.py is an extension.

---

## 📂 Project Structure

```
data-janitor-env/
├── models.py              # Pydantic schemas
├── tasks.py               # Grader functions
├── env.py                 # Main environment class
├── mock_agent.py          # Test agent (main entrypoint)
├── inference.py           # Optional GPT-4 agent
├── requirements.txt       # Dependencies
├── setup.py               # Package setup
├── README.md              # This file
└── .gitignore             # Git ignore rules
```

---

## 🎓 Learning Path

1. **Beginner**: Run `python mock_agent.py` → see output → understand tasks
2. **Intermediate**: Read `models.py` → `tasks.py` → `env.py` in order
3. **Advanced**: Debug with VS Code → modify graders → test effects → add new tasks
4. **Expert**: Build your own agent (use inference.py as template)

---

## ✅ Verification Checklist

After setup:
- [ ] `python mock_agent.py` runs without errors
- [ ] All 3 tasks show "Final Score: 1.00"
- [ ] All rewards show "+1.00"
- [ ] Workspace cleanup happens (temp folder deleted)
- [ ] README is clear and complete
- [ ] `.gitignore` blocks venv/ and __pycache__/
- [ ] Files pushed to GitHub successfully

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: pandas` | Run `pip install -r requirements.txt` |
| `SQLite database is locked` | Close any open DB connections; temp files auto-cleanup |
| Script hangs | Check subprocess timeout in `env.py` (default 30s); increase if needed |
| Reward not +1.00 | Debug grader function; add print statements |
| GitHub push fails | Verify credentials: `git config user.email` and `git remote -v` |

---

## 📝 License

Open source. Modify and share freely.

---

**Questions?** Debug locally first → trace code → check graders → verify DB state → ask!