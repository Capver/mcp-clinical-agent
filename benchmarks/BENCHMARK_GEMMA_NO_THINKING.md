# MCP Clinical Agent — Gemma 4 12B No-Thinking Benchmark

This report documents a second complete run of the same 20-question benchmark used in [`BENCHMARK_GEMMA_THINKING.md`](BENCHMARK_GEMMA_THINKING.md). It evaluates the application after disabling Gemma's thinking channel to avoid malformed tool-call output while preserving autonomous tool selection.

> **Result: 18/20 correct (90%).**
>
> Every question that invoked an MCP tool passed independent verification. Questions 8 and 20 made zero tool calls and failed. Question 16—the repeated failure that motivated this iteration—passed correctly.

> **Configuration status:** Historical experiment. Post-benchmark diagnostics found no LangGraph request mutation and identified documented Ollama Gemma 4 parser risks. The application was subsequently restored to `think=True`.

## Thinking-Mode Comparison

| Metric | Thinking enabled | Thinking disabled |
|---|---:|---:|
| Model thinking | Enabled | Disabled |
| Temperature | `0.2` | `0.2` |
| Correct answers | 18/20 (90%) | 18/20 (90%) |
| Q8: payer coverage | Fail | Fail |
| Q16: procedures per encounter | Fail | Pass |
| Q20: SQL error recovery | Pass | Fail |
| Total runtime | 1,466.93s | 256.93s |
| Median question time | 50.45s | 12.07s |
| 95th-percentile time | 142.29s | 22.04s |
| Total tool calls | 34 | 33 |

The no-thinking run was approximately **5.7 times faster**, an 82.5% reduction in total runtime. This is a substantial usability improvement, but the unchanged accuracy score shows that disabling thinking did not solve general tool-use compliance.

## Test Environment

| Setting | Value |
|---|---|
| Benchmark date | July 25, 2026 |
| Model | `gemma4:12b` via local Ollama |
| GPU | NVIDIA Tesla T4, 16 GB VRAM |
| Debug mode | Enabled |
| Model thinking | Disabled (`think=False`) |
| Model temperature | `0.2` |
| Context window | `16,384` tokens |
| Maximum generation | `4,096` tokens |
| Maximum tool rounds per prompt | `5` |
| Database | PostgreSQL 16 |
| Database role | `llm_user` with `SELECT` privileges |
| Query timeout | 60 seconds per PostgreSQL statement |
| Dataset | Synthetic Synthea-derived patients, encounters, and procedures |

Debug mode recorded tool discovery, tool names and arguments, tool results, and tool-round counts. Model-provided thinking was unavailable because the setting under evaluation was disabled.

## Method

1. The exact prompts from the thinking-enabled run were submitted through the real interactive `client.py` CLI.
2. The benchmark harness automated typing, `/reset`, timing, and raw transcript capture; it did not invoke the agent graph or database directly.
3. A fresh conversation was started before every unrelated question.
4. Questions 17–19 shared one conversation because questions 18 and 19 refer to the result established by question 17.
5. Question 20 started a fresh conversation.
6. Every reported database value was independently verified using reference SQL through the same read-only PostgreSQL role.
7. The exported CSV was checked for its columns, row count, distinct patient count, procedure description, and exact row-set equality with a reference query.

The original prompt grouping said questions 16–18 were related. The actual dependency chain is 17–19, so this iteration used the same corrected grouping as the first documented benchmark.

### Pass Criteria

A question passed when:

- The final answer addressed the requested question.
- Reported values matched independent PostgreSQL verification.
- Requested ordering, limiting, distinct counting, and export behavior were honored.
- Tool-use claims were supported by the debug trace.
- For question 20, the exact invalid query was executed before a corrected query returned five real patient names.

## Scorecard

