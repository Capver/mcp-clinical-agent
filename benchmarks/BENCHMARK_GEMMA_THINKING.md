# MCP Clinical Agent — Gemma 4 12B Thinking Benchmark

This report documents one end-to-end benchmark run of MCP Clinical Agent against the bundled synthetic clinical dataset. The run exercised schema discovery, aggregation, joins, distinct-patient analysis, multi-turn context, CSV export, and PostgreSQL error recovery through the actual CLI, local model, MCP server, and read-only database role.

> **Result: 18/20 correct (90%).**
>
> This documented rerun did not reproduce the earlier manually observed 20/20 result. Questions 8 and 16 failed because the model returned unrelated answers without calling a tool. The failures are retained here because they expose a real reliability limitation that a larger evaluation suite should measure.

## Test Environment

| Setting | Value |
|---|---|
| Benchmark date | July 25, 2026 |
| Model | `gemma4:12b` via local Ollama |
| GPU | NVIDIA Tesla T4, 16 GB VRAM |
| Debug mode | Enabled |
| Model temperature | `0.2` |
| Model thinking | Enabled (`think=True`) |
| Context window | `16,384` tokens |
| Maximum generation | `4,096` tokens |
| Maximum tool rounds per prompt | `5` |
| Database | PostgreSQL 16 |
| Database role used by MCP | `llm_user` with `SELECT` privileges |
| Query timeout | 60 seconds per PostgreSQL statement |
| Dataset | Synthetic Synthea-derived patients, encounters, and procedures |

Debug mode exposed tool discovery, model-provided thinking, tool names and arguments, tool results, and the tool-round count for every prompt. This report preserves the auditable evidence—generated SQL, tool sequence, returned values, timings, and final answers—without reproducing the full verbose thinking stream.

## Method

1. PostgreSQL and Ollama were run locally.
2. The benchmark used the real `client.py` CLI and its ordinary LangGraph/MCP execution path.
3. A new conversation thread was started between unrelated questions.
4. Questions 17–19 shared one thread because questions 18 and 19 depend on the procedure identified in question 17.
5. Question 20 started a new thread.
6. Every data result was independently checked with reference SQL executed through the same read-only PostgreSQL role.
7. The CSV produced by question 19 was inspected for its columns, row count, distinct patient count, and procedure description.

The supplied grouping note said questions 16–18 were related. The actual dependency chain is questions 17–19: question 16 is independent, while question 19 refers to the unique patients established by questions 17 and 18. The benchmark followed the logical 17–19 grouping so question 19 would have valid conversational context.

### Pass Criteria

A question passed when:

- The final answer addressed the requested question.
- All reported values matched independent PostgreSQL verification.
- Any requested ordering, limiting, distinct counting, or export behavior was honored.
- For question 20, the exact invalid query was attempted before a corrected query succeeded.

Latency is measured end to end. It includes local model inference, schema inspection, MCP calls, database execution, retries, and final-answer generation; it is not raw PostgreSQL query latency.

## Scorecard

| # | Result | Time | Tool rounds | Tool sequence |
|---:|:---:|---:|---:|---|
| 1 | Pass | 32.15s | 1 | Schema |
| 2 | Pass | 16.27s | 2 | Schema → Query |
| 3 | Pass | 24.20s | 2 | Schema → Query |
| 4 | Pass | 16.80s | 2 | Schema → Query |
| 5 | Pass | 19.97s | 2 | Schema → Query |
| 6 | Pass | 35.67s | 2 | Schema → Query |
| 7 | Pass | 46.10s | 2 | Schema → Query |
| 8 | **Fail** | 29.50s | 0 | None |
| 9 | Pass | 72.82s | 2 | Schema → Query |
| 10 | Pass | 125.83s | 2 | Schema → Query |
| 11 | Pass | 48.86s | 2 | Schema → Query |
| 12 | Pass | 77.48s | 2 | Schema → Query |
| 13 | Pass | 90.96s | 2 | Schema → Query |
| 14 | Pass | 142.29s | 2 | Schema → Query |
| 15 | Pass | 118.51s | 2 | Schema → Query |
| 16 | **Fail** | 52.03s | 0 | None |
| 17 | Pass | 60.55s | 2 | Schema → Query |
| 18 | Pass | 40.77s | 1 | Query |
| 19 | Pass | 91.65s | 1 | CSV export |
| 20 | Pass | 324.52s | 3 | Query failure → Schema → Corrected query |

