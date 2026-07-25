# MCP Clinical Agent — Qwen 3.5 Benchmark

This report documents two consecutive end-to-end runs of the same 20-question benchmark against the bundled synthetic clinical dataset. Both runs used the real interactive CLI, local model, LangGraph agent, MCP server, read-only PostgreSQL role, and debug mode.

> **Result: 20/20 correct in run one and 20/20 correct in run two.**
>
> A perfect score in two runs is evidence for this model and runtime configuration, not proof that the application is perfect or deterministic. Local model output can vary between otherwise identical runs.

## Run Summary

| Metric | Run one | Run two |
|---|---:|---:|
| Correct answers | 20/20 (100%) | 20/20 (100%) |
| Total runtime | 1,185.44s (19.76 min) | 1,308.53s (21.81 min) |
| Median question time | 51.95s | 51.62s |
| 95th-percentile time | 110.95s | 135.45s |
| Total tool calls | 39 | 38 |
| Q19 exported rows | 509 | 509 |
| Q19 distinct patients | 509 | 509 |

The score was stable across these two runs, but the execution path was not identical. For example, run one initially generated invalid nested-aggregate SQL for question 14, received a real PostgreSQL error, corrected the query, and returned the right answer. Run two generated a valid subquery on its first attempt. End-to-end runtime also differed by 123.09 seconds.

## Test Environment

| Setting | Value |
|---|---|
| Benchmark date | July 25, 2026 |
| Model | `qwen3.5:9B` via local Ollama |
| Model artifact | Q4_K_M, approximately 6.6 GB |
| GPU | NVIDIA Tesla T4, 16 GB VRAM |
| Ollama server | `0.30.7` |
| Ollama Python client | `0.6.2` |
| LangGraph | `1.2.9` |
| MCP Python SDK | `1.28.1` |
| Debug mode | Enabled |
| Model thinking | Enabled (`think=True`) |
| Temperature | `0.2` |
| Context window | `16,384` tokens |
| Maximum generation | `4,096` tokens |
| Maximum tool rounds per prompt | `5` |
| Database | PostgreSQL 16 |
| Database role | `llm_user` with `SELECT` privileges |
| Query timeout | 60 seconds per PostgreSQL statement |
| Dataset | Synthetic Synthea-derived patients, encounters, and procedures |

The benchmark was completed on Ollama `0.30.7`; it should not be presented as evidence for every Ollama or Qwen release.

## Method

1. Each prompt was submitted through the real interactive `client.py` CLI with debug mode enabled.
2. The benchmark harness automated input, conversation resets, timing, and transcript capture. It did not call the graph, MCP server, or database directly.
3. A fresh conversation was started before every unrelated prompt.
4. Questions 17–19 shared one conversation because questions 18 and 19 refer to the procedure established by question 17.
5. Question 20 started a fresh conversation.
6. Every reported value was checked independently against PostgreSQL.
7. The question 19 CSV was checked for its header, row count, unique IDs, procedure description, and exact patient-ID set equality with a reference query.
8. A question passed only if its final answer, SQL semantics, ordering, distinct-count behavior, and requested side effect were correct.

The original grouping note said questions 16–18 were related. The actual dependency chain is 17–19: question 16 is independent, while question 19 refers to the patients identified by questions 17 and 18. The benchmark followed the logical dependency so question 19 had valid conversational context.

## Scorecards

### Run One

