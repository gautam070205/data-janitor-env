import sqlite3
import pandas as pd
import re
from typing import Tuple


def grade_easy_task(db_path: str) -> Tuple[float, str]:
    """
    Grade the easy task: Load users.csv into 'users' table.
    Score = rows_loaded / 10.0
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
        if not cursor.fetchone():
            return 0.001, "Table 'users' does not exist"
        
        # Count rows
        cursor.execute("SELECT COUNT(*) FROM users;")
        row_count = cursor.fetchone()[0]
        
        conn.close()
        
        score = min(row_count / 10.0, 0.999)
        return score, f"Loaded {row_count}/10 rows into 'users' table"
    
    except Exception as e:
        return 0.001, f"Error grading easy task: {str(e)}"


def grade_medium_task(db_path: str) -> Tuple[float, str]:
    """
    Grade the medium task: Clean dates in 'clean_sales' table.
    Score = correct_dates / 20.0
    """
    try:
        conn = sqlite3.connect(db_path)
        
        # Check if table exists
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clean_sales';")
        if not cursor.fetchone():
            return 0.001, "Table 'clean_sales' does not exist"
        
        # Read date column
        df = pd.read_sql_query("SELECT date FROM clean_sales;", conn)
        conn.close()
        
        if df.empty:
            return 0.001, "No data in 'clean_sales' table"
        
        # Check date format YYYY-MM-DD
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        correct_dates = df['date'].str.match(pattern).sum()
        
        score = min(correct_dates / 20.0, 0.999)
        return score, f"Correct date format in {correct_dates}/20 rows"
    
    except Exception as e:
        return 0.001, f"Error grading medium task: {str(e)}"


def grade_hard_task(db_path: str) -> Tuple[float, str]:
    """
    Grade the hard task: Calculate LTV in 'ltv_report' table.
    Ground truth: {1: 150.50, 3: 500.00, 4: 10.25}
    Score = correct_rows / 3.0
    """
    try:
        conn = sqlite3.connect(db_path)
        
        # Check if table exists
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ltv_report';")
        if not cursor.fetchone():
            return 0.001, "Table 'ltv_report' does not exist"
        
        # Read data
        df = pd.read_sql_query("SELECT user_id, total_ltv FROM ltv_report;", conn)
        conn.close()
        
        if df.empty:
            return 0.001, "No data in 'ltv_report' table"
        
        # Ground truth
        ground_truth = {1: 150.50, 3: 500.00, 4: 10.25}
        
        correct_rows = 0
        for _, row in df.iterrows():
            user_id = int(row['user_id'])
            total_ltv = float(row['total_ltv'])
            if user_id in ground_truth and abs(total_ltv - ground_truth[user_id]) < 0.01:
                correct_rows += 1
        
        score = min(correct_rows / 3.0, 0.999)
        return score, f"Correct LTV calculations for {correct_rows}/3 users"
    
    except Exception as e:
        return 0.001, f"Error grading hard task: {str(e)}"