## Detailed Results

### 1. Schema discovery and relationships

**Prompt:** What tables are available in the database, what are their primary keys, and how are the tables related?

**Debug evidence:** Called `get_database_schema`.

**Final result:** The agent identified:

- `patients`, primary key `id`
- `encounters`, primary key `id`, with `patient → patients.id`
- `procedures`, primary key `id`, with `patient → patients.id` and `encounter → encounters.id`

**Verification:** PostgreSQL reported all three tables, all three primary keys, and the three stated foreign keys.

**Verdict:** **Pass.** The answer correctly described the physical relationships. It did not mention that the foreign-key columns are nullable, but cardinality/nullability was not explicitly requested.

### 2. Total patients

**Prompt:** How many patients are in the database?

**Generated SQL:** `SELECT COUNT(*) FROM patients;`

**Final answer:** 974 patients.

**Verification:** 974.

**Verdict:** **Pass.**

### 3. Patients by gender

**Prompt:** Show me the number of patients for each gender.

**Generated SQL:** `SELECT gender, COUNT(*) AS patient_count FROM patients GROUP BY gender;`

**Final answer:** 494 male patients and 480 female patients.

**Verification:** `M = 494`, `F = 480`.

**Verdict:** **Pass.**

### 4. Total encounters

**Prompt:** How many clinical encounters are recorded?

**Generated SQL:** `SELECT COUNT(*) FROM encounters;`

**Final answer:** 27,891 encounters.

**Verification:** 27,891.

**Verdict:** **Pass.**

### 5. Total procedure records

**Prompt:** How many procedure records are in the database?

**Generated SQL:** `SELECT COUNT(*) FROM procedures;`

**Final answer:** 47,701 procedure records.

**Verification:** 47,701.

**Verdict:** **Pass.**

### 6. Five most common encounter classes

**Prompt:** What are the five most common encounter classes?

**Generated SQL:**

```sql
SELECT encounterclass, COUNT(*) AS count
FROM encounters
GROUP BY encounterclass
ORDER BY count DESC
LIMIT 5;
```

**Final answer:**

| Rank | Encounter class | Count |
|---:|---|---:|
| 1 | ambulatory | 12,537 |
| 2 | outpatient | 6,300 |
| 3 | urgentcare | 3,666 |
| 4 | emergency | 2,322 |
| 5 | wellness | 1,931 |

**Verification:** All five classes, counts, and rankings matched.

**Verdict:** **Pass.**

### 7. Average claim cost by encounter class

**Prompt:** What is the average total claim cost for each encounter class? Order the results from highest to lowest.

**Generated SQL:**

```sql
SELECT
    encounterclass,
    AVG(total_claim_cost) AS average_total_claim_cost
FROM encounters
GROUP BY encounterclass
ORDER BY average_total_claim_cost DESC;
```

**Final answer:**

| Encounter class | Average total claim cost |
|---|---:|
| inpatient | $7,761.35 |
| urgentcare | $6,369.16 |
| emergency | $4,629.65 |
| wellness | $4,260.71 |
| ambulatory | $2,894.11 |
| outpatient | $2,237.30 |

**Verification:** Every value and the descending order matched after rounding to cents.

**Verdict:** **Pass.**

### 8. Total payer coverage by encounter class

**Prompt:** For each encounter class, what is the total amount covered by payers?

**Debug evidence:** No tool was called. The tool-round count was zero.

**Observed answer:** The model returned a generic description of a patient-facing clinical assistant and suggested questions such as asking about medications or recent appointments. It did not address payer coverage.

**Reference result:**

| Encounter class | Total payer coverage |
|---|---:|
| ambulatory | $12,903,495.75 |
| emergency | $3,246,828.27 |
| inpatient | $3,688,764.95 |
| outpatient | $3,777,758.35 |
| urgentcare | $3,058,909.73 |
| wellness | $4,421,749.94 |

Reference SQL:

```sql
SELECT encounterclass, SUM(payer_coverage) AS total_payer_coverage
FROM encounters
GROUP BY encounterclass;
```

**Verdict:** **Fail.** The model ignored an answerable warehouse question and failed to use the available tools.

### 9. Cities with the most patients

**Prompt:** Which five cities have the largest number of patients?

**Generated SQL:**