| # | Result | Time | Tool rounds | Tool sequence |
|---:|:---:|---:|---:|---|
| 1 | Pass | 30.67s | 1 | Schema |
| 2 | Pass | 13.54s | 2 | Schema → Query |
| 3 | Pass | 19.97s | 2 | Schema → Query |
| 4 | Pass | 16.88s | 2 | Schema → Query |
| 5 | Pass | 16.07s | 2 | Schema → Query |
| 6 | Pass | 35.94s | 2 | Schema → Query |
| 7 | Pass | 79.26s | 2 | Schema → Query |
| 8 | Pass | 61.55s | 2 | Schema → Query |
| 9 | Pass | 69.73s | 2 | Schema → Query |
| 10 | Pass | 108.30s | 2 | Schema → Query |
| 11 | Pass | 54.94s | 2 | Schema → Query |
| 12 | Pass | 45.93s | 2 | Schema → Query |
| 13 | Pass | 73.47s | 2 | Schema → Query |
| 14 | Pass | 105.82s | 3 | Schema → Failed query → Corrected query |
| 15 | Pass | 67.08s | 2 | Schema → Query |
| 16 | Pass | 161.39s | 2 | Schema → Query |
| 17 | Pass | 48.96s | 2 | Schema → Query |
| 18 | Pass | 48.25s | 1 | Query |
| 19 | Pass | 46.48s | 1 | CSV export |
| 20 | Pass | 81.21s | 3 | Required failed query → Schema → Corrected query |

### Run Two

| # | Result | Time | Tool rounds | Tool sequence |
|---:|:---:|---:|---:|---|
| 1 | Pass | 37.34s | 1 | Schema |
| 2 | Pass | 19.89s | 2 | Schema → Query |
| 3 | Pass | 33.29s | 2 | Schema → Query |
| 4 | Pass | 36.56s | 2 | Schema → Query |
| 5 | Pass | 32.96s | 2 | Schema → Query |
| 6 | Pass | 72.70s | 2 | Schema → Query |
| 7 | Pass | 104.73s | 2 | Schema → Query |
| 8 | Pass | 87.18s | 2 | Schema → Query |
| 9 | Pass | 73.67s | 2 | Schema → Query |
| 10 | Pass | 134.21s | 2 | Schema → Query |
| 11 | Pass | 52.20s | 2 | Schema → Query |
| 12 | Pass | 45.48s | 2 | Schema → Query |
| 13 | Pass | 66.63s | 2 | Schema → Query |
| 14 | Pass | 91.76s | 2 | Schema → Query |
| 15 | Pass | 51.03s | 2 | Schema → Query |
| 16 | Pass | 159.07s | 2 | Schema → Query |
| 17 | Pass | 41.29s | 2 | Schema → Query |
| 18 | Pass | 32.68s | 1 | Query |
| 19 | Pass | 49.28s | 1 | CSV export |
| 20 | Pass | 86.58s | 3 | Required failed query → Schema → Corrected query |

## Detailed Verified Results

The SQL shown below is from run two unless a run-specific difference is noted.

### 1. Schema discovery and relationships

**Prompt:** What tables are available in the database, what are their primary keys, and how are the tables related?

**Tool:** `get_database_schema`

**Answer:** The agent identified:

- `patients`, primary key `id`
- `encounters`, primary key `id`, with `patient → patients.id`
- `procedures`, primary key `id`, with `patient → patients.id` and `encounter → encounters.id`

**Verdict:** **Pass in both runs.**

### 2. Total patients

**Prompt:** How many patients are in the database?

```sql
SELECT COUNT(*) AS total_patients
FROM patients;
```

**Answer and verification:** 974.

**Verdict:** **Pass in both runs.**

### 3. Patients by gender

**Prompt:** Show me the number of patients for each gender.

```sql
SELECT COUNT(*) AS patient_count, gender
FROM patients
GROUP BY gender
ORDER BY gender;
```

| Gender | Patients |
|---|---:|
| F | 480 |
| M | 494 |

**Verdict:** **Pass in both runs.**

### 4. Total encounters

**Prompt:** How many clinical encounters are recorded?

```sql
SELECT COUNT(*) AS total_encounters
FROM encounters;
```

**Answer and verification:** 27,891.

**Verdict:** **Pass in both runs.**

### 5. Total procedure records

**Prompt:** How many procedure records are in the database?

```sql
SELECT COUNT(*) AS total_procedure_records
FROM procedures;
```

**Answer and verification:** 47,701.

**Verdict:** **Pass in both runs.**

### 6. Five most common encounter classes

**Prompt:** What are the five most common encounter classes?

```sql
SELECT encounterclass, COUNT(*) AS frequency
FROM encounters
WHERE encounterclass IS NOT NULL
GROUP BY encounterclass
ORDER BY frequency DESC
LIMIT 5;
```