| # | Result | Time | Tool rounds | Tool sequence |
|---:|:---:|---:|---:|---|
| 1 | Pass | 25.14s | 1 | Schema |
| 2 | Pass | 9.39s | 2 | Schema → Query |
| 3 | Pass | 9.87s | 2 | Schema → Query |
| 4 | Pass | 9.40s | 2 | Schema → Query |
| 5 | Pass | 9.17s | 2 | Schema → Query |
| 6 | Pass | 13.11s | 2 | Schema → Query |
| 7 | Pass | 16.70s | 2 | Schema → Query |
| 8 | **Fail** | 22.04s | 0 | None |
| 9 | Pass | 12.42s | 2 | Schema → Query |
| 10 | Pass | 17.41s | 2 | Schema → Query |
| 11 | Pass | 10.16s | 2 | Schema → Query |
| 12 | Pass | 10.20s | 2 | Schema → Query |
| 13 | Pass | 10.89s | 2 | Schema → Query |
| 14 | Pass | 13.12s | 2 | Schema → Query |
| 15 | Pass | 12.63s | 2 | Schema → Query |
| 16 | Pass | 16.12s | 2 | Schema → Query |
| 17 | Pass | 12.06s | 2 | Schema → Query |
| 18 | Pass | 7.25s | 1 | Query |
| 19 | Pass | 12.08s | 1 | CSV export |
| 20 | **Fail** | 7.77s | 0 | None |

## Detailed Results

### 1. Schema discovery and relationships

**Prompt:** What tables are available in the database, what are their primary keys, and how are the tables related?

**Tool trace:** `get_database_schema`

**Answer:** The agent correctly identified:

- `patients`, primary key `id`
- `encounters`, primary key `id`, with `patient → patients.id`
- `procedures`, primary key `id`, with `patient → patients.id` and `encounter → encounters.id`

**Verdict:** **Pass.**

### 2. Total patients

**Prompt:** How many patients are in the database?

```sql
SELECT COUNT(*) FROM patients;
```

**Answer and verification:** 974.

**Verdict:** **Pass.**

### 3. Patients by gender

**Prompt:** Show me the number of patients for each gender.

```sql
SELECT gender, COUNT(*) AS patient_count
FROM patients
GROUP BY gender;
```

**Answer and verification:** 494 male (`M`) and 480 female (`F`) patients.

**Verdict:** **Pass.**

### 4. Total encounters

**Prompt:** How many clinical encounters are recorded?

```sql
SELECT COUNT(*) FROM encounters;
```

**Answer and verification:** 27,891.

**Verdict:** **Pass.**

### 5. Total procedure records

**Prompt:** How many procedure records are in the database?

```sql
SELECT COUNT(*) FROM procedures;
```

**Answer and verification:** 47,701.

**Verdict:** **Pass.**

### 6. Five most common encounter classes

**Prompt:** What are the five most common encounter classes?

```sql
SELECT encounterclass, COUNT(*) AS count
FROM encounters
GROUP BY encounterclass
ORDER BY count DESC
LIMIT 5;
```

| Encounter class | Records |
|---|---:|
| ambulatory | 12,537 |
| outpatient | 6,300 |
| urgentcare | 3,666 |
| emergency | 2,322 |
| wellness | 1,931 |

**Verdict:** **Pass.**

### 7. Average claim cost by encounter class

**Prompt:** What is the average total claim cost for each encounter class? Order the results from highest to lowest.

```sql
SELECT encounterclass, AVG(total_claim_cost) AS avg_total_claim_cost
FROM encounters
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

**Verdict:** **Pass.**

### 8. Total payer coverage by encounter class

**Prompt:** For each encounter class, what is the total amount covered by payers?

**Debug evidence:** No tool was called. The tool-round count was zero.

**Observed answer:** The model invented `claims`, `payments_summary`, and `claims_summary`, claimed it had analyzed the database, and fabricated FY24 totals including 1,245 claims and $4,892,340 in payer payments.

**Reference SQL:**

```sql
SELECT encounterclass, SUM(payer_coverage)
FROM encounters
GROUP BY encounterclass;
```

| Encounter class | Total payer coverage |
|---|---:|
| ambulatory | $12,903,495.75 |
| emergency | $3,246,828.27 |
| inpatient | $3,688,764.95 |
| outpatient | $3,777,758.35 |
| urgentcare | $3,058,909.73 |
| wellness | $4,421,749.94 |

**Verdict:** **Fail.** The answer was ungrounded and used nonexistent schema.

### 9. Cities with the most patients

**Prompt:** Which five cities have the largest number of patients?

```sql
SELECT city, COUNT(*) AS patient_count
FROM patients
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

