import os
import json
import asyncio
from openai import AsyncOpenAI
from env import DataJanitorEnv
from models import DataJanitorAction, ActionType


SYSTEM_PROMPT = """You are an expert data engineer solving data cleaning challenges. Your goal is to write and execute Python code that transforms raw messy data into a clean SQLite database.

## Task Instructions
1. You will receive a task description with mixed-format data files (CSV, JSON, etc.)
2. Examine the files carefully
3. Write Python code to clean and load data into output.db
4. Use pandas and/or sqlite3 to manipulate data
5. Save results to appropriately named SQLite tables

## Important Rules
- ALWAYS respond with ONLY valid JSON, no explanations
- Use action_type "run_python" to execute Python code
- Import pandas, sqlite3, json, csv as needed in your code
- Reference files at workspace root (e.g., "users.csv", "users.json")
- Save output to "output.db" (already exists)
- Be careful with data types - use float/int/str appropriately

## JSON Response Format (REQUIRED)
Respond with ONLY this JSON structure:
{
  "action_type": "run_python",
  "python_code": "import pandas as pd\\n..."
}

DO NOT write any text outside the JSON. NO explanations, NO markdown code blocks, ONLY JSON."""

class DataEngineerAgent:
    def __init__(self, task_level: str):
        self.task_level = task_level
        self.env = DataJanitorEnv(task_level, max_steps=10)
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.conversation = [{"role": "system", "content": SYSTEM_PROMPT}]

    async def run(self):
        print(f"\n{'='*60}")
        print(f"[START] {self.task_level.upper()} TASK (GPT-4)")
        print(f"{'='*60}")
        
        response = self.env.reset()
        step_num = 0
        
        print(f"Task: {response.observation.task_description}")
        print(f"Initial Files: {', '.join(response.observation.files_in_workspace)}")
        print(f"Database: {response.observation.database_info}\n")
        
        while not response.done and step_num < self.env.max_steps:
            step_num += 1
            step_num += 1
            
            # Add current observation to conversation
            obs_text = f"""
Task: {response.observation.task_description}
Files: {', '.join(response.observation.files_in_workspace)}
Database: {response.observation.database_info}
Stdout: {response.observation.stdout}
Stderr: {response.observation.stderr}
"""
            self.conversation.append({"role": "user", "content": obs_text})
            
            # Get action from LLM
            try:
                llm_response = await self.client.chat.completions.create(
                    model="gpt-4",
                    messages=self.conversation,
                    max_tokens=500,
                    temperature=0.1
                )
                
                action_json = llm_response.choices[0].message.content.strip()
                
                # Handle LLM wrapping JSON in markdown code blocks
                if action_json.startswith("```"):
                    action_json = action_json.split("```")[1].strip()
                    if action_json.startswith("json"):
                        action_json = action_json[4:].strip()
                
                try:
                    action_data = json.loads(action_json)
                except json.JSONDecodeError as json_err:
                    print(f"[STEP {step_num}] ⚠️ Invalid JSON from LLM: {json_err}")
                    print(f"Response was: {action_json[:100]}...")
                    continue  # Skip to next step
                
                try:
                    action = DataJanitorAction(**action_data)
                except ValueError as val_err:
                    print(f"[STEP {step_num}] ⚠️ Invalid action format: {val_err}")
                    continue  # Skip to next step
                
                print(f"[STEP {step_num}] Action: {action.action_type.value if hasattr(action.action_type, 'value') else action.action_type}")
                
                # Execute action
                response = self.env.step(action)
                
                # Add result to conversation
                result_text = f"Reward: {response.reward:.3f}, Done: {response.done}, Current Score: {self.env._get_current_score():.3f}"
                self.conversation.append({"role": "assistant", "content": result_text})
                
                if response.reward > 0:
                    print(f"  └─ Reward: +{response.reward:.3f} (Total Score: {self.env._get_current_score():.3f})")
                else:
                    print(f"  └─ Reward: {response.reward:.3f} (Total Score: {self.env._get_current_score():.3f})")
                    
            except Exception as e:
                print(f"[STEP {step_num}] ❌ Error: {type(e).__name__}: {e}")
                break
        
        final_score = self.env._get_current_score()
        print(f"\n{'='*60}")
        print(f"[END] Task: {self.task_level.upper()} | Final Score: {final_score:.3f} | Steps: {step_num}")
        print(f"{'='*60}\n")

    async def cleanup(self):
        self.env.cleanup()


async def main():
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key or api_key == "sk-your-api-key-here":
        print("❌ ERROR: OPENAI_API_KEY not set or invalid!")
        print("\nTo use inference.py with GPT-4:")
        print("  1. Copy .env.example to .env")
        print("  2. Add your OpenAI API key: export OPENAI_API_KEY=sk-...")
        print("  3. Run: python inference.py")
        print("\nAlternatively, use mock_agent.py (no API key required):")
        print("  python mock_agent.py")
        return
    
    print("✅ OpenAI API key found!")
    print("🚀 Starting GPT-4 agent inference on all 3 tasks...\n")
    
    total_score = 0.0
    for task_level in ["easy", "medium", "hard"]:
        agent = DataEngineerAgent(task_level)
        try:
            await agent.run()
            total_score += agent.env._get_current_score()
        except Exception as e:
            print(f"❌ Task {task_level} failed: {type(e).__name__}: {e}\n")
        finally:
            await agent.cleanup()
    
    print(f"\n{'='*60}")
    print(f"📊 FINAL RESULTS: Total Score: {total_score:.3f} / 3.0")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())