```sql
SELECT city, COUNT(*) AS patient_count
FROM patients
WHERE city IS NOT NULL
  AND city != ''
GROUP BY city
ORDER BY patient_count DESC
LIMIT 5;
```

**Final answer:** Boston 541, Quincy 80, Cambridge 45, Revere 42, and Chelsea 39.

**Verification:** All five cities, counts, and rankings matched.

**Verdict:** **Pass.**

### 10. Procedures reaching the most unique patients

**Prompt:** Which five procedures were performed on the greatest number of unique patients?

**Generated SQL:**

```sql
SELECT
    description,
    COUNT(DISTINCT patient) AS unique_patients
FROM procedures
GROUP BY description
ORDER BY unique_patients DESC
LIMIT 5;
```

**Final answer:**

| Procedure | Unique patients |
|---|---:|
| Assessment of health and social care needs (procedure) | 509 |
| Depression screening using Patient Health Questionnaire Two-Item score (procedure) | 500 |
| Depression screening (procedure) | 500 |
| Assessment of anxiety (procedure) | 437 |
| Assessment of substance use (procedure) | 436 |

**Verification:** All five procedures and counts matched. The two depression-screening procedures tie at 500, so their relative ordering is not significant.

**Verdict:** **Pass.**

### 11. Unique patients with an encounter

**Prompt:** How many unique patients have at least one encounter?

**Generated SQL:** `SELECT COUNT(DISTINCT patient) FROM encounters;`

**Final answer:** 974.

**Verification:** 974.

**Verdict:** **Pass.**

### 12. Unique patients with a procedure

**Prompt:** How many unique patients have at least one procedure?

**Generated SQL:** `SELECT COUNT(DISTINCT patient) FROM procedures WHERE patient IS NOT NULL;`

**Final answer:** 793.

**Verification:** 793.

**Verdict:** **Pass.**

### 13. Patients without encounters

**Prompt:** How many patients have no recorded encounters?

**Generated SQL:**

```sql
SELECT COUNT(*)
FROM patients AS p
WHERE NOT EXISTS (
    SELECT 1
    FROM encounters AS e
    WHERE e.patient = p.id
);
```

**Final answer:** Zero; every patient has at least one encounter.

**Verification:** 0.

**Verdict:** **Pass.**

### 14. Average procedures per patient

**Prompt:** Among patients who have at least one procedure, what is the average number of procedure records per patient?

**Generated SQL:**

```sql
SELECT AVG(count_per_patient) AS average_procedures
FROM (
    SELECT COUNT(*) AS count_per_patient
    FROM procedures
    GROUP BY patient
) AS subquery;
```

**Final answer:** Approximately 60.15 procedure records per patient.

**Verification:** 60.152585. There are no procedure records with a null `patient`, so the generated grouping matches the requested population.

**Verdict:** **Pass.**

### 15. Year with the most encounters

**Prompt:** Which calendar year had the largest number of encounters, and how many encounters occurred that year?

**Generated SQL:**

```sql
SELECT
    EXTRACT(YEAR FROM start) AS encounter_year,
    COUNT(*) AS count
FROM encounters
WHERE start IS NOT NULL
GROUP BY 1
ORDER BY 2 DESC
LIMIT 1;
```

**Final answer:** 2014 with 3,885 encounters.

**Verification:** 2014, 3,885.

**Verdict:** **Pass.**

### 16. Encounter class with the highest procedures-per-encounter average

**Prompt:** Among encounters that have at least one procedure, which encounter class has the highest average number of procedures per encounter?

**Debug evidence:** No tool was called. The tool-round count was zero.

**Observed answer:** The model changed the requested grouping from encounter class to county, invented a `fact_measures` table and `count_of_procedures` column, and returned malformed SQL containing `FROM t1` and `GROUP BY .count_#`.

**Reference SQL:**

```sql
WITH procedure_counts AS (
    SELECT encounter, COUNT(*) AS procedure_count
    FROM procedures
    WHERE encounter IS NOT NULL
    GROUP BY encounter
)
SELECT
    e.encounterclass,
    AVG(pc.procedure_count) AS average_procedure_count
FROM procedure_counts AS pc
JOIN encounters AS e
  ON e.id = pc.encounter
GROUP BY e.encounterclass
ORDER BY average_procedure_count DESC
LIMIT 1;
```

