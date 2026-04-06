import os
import json
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI
from env import DataJanitorEnv
from models import DataJanitorAction, ActionType

# Load environment variables from .env file
load_dotenv()


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
        
        # Get LLM configuration from environment variables
        api_base = os.getenv("API_BASE_URL")
        model_name = os.getenv("MODEL_NAME")
        hf_token = os.getenv("HF_TOKEN")
        
        # Create OpenAI client with configurable endpoint and credentials
        self.client = AsyncOpenAI(
            api_key=hf_token or os.getenv("OPENAI_API_KEY"),
            base_url=api_base or "https://api.openai.com/v1"
        )
        self.model_name = model_name or "gpt-4"
        self.conversation = [{"role": "system", "content": SYSTEM_PROMPT}]

    async def run(self):
        print(f"[START] {self.task_level.upper()}")
        
        response = self.env.reset()
        step_num = 0
        
        while not response.done and step_num < self.env.max_steps:
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
                    model=self.model_name,
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
                except json.JSONDecodeError:
                    print(f"[STEP] {step_num} invalid_json")
                    continue
                
                try:
                    action = DataJanitorAction(**action_data)
                except ValueError:
                    print(f"[STEP] {step_num} invalid_action")
                    continue
                
                # Execute action
                response = self.env.step(action)
                
                # Add result to conversation
                result_text = f"Reward: {response.reward:.3f}, Done: {response.done}, Current Score: {self.env._get_current_score():.3f}"
                self.conversation.append({"role": "assistant", "content": result_text})
                
                # Structured logging
                action_type = action.action_type.value if hasattr(action.action_type, 'value') else str(action.action_type)
                score = self.env._get_current_score()
                print(f"[STEP] {step_num} {action_type} reward={response.reward:.3f} score={score:.3f}")
                    
            except Exception as e:
                print(f"[STEP] {step_num} error {type(e).__name__}")
                break
        
        final_score = self.env._get_current_score()
        print(f"[END] {self.task_level.upper()} score={final_score:.3f} steps={step_num}")

    async def cleanup(self):
        self.env.cleanup()


async def main():
    # Check for required environment variables
    api_base = os.getenv("API_BASE_URL")
    model_name = os.getenv("MODEL_NAME")
    hf_token = os.getenv("HF_TOKEN")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    # At least one credential source must be provided
    if not hf_token and not openai_key:
        print("❌ ERROR: Neither HF_TOKEN nor OPENAI_API_KEY is set!")
        print("\nRequired environment variables:")
        print("  - API_BASE_URL (optional, defaults to OpenAI)")
        print("  - MODEL_NAME (optional, defaults to 'gpt-4')")
        print("  - HF_TOKEN or OPENAI_API_KEY (required)")
        print("\nExample setup:")
        print("  export API_BASE_URL=https://api.openai.com/v1")
        print("  export MODEL_NAME=gpt-4")
        print("  export HF_TOKEN=hf_...")
        print("  python inference.py")
        return
    
    print("✅ LLM Configuration:")
    print(f"  API_BASE_URL: {api_base or 'https://api.openai.com/v1'}")
    print(f"  MODEL_NAME: {model_name or 'gpt-4'}")
    print(f"  Credential: {'HF_TOKEN' if hf_token else 'OPENAI_API_KEY'}")
    print("\n🚀 Starting inference on all 3 tasks...\n")
    
    total_score = 0.0
    for task_level in ["easy", "medium", "hard"]:
        agent = DataEngineerAgent(task_level)
        try:
            await agent.run()
            total_score += agent.env._get_current_score()
        except Exception as e:
            print(f"[END] {task_level.upper()} error {type(e).__name__}")
        finally:
            agent.env.cleanup()


if __name__ == "__main__":
    asyncio.run(main())