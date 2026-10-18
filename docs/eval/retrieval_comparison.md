Rank of the first chunk from the expected document that contains the answer (top-10 candidates; "miss" = not retrieved). Same RBAC filter for both.

| Query | Role | Dense only | Hybrid (dense+BM25, RRF) | Hybrid + rerank (top-3) |
|---|---|---|---|---|
| `What is the correct IV cannula size for a paediatric patient under 5kg?` | nurse | 1 | 1 | 1 |
| `What does fault code F-09 mean on the RadiPro MX-150?` | technician | 1 | 1 | 1 |
| `DriveFlow IP-200 fault F-03` | technician | 5 | 2 | 1 |
| `Package rate for ICD-10 I21.4` | billing_executive | 8 | 1 | 2 |
| `J44.1 typical length of stay` | billing_executive | miss | 6 | 1 |
| `CURB-65 score disposition` | doctor | 1 | 1 | 1 |
| `Ceftriaxone standard dose and tier` | doctor | 2 | 1 | 1 |
| `aPTT critical value heparin` | doctor | 1 | 1 | 1 |
| `Bowie-Dick test frequency SterilPro 3000` | technician | 1 | 1 | 1 |
| `VIP score cannula change` | nurse | 1 | 1 | 1 |
| `Provident Fund PF contribution rate` | nurse | 1 | 1 | 1 |
| `EXCL-03 exclusion` | billing_executive | 2 | 2 | 1 |
| **Answer in top-3** | | **9/12** | **11/12** | **12/12** |
