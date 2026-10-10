import sqlite3
import re
from typing import Dict, Any
from app.config import settings
from app.RAG.llm import call_llm

SQLITE_SCHEMA_PROMPT = """
You are a SQLite expert database engineer for MediAssist Health Network.
Translate the following natural language question into a single valid SQLite SELECT query.

Database Schema:
1. Table `claims`:
   - `claim_id` TEXT PRIMARY KEY (e.g. 'CLM-1001')
   - `patient_name` TEXT
   - `department` TEXT (e.g. 'Cardiology', 'Orthopedics', 'Pediatrics', 'ICU', 'Oncology')
   - `claim_amount` REAL (amount in INR)
   - `status` TEXT ('Approved', 'Pending', 'Rejected', 'Under Review')
   - `claim_date` DATE ('YYYY-MM-DD')
   - `escalated` BOOLEAN (1 = escalated, 0 = not escalated)
   - `insurance_provider` TEXT ('Star Health', 'Max Bupa', 'HDFC ERGO', 'ICICI Lombard', 'Ayushman Bharat')

2. Table `maintenance_tickets`:
   - `ticket_id` TEXT PRIMARY KEY (e.g. 'TCK-501')
   - `equipment_name` TEXT (e.g. 'Ventilator VentMax-2000', 'Infusion Pump SP-500', 'MRI Scanner 3T')
   - `category` TEXT (e.g. 'Critical Care', 'ICU', 'Radiology', 'Emergency')
   - `issue_type` TEXT (e.g. 'Calibration Failure', 'Battery Degradation', 'Cooling Unit Leak')
   - `status` TEXT ('Open', 'In Progress', 'Closed')
   - `priority` TEXT ('Low', 'Medium', 'High', 'Critical')
   - `created_date` DATE ('YYYY-MM-DD')
   - `technician_assigned` TEXT

Rules:
- Output ONLY the raw executable SQL statement. Do NOT include markdown code blocks, explanation text, or preambles.
- Use only SELECT statements. Never modify data.
"""

def extract_clean_sql(raw_output: str) -> str:
    """
    Step 2: Clean the raw LLM output to extract only the pure SQL statement.
    Removes markdown code fences (```sql ... ```), commentary, and newlines.
    """
    # Remove markdown code blocks if present
    cleaned = re.sub(r'```(?:sql)?', '', raw_output, flags=re.IGNORECASE)
    cleaned = re.sub(r'```', '', cleaned)
    cleaned = cleaned.strip()
    
    # Extract starting from SELECT
    match = re.search(r'(SELECT\s.*?(?:;|$))', cleaned, re.IGNORECASE | re.DOTALL)
    if match:
        sql = match.group(1).strip()
        if not sql.endswith(";"):
            sql += ";"
        return sql
    return cleaned

def sql_rag_chain(question: str) -> Dict[str, Any]:
    """
    Step 1: Translate NL question into SQL using LLM.
    Step 2: Clean raw LLM output to extract pure SQL statement.
    Step 3: Execute SQL against mediassist.db and pass results back to LLM for NL synthesis.
    """
    # Step 1: Prompt LLM for SQL translation
    prompt = f"{SQLITE_SCHEMA_PROMPT}\n\nQuestion: {question}\nSQL Query:"
    raw_sql_response = call_llm(prompt=prompt)
    
    # Step 2: Clean raw output
    clean_sql = extract_clean_sql(raw_sql_response)
    print(f"\n[SQL RAG Step 1 & 2] Question: '{question}' -> Cleaned SQL: '{clean_sql}'")
    
    # Step 3: Execute SQL against SQLite DB
    db_results = []
    columns = []
    error_msg = None
    
    try:
        conn = sqlite3.connect(settings.DB_PATH)
        cursor = conn.cursor()
        cursor.execute(clean_sql)
        rows = cursor.fetchall()
        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
        db_results = [dict(zip(columns, row)) for row in rows]
        conn.close()
    except Exception as e:
        error_msg = str(e)
        print(f"[SQL RAG Execution Error]: {error_msg}")
        
    # Step 3b: Pass query results back to LLM for natural language response
    if error_msg:
        answer = f"I executed the generated SQL query `{clean_sql}`, but encountered an error: {error_msg}."
    else:
        synthesis_prompt = f"""
Given the natural language question and the SQL query execution results from MediAssist Health Network database, generate a clear, professional, and concise natural language answer.

Question: {question}
Executed SQL Query: {clean_sql}
Database Results: {db_results}

Provide a direct answer with exact numbers and summaries.
"""
        answer = call_llm(prompt=synthesis_prompt, system_instruction="You are a healthcare analytics assistant.")
        
    return {
        "answer": answer,
        "executed_sql": clean_sql,
        "db_results": db_results,
        "retrieval_type": "sql_rag"
    }