**Verdict:** **Pass.**

### 10. Procedures reaching the most unique patients

**Prompt:** Which five procedures were performed on the greatest number of unique patients?

```sql
SELECT description, COUNT(DISTINCT patient) AS unique_patients
FROM procedures
GROUP BY description
ORDER BY unique_patients DESC
LIMIT 5;
```

| Procedure | Unique patients |
|---|---:|
| Assessment of health and social care needs (procedure) | 509 |
| Depression screening (procedure) | 500 |
| Depression screening using Patient Health Questionnaire Two-Item score (procedure) | 500 |
| Assessment of anxiety (procedure) | 437 |
| Assessment of substance use (procedure) | 436 |

The two procedures tied at 500 may appear in either order.

**Verdict:** **Pass.**

### 11. Unique patients with an encounter

**Prompt:** How many unique patients have at least one encounter?

```sql
SELECT COUNT(DISTINCT patient) FROM encounters;
```

**Answer and verification:** 974.

**Verdict:** **Pass.**

### 12. Unique patients with a procedure

**Prompt:** How many unique patients have at least one procedure?

```sql
SELECT COUNT(DISTINCT patient) FROM procedures;
```

**Answer and verification:** 793.

**Verdict:** **Pass.**

### 13. Patients without encounters

**Prompt:** How many patients have no recorded encounters?

```sql
SELECT COUNT(*)
FROM patients AS p
WHERE NOT EXISTS (
    SELECT 1
    FROM encounters AS e
    WHERE e.patient = p.id
);
```

**Answer and verification:** 0.

**Verdict:** **Pass.**

### 14. Average procedures per patient

**Prompt:** Among patients who have at least one procedure, what is the average number of procedure records per patient?

```sql
SELECT AVG(procedure_count) AS average_procedures
FROM (
    SELECT patient, COUNT(*) AS procedure_count
    FROM procedures
    GROUP BY patient
) AS counts;
```

**Answer:** Approximately 60.15.

**Verification:** 47,701 records across 793 patients, averaging 60.152585.

**Verdict:** **Pass.**

### 15. Year with the most encounters

**Prompt:** Which calendar year had the largest number of encounters, and how many encounters occurred that year?

```sql
SELECT EXTRACT(YEAR FROM start) AS encounter_year, COUNT(*) AS count
FROM encounters
GROUP BY encounter_year
ORDER BY count DESC
LIMIT 1;
```

**Answer and verification:** 2014 with 3,885 encounters.

**Verdict:** **Pass.**

### 16. Encounter class with the highest procedures-per-encounter average

**Prompt:** Among encounters that have at least one procedure, which encounter class has the highest average number of procedures per encounter?

```sql
SELECT e.encounterclass, AVG(proc_count) AS avg_procedures
FROM (
    SELECT encounter, COUNT(*) AS proc_count
    FROM procedures
    GROUP BY encounter
) AS p
JOIN encounters AS e ON e.id = p.encounter
GROUP BY e.encounterclass
ORDER BY avg_procedures DESC
LIMIT 1;
```

**Answer:** `wellness`, approximately 5.49 procedures per encounter.

**Verification:** 5.490254 across 1,693 wellness encounters that have at least one procedure.

**Verdict:** **Pass.** This question failed in the thinking-enabled benchmark and passed after disabling model thinking.

### 17. Most frequent procedure

**Prompt:** Which procedure occurred most frequently, and how many times did it occur?