| Encounter class | Records |
|---|---:|
| ambulatory | 12,537 |
| outpatient | 6,300 |
| urgentcare | 3,666 |
| emergency | 2,322 |
| wellness | 1,931 |

**Verdict:** **Pass in both runs.**

### 7. Average claim cost by encounter class

**Prompt:** What is the average total claim cost for each encounter class? Order the results from highest to lowest.

```sql
SELECT encounterclass,
       AVG(total_claim_cost) AS avg_total_claim_cost
FROM encounters
WHERE total_claim_cost IS NOT NULL
GROUP BY encounterclass
ORDER BY avg_total_claim_cost DESC;
```

| Encounter class | Average claim cost |
|---|---:|
| inpatient | $7,761.35 |
| urgentcare | $6,369.16 |
| emergency | $4,629.65 |
| wellness | $4,260.71 |
| ambulatory | $2,894.11 |
| outpatient | $2,237.30 |

**Verdict:** **Pass in both runs.**

### 8. Payer coverage by encounter class

**Prompt:** For each encounter class, what is the total amount covered by payers?

```sql
SELECT encounterclass,
       SUM(payer_coverage) AS total_payer_coverage
FROM encounters
WHERE payer_coverage IS NOT NULL
GROUP BY encounterclass
ORDER BY total_payer_coverage DESC;
```

| Encounter class | Total payer coverage |
|---|---:|
| ambulatory | $12,903,495.75 |
| wellness | $4,421,749.94 |
| outpatient | $3,777,758.35 |
| inpatient | $3,688,764.95 |
| emergency | $3,246,828.27 |
| urgentcare | $3,058,909.73 |

**Verdict:** **Pass in both runs.**

### 9. Five cities with the most patients

**Prompt:** Which five cities have the largest number of patients?

```sql
SELECT city,
       COUNT(DISTINCT id) AS patient_count
FROM patients
WHERE city IS NOT NULL
  AND city != ''
GROUP BY city
ORDER BY patient_count DESC
LIMIT 5;
```

| City | Patients |
|---|---:|
| Boston | 541 |
| Quincy | 80 |
| Cambridge | 45 |
| Revere | 42 |
| Chelsea | 39 |

**Verdict:** **Pass in both runs.**

### 10. Procedures reaching the most unique patients

**Prompt:** Which five procedures were performed on the greatest number of unique patients?

```sql
SELECT description,
       COUNT(DISTINCT patient) AS num_unique_patients
FROM procedures
GROUP BY description
ORDER BY num_unique_patients DESC
LIMIT 5;
```

| Procedure | Unique patients |
|---|---:|
| Assessment of health and social care needs (procedure) | 509 |
| Depression screening using Patient Health Questionnaire Two-Item score (procedure) | 500 |
| Depression screening (procedure) | 500 |
| Assessment of anxiety (procedure) | 437 |
| Assessment of substance use (procedure) | 436 |

**Verdict:** **Pass in both runs.**

### 11. Unique patients with an encounter

**Prompt:** How many unique patients have at least one encounter?

```sql
SELECT COUNT(DISTINCT patient) AS unique_patients_with_encounters
FROM encounters
WHERE patient IS NOT NULL;
```

**Answer and verification:** 974.

**Verdict:** **Pass in both runs.**

### 12. Unique patients with a procedure

**Prompt:** How many unique patients have at least one procedure?

```sql
SELECT COUNT(DISTINCT patient) AS unique_patient_count
FROM procedures
WHERE patient IS NOT NULL;
```

**Answer and verification:** 793.

**Verdict:** **Pass in both runs.**

### 13. Patients without encounters

**Prompt:** How many patients have no recorded encounters?

```sql
SELECT COUNT(*) AS patient_count_without_encounters
FROM patients p
LEFT JOIN encounters e ON p.id = e.patient
WHERE e.patient IS NULL;
```

**Answer and verification:** 0.

**Verdict:** **Pass in both runs.**

### 14. Average procedure records per patient

**Prompt:** Among patients who have at least one procedure, what is the average number of procedure records per patient?

Run two generated:

```sql
SELECT AVG(procedure_count) AS avg_procedures_per_patient
FROM (
    SELECT patient, COUNT(*) AS procedure_count
    FROM procedures
    GROUP BY patient
) AS patient_procedures;
```

**Answer and verification:** Approximately 60.15 procedure records.

In run one, the first attempt incorrectly nested `AVG(COUNT(*))` at one query level. PostgreSQL rejected it, after which the agent generated the valid subquery and returned the correct result. This was counted as a pass because autonomous tool-error recovery is an explicit application requirement.

**Verdict:** **Pass in both runs.**

### 15. Year with the most encounters

**Prompt:** Which calendar year had the largest number of encounters, and how many encounters occurred that year?

```sql
SELECT EXTRACT(YEAR FROM start) AS encounter_year,
       COUNT(*) AS num_encounters
FROM encounters
WHERE start IS NOT NULL
GROUP BY EXTRACT(YEAR FROM start)
ORDER BY num_encounters DESC
LIMIT 1;
```

**Answer and verification:** 2014, with 3,885 encounters.

**Verdict:** **Pass in both runs.**

### 16. Encounter class with the highest procedure density

**Prompt:** Among encounters that have at least one procedure, which encounter class has the highest average number of procedures per encounter?

```sql
SELECT e.encounterclass,
       COUNT(p.id) AS num_procedures,
       COUNT(DISTINCT p.encounter) AS num_encounters_with_procedures,
       ROUND(
           COUNT(p.id)::numeric / COUNT(DISTINCT p.encounter),
           2
       ) AS avg_procedures_per_encounter
FROM encounters e
JOIN procedures p ON e.id = p.encounter
GROUP BY e.encounterclass
ORDER BY avg_procedures_per_encounter DESC;
```

| Encounter class | Procedures | Encounters with procedures | Average |
|---|---:|---:|---:|
| wellness | 9,295 | 1,693 | 5.49 |
| outpatient | 14,958 | 3,317 | 4.51 |
| inpatient | 3,137 | 1,045 | 3.00 |
| ambulatory | 17,822 | 6,851 | 2.60 |
| emergency | 1,442 | 725 | 1.99 |
| urgentcare | 1,047 | 1,039 | 1.01 |

**Answer:** Wellness, at approximately 5.49 procedures per encounter.

**Verdict:** **Pass in both runs.**

### 17. Most frequent procedure

**Prompt:** Which procedure occurred most frequently, and how many times did it occur?

```sql
SELECT description, COUNT(*) AS frequency
FROM procedures
GROUP BY description
ORDER BY frequency DESC
LIMIT 1;
```

**Answer and verification:** Assessment of health and social care needs (procedure), 4,596 occurrences.

**Verdict:** **Pass in both runs.**

### 18. Unique patients receiving that procedure

**Prompt:** How many unique patients had that procedure?

```sql
SELECT COUNT(DISTINCT patient) AS unique_patients
FROM procedures
WHERE description =
    'Assessment of health and social care needs (procedure)';
```

**Answer and verification:** 509 unique patients.

**Verdict:** **Pass in both runs.**

### 19. CSV export

**Prompt:** Export one row for each of those unique patients to benchmark_patients.csv. Include the patient ID, first name, last name, and procedure description.

**Tool:** `export_query_to_csv`

```sql
SELECT DISTINCT
       p.id AS patient_id,
       p.first,
       p.last,
       pr.description AS procedure_description
FROM procedures pr
JOIN patients p ON pr.patient = p.id
WHERE pr.description =
    'Assessment of health and social care needs (procedure)'
ORDER BY p.id;
```

**Verification in each run:**

- File: `exports/benchmark_patients.csv`
- Columns: `patient_id`, `first`, `last`, `procedure_description`
- Data rows: 509
- Distinct patient IDs: 509
- Distinct procedure descriptions: 1
- Patient-ID set exactly equal to an independent PostgreSQL reference query: yes

**Verdict:** **Pass in both runs.**

### 20. SQL error recovery

**Prompt:** For this benchmark, first execute this exact SQL: SELECT patient_name FROM patients;. When it fails, correct the query and show me the first and last names of five patients.

