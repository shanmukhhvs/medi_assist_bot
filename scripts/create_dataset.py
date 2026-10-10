import os
import sqlite3
from datetime import datetime, timedelta
import random

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DOCS_DIR = os.path.join(DATA_DIR, "raw_documents")
DB_PATH = os.path.join(DATA_DIR, "mediassist.db")

def init_sqlite_db():
    print(f"Initializing SQLite database at: {DB_PATH}")
    os.makedirs(DATA_DIR, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create claims table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS claims (
        claim_id TEXT PRIMARY KEY,
        patient_name TEXT,
        department TEXT,
        claim_amount REAL,
        status TEXT,
        claim_date DATE,
        escalated BOOLEAN,
        insurance_provider TEXT
    );
    """)
    
    # Create maintenance_tickets table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS maintenance_tickets (
        ticket_id TEXT PRIMARY KEY,
        equipment_name TEXT,
        category TEXT,
        issue_type TEXT,
        status TEXT,
        priority TEXT,
        created_date DATE,
        technician_assigned TEXT
    );
    """)
    
    # Check if empty, populate if needed
    cursor.execute("SELECT COUNT(*) FROM claims;")
    if cursor.fetchone()[0] == 0:
        print("Populating claims table...")
        departments = ["Cardiology", "Orthopedics", "Neurology", "Pediatrics", "Oncology", "General Surgery", "ICU"]
        statuses = ["Approved", "Pending", "Rejected", "Under Review"]
        providers = ["Star Health", "Max Bupa", "HDFC ERGO", "ICICI Lombard", "Ayushman Bharat"]
        
        sample_claims = [
            ("CLM-1001", "Aarav Sharma", "Cardiology", 125000.0, "Approved", "2026-09-01", 0, "Star Health"),
            ("CLM-1002", "Priya Patel", "Orthopedics", 85000.0, "Rejected", "2026-09-03", 1, "Max Bupa"),
            ("CLM-1003", "Rajesh Kumar", "Neurology", 210000.0, "Approved", "2026-09-05", 0, "HDFC ERGO"),
            ("CLM-1004", "Ananya Gupta", "Pediatrics", 45000.0, "Pending", "2026-09-10", 0, "ICICI Lombard"),
            ("CLM-1005", "Vikram Singh", "Oncology", 340000.0, "Rejected", "2026-09-12", 1, "Star Health"),
            ("CLM-1006", "Sanya Verma", "ICU", 195000.0, "Under Review", "2026-09-15", 1, "Ayushman Bharat"),
            ("CLM-1007", "Rohan Mehta", "General Surgery", 115000.0, "Approved", "2026-09-18", 0, "Max Bupa"),
            ("CLM-1008", "Kavita Reddy", "Cardiology", 280000.0, "Rejected", "2026-09-20", 1, "HDFC ERGO"),
            ("CLM-1009", "Amitabh Joshi", "Orthopedics", 92000.0, "Approved", "2026-09-22", 0, "Star Health"),
            ("CLM-1010", "Neha Nair", "Pediatrics", 38000.0, "Rejected", "2026-09-25", 1, "ICICI Lombard"),
            ("CLM-1011", "Deepak Chawla", "ICU", 420000.0, "Under Review", "2026-09-28", 1, "Star Health"),
            ("CLM-1012", "Sunita Rao", "Oncology", 275000.0, "Approved", "2026-10-01", 0, "Max Bupa"),
        ]
        cursor.executemany("INSERT INTO claims VALUES (?,?,?,?,?,?,?,?)", sample_claims)
        
    cursor.execute("SELECT COUNT(*) FROM maintenance_tickets;")
    if cursor.fetchone()[0] == 0:
        print("Populating maintenance_tickets table...")
        sample_tickets = [
            ("TCK-501", "Ventilator VentMax-2000", "Critical Care", "Calibration Failure", "Open", "High", "2026-09-10", "Tech Anand"),
            ("TCK-502", "Infusion Pump SP-500", "ICU", "Battery Degradation", "In Progress", "Medium", "2026-09-12", "Tech Anand"),
            ("TCK-503", "MRI Scanner 3T", "Radiology", "Cooling Unit Leak", "Open", "Critical", "2026-09-15", "Tech Rajesh"),
            ("TCK-504", "ECG Monitor Cardia-X", "Cardiology", "Display Glitch", "Closed", "Low", "2026-09-18", "Tech Anand"),
            ("TCK-505", "Defibrillator LifeLine Pro", "Emergency", "Self-test Alarm", "Open", "High", "2026-09-20", "Tech Suresh"),
            ("TCK-506", "Dialysis Machine MedFlow-90", "Nephrology", "Filter Pressure Error", "In Progress", "High", "2026-09-22", "Tech Anand"),
            ("TCK-507", "Anesthesia Workstation AI-20", "Operation Theater", "Gas Flow Valve Failure", "Open", "Critical", "2026-09-25", "Tech Rajesh"),
            ("TCK-508", "Patient Monitor PM-100", "General Ward", "Sensor Disconnect", "Closed", "Low", "2026-09-28", "Tech Anand"),
        ]
        cursor.executemany("INSERT INTO maintenance_tickets VALUES (?,?,?,?,?,?,?,?)", sample_tickets)
        
    conn.commit()
    conn.close()
    print("Database initialization complete.")