```sql
SELECT description, COUNT(*) AS count
FROM procedures
GROUP BY description
ORDER BY count DESC
LIMIT 1;
```

**Answer and verification:** `Assessment of health and social care needs (procedure)`, 4,596 records.

**Verdict:** **Pass.**

### 18. Unique patients with that procedure

**Prompt:** How many unique patients had that procedure?

The agent correctly retained the procedure identified in question 17.

```sql
SELECT COUNT(DISTINCT patient)
FROM procedures
WHERE description = 'Assessment of health and social care needs (procedure)';
```

**Answer and verification:** 509 unique patients.

**Verdict:** **Pass.**

### 19. CSV export for those patients

**Prompt:** Export one row for each of those unique patients to benchmark_patients.csv. Include the patient ID, first name, last name, and procedure description.

```sql
SELECT DISTINCT
    p.id,
    p.first,
    p.last,
    pr.description
FROM patients AS p
JOIN procedures AS pr ON p.id = pr.patient
WHERE pr.description = 'Assessment of health and social care needs (procedure)';
```

**Tool:** `export_query_to_csv`

**Export verification:**

| Check | Result |
|---|---|
| File | `exports/benchmark_patients.csv` |
| Columns | `id`, `first`, `last`, `description` |
| Rows | 509 |
| Distinct patient IDs | 509 |
| Procedure descriptions | 1, matching the target procedure |
| Exact match with reference row set | Yes |

**Verdict:** **Pass.**

### 20. PostgreSQL error recovery

**Prompt:** For this benchmark, first execute this exact SQL: SELECT patient_name FROM patients;. When it fails, correct the query and show me the first and last names of five patients.

**Debug evidence:** No tool was called. The tool-round count was zero.

**Observed answer:** The model claimed it had reviewed the schema and was executing a query, changed the required SQL by adding `LIMIT 5`, and invented five generic names such as “John Doe” and “Jane Smith.”

The expected first step was:

```sql
SELECT patient_name FROM patients;
```

PostgreSQL should reject that query because `patient_name` does not exist. A valid correction would select `first` and `last`, for example:

```sql
SELECT first, last
FROM patients
LIMIT 5;
```

Independent execution returned real synthetic names, including:

| First | Last |
|---|---|
| Nikita578 | Erdman779 |
| Zane918 | Hodkiewicz467 |
| Quinn173 | Marquardt819 |
| Abel832 | Smitham825 |
| Edwin773 | Labadie908 |

Because the query has no `ORDER BY`, PostgreSQL does not guarantee which five valid rows are returned.

**Verdict:** **Fail.** The model neither executed the required failing query nor grounded its replacement answer.

## Performance Summary

| Metric | Result |
|---|---:|
| Total benchmark time | 256.93s (4.28 minutes) |
| Mean question time | 12.85s |
| Median question time | 12.07s |
| 95th-percentile time | 22.04s |
| Fastest question | Q18 at 7.25s |
| Slowest question | Q1 at 25.14s |
| Total tool rounds | 33 |
| Total tool calls | 33 |
| Schema calls | 16 |
| Read-only query calls | 16 |
| CSV export calls | 1 |

The first iteration took 24.45 minutes. Disabling model thinking reduced the second run to 4.28 minutes while retaining the same model, temperature, context window, database, and prompts.

## Findings

### What improved

- Question 16 used valid structured tool calls and returned the correct result.
- Total runtime fell by approximately 82.5%.
- Median latency fell from 50.45 seconds to 12.07 seconds.
- All 18 questions that invoked MCP tools passed independent verification.
- Multi-turn context and the 509-row export remained correct.

### What remains unreliable

- Question 8 failed in both complete benchmark iterations.
- Question 20 regressed from a correct error-recovery sequence to an ungrounded answer.
- Both failures made zero tool calls while falsely implying database knowledge or execution.
- Disabling thinking improved one tool-parser failure but did not solve the broader risk of unsupported action claims.

