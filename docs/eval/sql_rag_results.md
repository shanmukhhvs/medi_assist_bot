6/6 questions match the hand-written reference SQL.

### How many billing claims were escalated last month?

- Generated SQL: `SELECT COUNT(*) AS escalated_claims_last_month FROM claims WHERE status = 'escalated' AND submitted_date >= date('2024-12-01') AND submitted_date < date('2024-12-28');`
- Rows: `[{'escalated_claims_last_month': 0}]`
- Reference result: `[(0,)]` → ✅ match
- Answer: There were 0 billing claims escalated last month.

### How many claims are escalated in total?

- Generated SQL: `SELECT COUNT(*) AS total_escalated_claims FROM claims WHERE status = 'escalated';`
- Rows: `[{'total_escalated_claims': 8}]`
- Reference result: `[(8,)]` → ✅ match
- Answer: The total number of escalated claims is 8.

### What is the total approved amount for approved claims?

- Generated SQL: `SELECT SUM(approved_amount) AS total_approved_amount FROM claims WHERE status = 'approved';`
- Rows: `[{'total_approved_amount': 2442700.0}]`
- Reference result: `[(2442700.0,)]` → ✅ match
- Answer: The total approved amount for approved claims is 2,442,700 INR.

### Which insurer has the highest total claimed amount?

- Generated SQL: `SELECT insurer, SUM(claimed_amount) AS total_claimed_amount FROM claims GROUP BY insurer ORDER BY total_claimed_amount DESC LIMIT 1;`
- Rows: `[{'insurer': 'Bajaj Allianz', 'total_claimed_amount': 1353000.0}]`
- Reference result: `[('Bajaj Allianz', 1353000.0)]` → ✅ match
- Answer: The insurer with the highest total claimed amount is Bajaj Allianz, with a total claimed amount of INR 1,353,000.

### Which equipment category has the most open maintenance tickets?

- Generated SQL: `SELECT category, COUNT(*) AS open_ticket_count 
FROM maintenance_tickets 
WHERE status = 'open' 
GROUP BY category 
ORDER BY open_ticket_count DESC 
LIMIT 1;`
- Rows: `[{'category': 'radiology', 'open_ticket_count': 4}]`
- Reference result: `[('radiology', 4)]` → ✅ match
- Answer: The equipment category with the most open maintenance tickets is 'radiology' with 4 open tickets.

### How many maintenance tickets are escalated for the RadiPro MX-150?

- Generated SQL: `SELECT COUNT(*) AS escalated_tickets FROM maintenance_tickets WHERE status = 'escalated' AND equipment_name = 'RadiPro MX-150';`
- Rows: `[{'escalated_tickets': 3}]`
- Reference result: `[(3,)]` → ✅ match
- Answer: There are 3 escalated maintenance tickets for the RadiPro MX-150.
