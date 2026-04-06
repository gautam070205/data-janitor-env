#!/usr/bin/env python3
"""
Simple OpenEnv API server for Hugging Face Spaces
Handles POST /reset and other endpoints required by the competition
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import sys
from env import DataJanitorEnv
from tasks import grade_easy_task, grade_medium_task, grade_hard_task

# Global environment instances
envs = {}

class OpenEnvHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        if self.path == "/" or self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {"status": "running", "message": "Data Janitor Environment API"}
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        """Handle POST requests"""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body.decode()) if body else {}
        except:
            data = {}
        
        # Handle /reset endpoint
        if self.path == "/reset":
            task_level = data.get("task_level", "easy")
            
            if task_level not in ["easy", "medium", "hard"]:
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                response = {"error": "Invalid task_level"}
                self.wfile.write(json.dumps(response).encode())
                return
            
            # Create new environment
            env = DataJanitorEnv(task_level, max_steps=10)
            obs = env.reset()
            
            # Store environment for this session
            session_id = id(env)
            envs[session_id] = env
            
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            
            response = {
                "session_id": session_id,
                "observation": {
                    "task_description": obs.observation.task_description,
                    "files_in_workspace": obs.observation.files_in_workspace,
                    "database_info": obs.observation.database_info
                },
                "reward": obs.reward,
                "done": obs.done
            }
            self.wfile.write(json.dumps(response).encode())
        
        # Handle /step endpoint
        elif self.path == "/step":
            session_id = data.get("session_id")
            action_data = data.get("action")
            
            if not session_id or session_id not in envs:
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                response = {"error": "Invalid session_id"}
                self.wfile.write(json.dumps(response).encode())
                return
            
            env = envs[session_id]
            
            try:
                from models import DataJanitorAction
                action = DataJanitorAction(**action_data)
                response_obj = env.step(action)
                
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                
                response = {
                    "observation": {
                        "task_description": response_obj.observation.task_description,
                        "files_in_workspace": response_obj.observation.files_in_workspace,
                        "database_info": response_obj.observation.database_info,
                        "stdout": response_obj.observation.stdout,
                        "stderr": response_obj.observation.stderr
                    },
                    "reward": response_obj.reward,
                    "done": response_obj.done
                }
                self.wfile.write(json.dumps(response).encode())
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                response = {"error": str(e)}
                self.wfile.write(json.dumps(response).encode())
        
        else:
            self.send_response(404)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {"error": "Endpoint not found"}
            self.wfile.write(json.dumps(response).encode())
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

def main() -> None:
    port = int(os.getenv("PORT", 7860))
    server = HTTPServer(("0.0.0.0", port), OpenEnvHandler)
    print(f"✅ OpenEnv API server running on port {port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