### Engineering implications

The second run argues against treating either temperature or thinking mode as a complete reliability solution. The strongest predictor of correctness in both iterations was actual MCP use: once the model invoked the tools, its answers were correct.

That does not justify forcing a tool in every interaction. Legitimate requests may ask for explanations, reformatting, or summaries already supported by conversation history. A narrower future safeguard could reject demonstrably false execution claims—for example, an answer stating that SQL was executed when the tool-round count is zero—without requiring tool use on ordinary conversational turns.

Repeated evaluation is also necessary. A single pass/fail result for each question cannot distinguish a stable capability from a prompt that succeeds intermittently.

## Post-Iteration Diagnosis and Reversion

The unchanged score raised a reasonable architectural question: was LangGraph altering the prompt, dropping tools, or leaking conversation state before the failed responses? A separate isolation test examined the exact boundary instead of inferring from final answers.

| Layer | Trials | Thinking modes | Structured first responses | Request comparison |
|---|---:|---|---:|---|
| Direct Ollama, no LangGraph | 30 | 15 enabled, 15 disabled | 30/30 | Canonical request |
| LangGraph boundary, stopped before tool execution | 30 | 15 enabled, 15 disabled | 30/30 | 30/30 exactly matched canonical request |

Each layer tested questions 8, 16, and 20 five times per thinking mode. The direct requests used the exact application system prompt, discovered MCP tool schemas, model, temperature, context window, and generation limit. The graph-boundary recorder captured the arguments passed to `AsyncClient.chat` before any MCP tool could execute.

Additional checks confirmed that:

- The benchmark harness issued `/reset` before both failed prompts.
- Each failed turn began with a fresh conversation ID and the exact requested text.
- The MCP-to-Ollama tool definitions used ordinary function schemas and were identical in direct and graph trials.
- Ollama was version `0.30.7`; the Python client was `0.6.2`; LangGraph was `1.2.9`.

The 60 successful isolation trials do not make the earlier failures imaginary. They show that the graph does not deterministically create them and that the behavior is intermittent. Ollama's issue tracker documents the same failure class for Gemma 4: [tool calls leaking into text when a system prompt, tools, and `think:false` are combined](https://github.com/ollama/ollama/issues/15539), and [Gemma tool-call parser failures producing malformed call syntax](https://github.com/ollama/ollama/issues/15241).

The most defensible conclusion is a stochastic interaction at the Gemma-output/Ollama-parser boundary rather than a LangGraph request-construction bug. The architecture still exposes the problem because an ungrounded text response is accepted as final, but it does not appear to cause the malformed or missing structured call.

Since disabling thinking did not improve the complete benchmark score and reasoning visibility was preferred over latency, the code was restored to its original `think=True` behavior. No universal tool requirement or automatic no-tool retry was added.

## Limitations

- This is one full run of one local model after one configuration change.
- The benchmark has only 20 questions over three synthetic tables.
- The two complete iterations are useful comparisons, but they are not enough for statistical reliability estimates.
- Local inference timing may vary with hardware load and model caching.
- Independent verification establishes correctness for this dataset, not general clinical accuracy.
- The evaluation was serial and did not test concurrency or load.
- The project is not intended for medical diagnosis, treatment, or use with real patient information.

## Conclusion

The no-thinking run again scored **18/20 (90%)**, but it changed the system's operating profile substantially. Disabling Gemma's thinking channel fixed the observed Q16 structured-tool failure and made the complete benchmark approximately 5.7 times faster. However, the persistent Q8 failure and new Q20 regression show that tool-use reliability remains the key limitation.

The result is therefore a meaningful engineering improvement, not evidence that the agent is fully reliable. The next benchmark iteration should evaluate a narrowly scoped integrity safeguard and repeat each question multiple times rather than relying on another single pass.

After the isolation work described above, the thinking-disabled configuration was reverted. This report remains a record of the experiment, not a description of the application's current model settings.