**Reference result:** `wellness`, averaging 5.490254 procedure records across its 1,693 encounters that have at least one procedure.

**Verdict:** **Fail.** The answer did not address the question, invented nonexistent schema, and bypassed the tools that could have grounded it.

### 17. Most frequent procedure

**Prompt:** Which procedure occurred most frequently, and how many times did it occur?

**Generated SQL:**

```sql
SELECT description, COUNT(*) AS occurrence_count
FROM procedures
GROUP BY description
ORDER BY occurrence_count DESC
LIMIT 1;
```

**Final answer:** Assessment of health and social care needs (procedure), 4,596 occurrences.

**Verification:** 4,596.

**Verdict:** **Pass.**

### 18. Unique patients with that procedure

**Prompt:** How many unique patients had that procedure?

**Context:** Continued the question 17 conversation without a reset.

**Generated SQL:**

```sql
SELECT COUNT(DISTINCT patient) AS unique_patient_count
FROM procedures
WHERE description =
    'Assessment of health and social care needs (procedure)';
```

**Final answer:** 509 unique patients.

**Verification:** 509.

**Verdict:** **Pass.**

### 19. CSV export for those patients

**Prompt:** Export one row for each of those unique patients to benchmark_patients.csv. Include the patient ID, first name, last name, and procedure description.

**Context:** Continued the questions 17–18 conversation without a reset.

**Tool:** `export_query_to_csv`

**Generated SQL:**

```sql
SELECT DISTINCT
    p.id,
    p.first,
    p.last,
    pr.description
FROM procedures AS pr
JOIN patients AS p
  ON pr.patient = p.id
WHERE pr.description =
    'Assessment of health and social care needs (procedure)';
```

**Tool result:** `exports/benchmark_patients.csv` created with 509 rows.

**Independent file verification:**

- Columns: `id`, `first`, `last`, `description`
- Rows: 509
- Distinct patient IDs: 509
- Distinct procedure descriptions: 1
- Procedure description: Assessment of health and social care needs (procedure)

**Verdict:** **Pass.**

### 20. PostgreSQL error recovery

**Prompt:** For this benchmark, first execute this exact SQL: SELECT patient_name FROM patients;. When it fails, correct the query and show me the first and last names of five patients.

**Debug trace:**

1. Called `execute_readonly_query` with the exact requested SQL:

   ```sql
   SELECT patient_name FROM patients;
   ```

2. PostgreSQL returned:

   ```text
   column "patient_name" does not exist
   LINE 1: SELECT patient_name FROM patients;
                     ^
   ```

3. Called `get_database_schema`.
4. Identified the real `first` and `last` columns.
5. Called `execute_readonly_query` with:

   ```sql
   SELECT first, last
   FROM patients
   LIMIT 5;
   ```

**Final answer:**

| First name | Last name |
|---|---|
| Nikita578 | Erdman779 |
| Zane918 | Hodkiewicz467 |
| Quinn173 | Marquardt819 |
| Abel832 | Smitham825 |
| Edwin773 | Labadie908 |

**Verification:** The invalid query was attempted first, the PostgreSQL error was surfaced through MCP, and all five corrected-query rows matched.

**Verdict:** **Pass.** The recovery was logically correct but operationally expensive at 324.52 seconds.

## Performance Summary

| Metric | Result |
|---|---:|
| Total end-to-end time | 1,466.93s (24.45 minutes) |
| Mean time per question | 73.35s |
| Median time per question | 50.45s |
| 95th-percentile time | 142.29s |
| Fastest question | Q2 at 16.27s |
| Slowest question | Q20 at 324.52s |
| Total tool rounds | 34 |
| Total tool calls | 34 |
| Schema calls | 16 |
| Read-only query calls | 17 |
| CSV export calls | 1 |

The long timings primarily reflect local inference and repeated schema/tool cycles. They should not be interpreted as evidence that the underlying SQL statements took tens or hundreds of seconds.

## Targeted Failure Rerun

After the full benchmark, questions 8 and 16 were repeated in fresh debug-mode conversations. The original `0.2` temperature was tested first; both prompts were then run once at `0.0` as a small comparison. These follow-up runs do not replace the original 18/20 result.

| Question | Full run (`0.2`) | Fresh rerun (`0.2`) | Fresh rerun (`0.0`) |
|---|---|---|---|
| 8. Payer coverage by encounter class | Fail; 0 tool rounds | Pass; 2 tool rounds | Pass; 2 tool rounds |
| 16. Highest procedures-per-encounter average | Fail; 0 tool rounds | Fail; 0 tool rounds | Fail; 0 tool rounds |

