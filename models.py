from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from enum import Enum


class ActionType(str, Enum):
    RUN_PYTHON = "run_python"
    LIST_FILES = "list_files"
    READ_FILE = "read_file"


class DataJanitorAction(BaseModel):
    action_type: ActionType = Field(..., description="The type of action to perform")
    python_code: Optional[str] = Field(None, description="Python code to execute if action_type is run_python")
    file_path: Optional[str] = Field(None, description="File path to read if action_type is read_file")

    @validator('python_code')
    def validate_python_code(cls, v, values):
        if values.get('action_type') == ActionType.RUN_PYTHON and not v:
            raise ValueError('python_code is required when action_type is run_python')
        return v

    @validator('file_path')
    def validate_file_path(cls, v, values):
        if values.get('action_type') == ActionType.READ_FILE and not v:
            raise ValueError('file_path is required when action_type is read_file')
        return v


class DataJanitorObservation(BaseModel):
    task_description: str = Field(..., description="Description of the current task")
    stdout: str = Field("", description="Standard output from the last action")
    stderr: str = Field("", description="Standard error from the last action")
    files_in_workspace: List[str] = Field(default_factory=list, description="List of files in the workspace")
    database_info: Dict[str, Any] = Field(default_factory=dict, description="Information about the database state")
    current_score: float = Field(0.001, description="Current task score strictly between 0 and 1")


class EnvResponse(BaseModel):
    observation: DataJanitorObservation = Field(..., description="The current observation")
    reward: float = Field(..., description="The reward for the last action")
    done: bool = Field(..., description="Whether the episode is done")
    info: Dict[str, Any] = Field(default_factory=dict, description="Additional information")