def generate_markdown_documents():
    print("Generating raw medical documents...")
    collections = ["general", "clinical", "nursing", "billing", "equipment"]
    for col in collections:
        os.makedirs(os.path.join(DOCS_DIR, col), exist_ok=True)
        
    # 1. General Collection Documents
    with open(os.path.join(DOCS_DIR, "general", "hr_handbook_and_faq.md"), "w") as f:
        f.write("""# MediAssist Health Network HR Policy & Staff Handbook

## Section 1: Working Hours & Staff Leave Policy
All hospital staff must adhere to regular shift schedules. Full-time employees are entitled to 18 days of Paid Leave (PL), 12 days of Sick Leave (SL), and 10 days of Casual Leave (CL) per calendar year.
Emergency leave requests must be submitted through the MediAssist HR Portal at least 4 hours prior to shift commencement.

## Section 2: Code of Conduct & Patient Privacy (HIPAA / DISHA)
Every staff member (doctors, nurses, billing staff, technicians) must maintain strict patient confidentiality. Unauthorised disclosure of patient health information (PHI) to third parties is strictly prohibited and subject to immediate termination.

## Section 3: General Staff FAQs
### Q: How do I request a replacement ID badge?
A: Visit the IT & Security Helpdesk on the Ground Floor, Block B with an approved request form signed by your Department Manager.

### Q: What is the procedure for night shift meal allowances?
A: Staff working continuous night shifts exceeding 8 hours are eligible for a Rs. 250 meal voucher redeemable at the main hospital cafeteria.
""")

    # 2. Clinical Collection Documents
    with open(os.path.join(DOCS_DIR, "clinical", "clinical_treatment_protocols.md"), "w") as f:
        f.write("""# MediAssist Clinical Protocols & Drug Formulary Reference

## Section 1: Paediatric Emergency & IV Access Guidelines
### Subsection 1.1: IV Cannula Sizing for Paediatric Patients
For paediatric patients under 5kg (neonates and infants), the recommended IV cannula size is **24 Gauge (Yellow)** or **26 Gauge (Violet)**.
For paediatric patients between 5kg and 15kg, use **22 Gauge (Blue)** cannula.

### Subsection 1.2: Emergency Paediatric Anaphylaxis Protocol
In case of acute anaphylactic reaction in paediatric patients:
1. Administer Intramuscular (IM) Adrenaline (1:1000) at 0.01 mg/kg (maximum single dose 0.3 mg).
2. Secure airway and administer 100% high-flow oxygen.
3. Establish rapid IV access with 24G cannula and start normal saline bolus at 20 mL/kg.

## Section 2: Sepsis Bundle & Standard Drug Formulary
### Subsection 2.1: Adult Sepsis Initial Management
Administer broad-spectrum IV antibiotics within 1 hour of sepsis recognition.
First-line antibiotic choice: **Piperacillin-Tazobactam 4.5g IV Q6H** or **Meropenem 1g IV Q8H** plus **Vancomycin 15-20 mg/kg IV Q12H** if MRSA suspected.

### Subsection 2.2: Standard Drug Dosage Table
| Drug Name | Standard Indication | Adult Dose | Paediatric Dose | Route |
|---|---|---|---|---|
| Paracetamol | Pyrexia / Mild Pain | 500mg - 1000mg Q6H | 15mg/kg Q6H | Oral / IV |
| Adrenaline (1:1000) | Anaphylaxis / Cardiac Arrest | 0.5mg IM | 0.01mg/kg IM | IM / IV |
| Amoxicillin-Clavulanate | Community Acquired Pneumonia | 1.2g Q8H | 30mg/kg Q8H | IV |
| Ondansetron | Anti-emetic / Nausea | 4mg - 8mg Q8H | 0.15mg/kg Q8H | IV / Oral |
""")

    # 3. Nursing Collection Documents
    with open(os.path.join(DOCS_DIR, "nursing", "icu_nursing_procedures.md"), "w") as f:
        f.write("""# MediAssist ICU Nursing Procedures & Care Guidelines

## Section 1: Central Line Care & Infection Control
Nursing staff must perform daily inspection of all central venous catheter (CVC) insertion sites.
Sterile dressing changes must be conducted every 7 days or immediately if the dressing becomes damp, loosened, or visibly soiled. Clean insertion site with 2% Chlorhexidine in 70% Isopropyl Alcohol.

## Section 2: Patient IV Cannula Insertion & Maintenance
### Subsection 2.1: Cannula Site Monitoring
All peripheral IV sites must be assessed every 4 hours using the Visual Infusion Phlebitis (VIP) Score.
If VIP score is 2 or higher, immediately remove the cannula and re-site in the opposite limb.

### Subsection 2.2: Paediatric Nursing Precautions
When caring for paediatric patients under 5kg requiring IV fluids:
- Use micro-drip infusion sets equipped with volumetric infusion pumps (e.g. Infusion Pump SP-500).
- Confirm cannula placement with 24 Gauge cannula before infusing hypertonic solutions.
- Monitor hourly fluid intake strictly to prevent fluid overload.
""")

    # 4. Billing Collection Documents
    with open(os.path.join(DOCS_DIR, "billing", "insurance_billing_guidelines.md"), "w") as f:
        f.write("""# MediAssist Insurance Billing & Claims Submission Guide

## Section 1: Insurance Billing Codes & ICD-10 Cross Reference
Billing executives must ensure all submitted claims include accurate ICD-10 diagnostic codes and CPT procedure codes:
- **ICD-10 J96.00**: Acute respiratory failure, unspecified
- **ICD-10 A41.9**: Sepsis, unspecified organism
- **ICD-10 T78.2XXA**: Anaphylactic shock, initial encounter
- **CPT 99214**: Outpatient physician visit, moderate complexity (Fee: Rs. 1,500)
- **CPT 36000**: Introduction of needle or intracatheter, vein (IV insertion) (Fee: Rs. 450)

## Section 2: Claim Submission & Escalation Procedure
Claims must be uploaded to the TPA insurance portal within 48 hours of patient discharge.
If a claim is rejected due to "Document Discrepancy", the billing executive must escalate to the Senior Billing Manager within 24 hours.

## Section 3: Pricing & Procurement Directory
- Standard ICU Daily Bed Rate: Rs. 15,000 / day
- Ventilator Usage Charge: Rs. 5,000 / day
- Emergency Room Consultation: Rs. 2,500
""")

    # 5. Equipment Collection Documents
    with open(os.path.join(DOCS_DIR, "equipment", "equipment_maintenance_manual.md"), "w") as f:
        f.write("""# MediAssist Medical Equipment Operation & Maintenance Manual

## Section 1: Syringe Infusion Pump SP-500 Operation & Calibration
### Subsection 1.1: Maintenance Schedule & Calibration
The Syringe Pump SP-500 requires biannual occlusion pressure calibration (every 6 months).
Calibration Procedure:
1. Connect 50 mL syringe filled with distilled water to pressure transducer tester.
2. Set flow rate to 20 mL/hr and initiate infusion.
3. Verify that High Pressure Alarm triggers precisely between 800 mmHg and 900 mmHg.
4. Record calibration timestamp in the MediAssist Maintenance Log.

## Section 2: Mechanical Ventilator VentMax-2000 Maintenance
### Subsection 2.1: Oxygen Sensor & Flow Transducer Inspection
Bi-weekly preventive maintenance required for all VentMax-2000 units in Critical Care.
Check O2 cell voltage output; if output drops below 10 mV in ambient air (21% O2), replace the cell immediately (Part No. VM-O2-99).

### Subsection 2.2: Troubleshooting Error Code E-04 (Flow Fault)
Error Code E-04 indicates expiratory flow sensor calibration drift.
Solution: Perform automated flow sensor zeroing calibration via Technician Service Menu > Calibration > Expiratory Sensor.
""")

    print("Raw document creation complete.")

if __name__ == "__main__":
    init_sqlite_db()
    generate_markdown_documents()