Both runs used the required sequence:

1. `execute_readonly_query`

   ```sql
   SELECT patient_name FROM patients;
   ```

   PostgreSQL returned `column "patient_name" does not exist`.

2. `get_database_schema`

3. `execute_readonly_query`

   ```sql
   SELECT first, last
   FROM patients
   LIMIT 5;
   ```

| First name | Last name |
|---|---|
| Nikita578 | Erdman779 |
| Zane918 | Hodkiewicz467 |
| Quinn173 | Marquardt819 |
| Abel832 | Smitham825 |
| Edwin773 | Labadie908 |

**Verdict:** **Pass in both runs.** The exact invalid SQL was executed before schema inspection or correction.

## Model Configuration Comparison

| Model and run | Thinking | Scope | Observed result | Runtime |
|---|:---:|---|---:|---:|
| Gemma 4 12B, original manual run | On | 20 questions | 20/20 | Not recorded |
| Gemma 4 12B, documented run | On | 20 questions | 18/20 | 24.45 min |
| Gemma 4 12B, no-thinking run | Off | 20 questions | 18/20 | 4.28 min |
| Qwen 3.5 9B, runs one and two | On | 20 questions x 2 | 20/20, 20/20 | 19.76, 21.81 min |
| Qwen 3.5 9B, no-thinking run | Off | 20 questions | 18/20 | 12.11 min |

In this limited sample, thinking-enabled Qwen was more reliable than Gemma while remaining slow on the Tesla T4. This does not establish that Qwen is universally better, nor does it isolate whether the improvement comes from the model, tool-call serialization, Ollama's model-specific parser, or an interaction among those components.

The Qwen runs also included one narrow prompt correction for question 20. The original system prompt always required schema inspection before the first SQL query, which contradicted the user's explicit instruction to execute a known-invalid statement first. The corrected rule honors an explicit exact-SQL-first request while keeping schema-first behavior for ordinary database questions. It does not force a tool call on every interaction.

### No-thinking follow-up

Qwen 3.5 9B was then run through the complete benchmark with thinking disabled. It scored **18/20** in 726.44 seconds (12.11 minutes), with a 33.05-second median question time.

- Q19 exported 4,596 procedure-instance rows instead of one row for each of 509 unique patients. It also replaced the stored procedure description with an altered literal.
- Q20 executed the required invalid SQL first, but its corrected query concatenated `prefix`, `first`, and `suffix`, omitted `last`, and therefore did not answer the request.
- Q2 and Q5 returned correct results through SQL but skipped the system prompt's schema-first step.
- No turn ended with an unsupported zero-tool database answer.

Because the first no-thinking run was not 20/20, it was not repeated. Its runtime was roughly 39-44% lower than the two thinking-enabled Qwen runs, but these timings are observations from individual local runs rather than a controlled performance study.

## Limitations

- Two full runs are not a statistically meaningful reliability study.
- Temperature `0.2` reduces randomness but does not make model output deterministic.
- The same question already followed different valid and invalid-then-corrected SQL paths between these runs.
- The thinking/no-thinking Qwen timings are not a controlled performance experiment.
- Results apply to the documented model, quantization, prompt, application code, dataset, and hardware.
- The benchmark favors analytical warehouse questions and does not cover prompt injection, malicious SQL, concurrency, load, very large result sets, or production security.
- The dataset is synthetic and contains only three tables.
- A 20/20 score says that the final benchmark outcomes were correct; it does not mean every intermediate reasoning step was flawless.

## Conclusion

`qwen3.5:9B` completed two consecutive full benchmark runs without an incorrect final outcome. It correctly selected tools, generated SQL, maintained multi-turn context, exported an exact 509-patient CSV, and recovered from both an unplanned SQL error and the deliberately invalid query.

That is a useful portfolio result, but the defensible claim is **“20/20 in two documented runs under this configuration,”** not **“the agent is 100% accurate.”** The next meaningful improvement is an automated repeated evaluation harness that stores structured results and can compare models, runtime versions, accuracy, tool compliance, and latency over many runs.