On both successful question 8 reruns, the model inspected the schema and executed the correct grouped sum. All six totals matched the reference result above.

On both question 16 reruns, the model's reasoning stated that it should inspect the schema, but it emitted malformed tool-call-like text rather than a structured tool call. The agent therefore had no `tool_calls` payload to execute and ended with zero tool rounds. Lowering the temperature did not correct that failure mode in this limited test.

### Fix validation

Because the malformed syntax appeared in the model's thinking channel, the next experiment disabled Ollama thinking while restoring the original `0.2` temperature. Tool selection remained autonomous: the graph did not force a tool call or retry an ordinary tool-free response.

Question 16 then passed in **four out of four fresh conversations**—three focused experimental runs and one run through the temporarily updated application. Every run selected the schema and query tools and returned `wellness` at approximately `5.49` procedures per encounter. One run initially generated an invalid SQL alias, received the PostgreSQL error, corrected the query, and still reached the verified result.

The experiment temporarily exposed `MODEL_THINKING = False` in `config.py` and passed it to Ollama rather than hard-coding `think=True`. The system prompt was also clarified without forcing tool use.

This is promising evidence for the parser-interaction diagnosis, not proof that the full benchmark is now 20/20. A complete repeated benchmark is still needed.

The subsequent complete run in [`BENCHMARK_GEMMA_NO_THINKING.md`](BENCHMARK_GEMMA_NO_THINKING.md) again scored 18/20: question 16 passed, question 8 failed again, and question 20 regressed. A later isolation test sent the three unstable prompts directly to Ollama and through the LangGraph boundary with thinking both enabled and disabled. All 60 responses contained structured tool calls, and all 30 graph requests exactly matched their direct equivalents.

Those results, together with documented Ollama Gemma 4 parser defects, point to an intermittent Gemma-output/Ollama-parser boundary rather than prompt or tool-schema mutation by LangGraph. Because disabling thinking did not improve full-run accuracy and has its own documented parser risk, the experiment was reverted; the current application again uses `think=True`.

## Findings

### What worked

- All 17 ordinary database questions that actually invoked MCP tools returned correct results.
- The linked questions 17–19 correctly retained conversational context.
- The CSV export produced one row per distinct patient with the requested data.
- The agent recovered from a real PostgreSQL error after executing the exact invalid query requested in question 20.
- The restricted role was sufficient for all read-only analysis and export queries.

### What failed

- Questions 8 and 16 required warehouse data but the model made zero tool calls.
- Question 8 returned an unrelated generic assistant introduction.
- Question 16 hallucinated nonexistent schema and malformed SQL.
- Debug mode made these failures easy to distinguish from SQL or MCP failures: the database was never contacted.

### Engineering implications

The failures are not explained by LangGraph changing the initial request: captured graph requests matched direct Ollama requests exactly. The evidence instead points to intermittent model-output or Ollama Gemma-parser behavior. Requiring a tool on every turn would still be an overcorrection because it would interfere with legitimate tool-free interactions; any future safeguard should target unsupported database-execution claims rather than all no-tool answers.

The 324.52-second recovery case also shows that correctness and usability need separate evaluation dimensions. A production-oriented benchmark should track:

- Answer correctness
- Grounding/tool-use compliance
- SQL validity
- Tool rounds and retries
- End-to-end latency
- Export correctness
- Failure recovery

## Limitations

- The headline score is one full stochastic run of one local model; targeted follow-ups covered two prompts at two temperatures and four additional Q16 fix-validation runs.
- The benchmark contains only 20 questions over three synthetic tables.
- Independent verification confirms logical correctness for this dataset, not general clinical accuracy.
- The evaluation was run serially and does not test concurrency or load.
- The model-provided thinking trace is diagnostic output, not a stable or independently validated explanation.
- The project is not intended for medical diagnosis, treatment, or production use with real patient information.

## Conclusion

The documented result is **18/20 (90%)**, with strong SQL/tool performance once MCP was invoked and two serious tool-use failures where it was not. That result is less flattering than the earlier 20/20 manual run, but it is more useful: it demonstrates both the system’s working capabilities and the specific reliability boundary that should guide the next iteration.
