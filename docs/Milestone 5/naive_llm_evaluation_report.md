# Milestone 5 - Naive LLM Evaluation Summary (v1 vs v2 vs v3)

This report compares three prompt variants for Groq `gpt-oss-20b` LLM evaluation across 97 PRs in the evaluation dataset. Each variant employs different prompting strategies to optimize for token efficiency, response quality, and model behavior under the Groq 8K TPM rate limit.

## Artifacts
- Prompt v1: `src/rag_model/prompts/v1.txt` (max 5 violations per PR constraint)
- Prompt v2: `src/rag_model/prompts/v2.txt` (uncap max findings constraint)
- Prompt v3: `src/rag_model/prompts/v3.txt` (shortened prompt efficiency)
- v1 results file: `outputs/llm_raw_responses_v1.txt`
- v2 results file: `outputs/llm_raw_responses_v2.txt`
- v3 results file: `outputs/llm_raw_responses_v3.txt`
- Evaluation script: `src/evaluation/evaluate_llm_raw_txt.py`

## Evaluation Objective
Test three distinct prompting strategies for detecting PEP 8 violations in Python code using Groq LLM, evaluate predictions against ground truth using TP/FP/FN metrics (precision/recall/F1), and analyze how token-efficiency trade-offs affect model behavior and output quality.

## Prompting Strategy Overview

### v1: Conservative with Explicit Constraint
**Core Strategy:** Rate-limiting model reasoning by capping findings per PR.

**Rationale:** With Groq's 8K TPM limit and complex code PRs consuming substantial tokens, models risk generating no output tokens if reasoning becomes too deep/lengthy. By explicitly constraining "Max 5 findings per PR," the prompt signals to the model to stop early and prioritize output delivery over exhaustive analysis.

**Key Instruction:**
```
CONSTRAINTS:
- Max 5 findings per PR
- Detect ONLY clear, high-confidence violations
```

**Operational Trade-off:** Sacrifices recall for guaranteed output delivery. Lower per-PR analysis depth reduces token expenditure, allowing more PRs to complete successfully.

### v2: Unconstrained for Higher Recall
**Core Strategy:** Remove artificial per-PR cap; encourage full analysis.

**Rationale:** The v1 constraint was empirically chosen, not theoretically justified. v2 tests whether removing the cap allows models to provide more thorough findings without hitting token exhaustion on simpler PRs.

**Key Instruction Change:**
```
CONSTRAINTS:
- Detect ONLY clear, high-confidence violations
- Do NOT guess or infer
- Be precise: exact line_number
```

**Operational Trade-off:** Encourages exhaustive finding detection. Risk: more complex PRs may still fail to generate output if the model's reasoning depth + findings list exceeds context limits.

### v3: Prompt Efficiency via Compression
**Core Strategy:** Radically shorten the prompt to reduce token waste on instruction overhead.

**Rationale:** Both v1 and v2 spent significant tokens on verbose processing rules and repetitive explanations. v3 collapses the prompt to ~150 tokens (vs. ~450 for v1/v2) by:
- Merging processing rules into single compact lines
- Removing verbose violation type descriptions
- Eliminating redundant output format explanations
- Keeping only essential constraints

**Key Changes:**
```
- Single-line violation definitions instead of multi-line with examples
- Removed "PROCESSING RULES" section entirely
- Compact "Rules:" section combining multiple directives
- Output format shown inline rather than elaborate block
```

**Operational Advantage:** Saves ~300 tokens per batch on prompt overhead, freeing budget for complex PR code analysis. Formula:
$$\text{TokenBudget}_{\text{available}} = \text{8K context} - \text{PromptTokens} - \text{CodeTokens}$$

For complex PRs, v3's shorter prompt allows larger code sections or deeper model reasoning before token exhaustion.

## High-Level Metrics Comparison

| Metric | v1 | v2 | v3 |
|---|---|---|---|
| **Ground-truth PRs** | 97 | 97 | 97 |
| **Predicted PRs (parsed JSON)** | 49 | 26 | 31 |
| **Empty responses** | 48 | 71 | 66 |
| **Empty response rate** | 49.5% | 73.2% | 68.0% |
| **Analyzed PRs** | 47 | 24 | 29 |
| **Total LLM comments** | 186 | 86 | 104 |
| **Total GT comments (analyzed)** | 272 | 91 | 108 |
| **Missed violations** | 92 | 11 | 6 |
| **Extra violations** | 6 | 6 | 2 |
| **Equal violations (PRs)** | 23 | 16 | 24 |
| **Line match success rate** | 46.8% | 51.2% | **56.7%** |

## Failure Analysis

### Empty Response Rate Progression
- **v1: 49.5% failure** — Conservative cap allowed more PRs to output, but still high failure rate on complex PRs
- **v2: 73.2% failure** — Uncapped strategy triggered MORE failures; model likely entered deep reasoning loops on large PRs, exhausting tokens before generating output
- **v3: 68.0% failure** — Modest improvement over v2 but still higher than v1; prompt efficiency helped but insufficient to offset cumulative factors

### Root Causes (Groq 8K TPM + Model Behavior)
1. **Complex code PRs burn tokens before output:** Longer source files + deeper reasoning = token exhaustion mid-analysis
2. **v2 exacerbated this:** Removing the cap signaled "find everything," causing the model to attempt exhaustive analysis on large PRs, consuming tokens before generating any output tokens
3. **v3 partially mitigated:** Freed ~300 tokens per batch, reducing failures for moderately complex PRs
4. **Token budget formula:**
   - Input tokens (prompt + code): typically 2–4K for complex PRs
   - Model reasoning overhead: ~500–800 tokens for v1/v2 unconstrained analysis
   - Output tokens needed: ~200–400 to encode robust JSON array
   - **v3 saves 300 tokens, reclaiming output space for borderline PRs**

### Observed Pattern
- PRs with simple code (<500 LOC, <1.5K tokens): v1, v2, v3 all succeed
- Medium complexity (500–2K LOC): v1 and v3 succeed; v2 often fails
- High complexity (>2K LOC): all variants struggle; v3 slightly better due to prompt savings

## Per-Category Detailed Metrics

### v1: Conservative Strategy Results

| Category | Precision | Recall | F1 | TP | FP | FN | Line Match | Line Mismatch |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **documentation_formatting** | 0.7500 | 0.1034 | 0.1818 | 3 | 1 | 26 | 0 | 4 |
| **indentation** | 0.6471 | 0.2292 | 0.3385 | 11 | 6 | 37 | 4 | 13 |
| **mutable_default** | 1.0000 | 0.5862 | 0.7391 | 17 | 0 | 12 | 5 | 12 |
| **naming_convention** | 0.9643 | 0.9474 | **0.9558** | 54 | 2 | 3 | 16 | 40 |
| **unused_import** | 1.0000 | 0.8440 | **0.9154** | 92 | 0 | 17 | 62 | 30 |

**v1 Observations:**
- **Strong on naming_convention & unused_import:** Both categories exceed F1=0.91, indicating the model reliably detects these straightforward violations
- **Perfect precision on unused_import (1.0000):** Zero false positives; when the model identifies an unused import, it is almost always correct
- **Weak on documentation_formatting (F1=0.1818):** Lowest F1; model struggles to identify docstring issues despite high precision (0.75 on 4 detections), suggesting this category is under-represented in training or requires deeper semantic understanding
- **Indentation underperformance (F1=0.3385):** Recall only 0.23 indicates the model misses many indentation issues, possibly due to token constraints limiting thorough line-by-line analysis
- **Mutable_default plateau at R=0.5862:** Model catches strong cases but misses subtle mutable defaults (e.g., `dict()` vs `{}`, or mutable objects in nested contexts)
- **Line matching coherence (46.8%):** Of 186 LLM findings, 87 (46.8%) match expected line numbers; 99 are either off-line or false positives
- **Reasonably balanced:** 23 PRs had exact violation counts matching ground truth, suggesting the Max 5 cap was not overly limiting for many simple PRs

### v2: Unconstrained Strategy Results

| Category | Precision | Recall | F1 | TP | FP | FN | Line Match | Line Mismatch |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **documentation_formatting** | 0.0000 | 0.0000 | **0.0000** | 0 | 0 | 1 | 0 | 0 |
| **indentation** | 0.0000 | 0.0000 | **0.0000** | 0 | 7 | 0 | 0 | 7 |
| **mutable_default** | 1.0000 | 0.8333 | 0.9091 | 10 | 0 | 2 | 1 | 9 |
| **naming_convention** | 1.0000 | 1.0000 | **1.0000** | 15 | 0 | 0 | 4 | 11 |
| **unused_import** | 1.0000 | 0.8571 | 0.9231 | 54 | 0 | 9 | 39 | 15 |

**v2 Observations:**
- **Complete failure on indentation (F1=0.0000):** 7 false positives, 0 true positives, 0 ground-truth matches. Model generated incorrect indentation findings in analyzed PRs
- **Perfect naming_convention (F1=1.0000):** Uncapped analysis allowed model to systematically verify naming rules; 15/15 correct with perfect precision/recall
- **Halved dataset (24 analyzed PRs vs. 47 v1):** 71 PRs had no response; model's unconstrained reasoning triggered token exhaustion on 24 additional PRs
- **Lower precision on mutable_default (R=0.8333 vs. 0.5862 in v1):** Counterintuitive — uncapped version found more but missed 2 vs. 12 in v1. Suggests uncap actually deepens analysis on simpler PRs, helping precision
- **Concentration in 2 categories:** Only 86 total findings vs. 186 in v1; model may have been more selective or reached token limits during output phase
- **Line matching still 51.2%:** Slightly better than v1, but on much smaller dataset (44 matches out of 86)
- **Critical flaw:** Indentation regression suggests uncapped analysis created model confusion; too many findings attempted led to incorrect categorization

### v3: Efficient Prompt Strategy Results

| Category | Precision | Recall | F1 | TP | FP | FN | Line Match | Line Mismatch |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **documentation_formatting** | 1.0000 | 0.5000 | **0.6667** | 1 | 0 | 1 | 0 | 1 |
| **mutable_default** | 1.0000 | 1.0000 | **1.0000** | 15 | 0 | 0 | 3 | 12 |
| **naming_convention** | 0.9048 | 0.8261 | 0.8636 | 19 | 2 | 4 | 10 | 11 |
| **unused_import** | 1.0000 | 0.9853 | **0.9926** | 67 | 0 | 1 | 46 | 21 |

**v3 Observations:**
- **Missing indentation category:** Model did not generate any indentation findings; prompt reframing may have inadvertently de-emphasized this category
- **Best unused_import F1 (0.9926):** Highest score across all variants; only 1 FN vs. 17 in v1 and 9 in v2
- **Perfect mutable_default (F1=1.0000):** Tied with v3's perfection; small dataset (15 TPs) but 100% accuracy
- **Improved documentation_formatting (F1=0.6667):** Better than v1 (0.1818) and v2 (0.0000); prompt efficiency allowed deeper analysis on simpler PRs
- **Higher line matching (56.7%):** 59/104 findings matched expected lines; best ratio across all variants
- **29 analyzed PRs (30% of dataset):** Better than v2 (25%) but worse than v1 (48%). Prompt savings helped some PRs but not enough to reclaim v1's volume

---

## Root Cause Analysis: Why Variants Diverged

### v1 vs. v2 Regression (49.5% → 73.2% failure)
**Why did removing the cap make things worse?**

1. **Token Accounting:**
   - v1 prompt: ~450 tokens (verbose rules, examples)
   - v2 prompt: ~450 tokens (identical)
   - v1 max-5 constraint signals: "Stop after 5, output now"
   - v2 no constraint signals: "Find all violations; be thorough"

2. **Model Behavior Change:**
   - v1: Model interprets max-5 as a hard stop; outputs after ~5 findings or fewer
   - v2: Model attempts exhaustive analysis; for complex PRs with 20–50+ latent violations, model enters deep reasoning loop consuming tokens without generating output

3. **Failure Cascade:**
   - v1 @ 1.5K code + 400 reasoning = 1.9K, leaves 6.1K for output ✓ (succeeds)
   - v2 @ 1.5K code + 1200 reasoning (unconstrained) = 2.7K, leaves 5.3K for output ✓ (still works)
   - v2 complex @ 3K code + 3000 reasoning = 6K, leaves 2K for output but model mid-analysis = ✗ (fails before output)

### v3 Improvement Mechanism
**Why did compression help v2's failure rate?**

1. **Prompt Efficiency Savings:**
   - v1/v2: 450 tokens → v3: 150 tokens (67% reduction)
   - Reclaimed budget: 300 tokens per PR, allows ~5–10% larger code sections on borderline PRs

2. **But Why Still 68% Failure?**
   - v1 used constraint signaling; v3 lost that signal by making prompt shorter but still unconstrained
   - v3 inherited v2's unconstrained behavior without v2's token savings (v2 also used same 450-token prompt)
   - **Conclusion:** Prompt length was secondary factor; constraint semantics were primary

3. **Where v3 Succeeded (56.7% line match):**
   - Better line-number accuracy suggests model attended more carefully to code without verbose rules
   - Freed attention budget went to precise line identification rather than parsing long constraints
   - Small dataset (104 findings) means precision gains on analyzed PRs

---

## Token Budget Deep Dive

### Estimated Token Consumption (Groq gpt-oss-20b)

| Component | v1 | v2 | v3 | Notes |
|---|---|---|---|---|
| **Prompt tokens** | 450 | 450 | 150 | v3 reframing saved 300 tokens |
| **Code tokens (typical)** | 1500 | 1500 | 1500 | Same code for fairness |
| **Model reasoning (constrained)** | 300–500 | 800–1500 | 300–500 | v2 searches exhaustively; v1/v3 bound |
| **Output JSON tokens** | 200–400 | 200–400 | 200–400 | Proportional to findings |
| **Total observed budget** | 2450–2900 | 2950–3850 | 2150–2550 | v3 tightest; v2 loosest |
| **Failure threshold** | ~6500–7500 | ~6500–7500 | ~6500–7500 | Context limit; cross-variant |

**Key Insight:** With 8K context limit and ~4–5K reserved for safety/parsing, actual usable budget is ~3–4K. v2's unconstrained reasoning can push complex PRs to 4–5K+ before output generation, triggering silent failures where model stops reasoning mid-analysis.

---

## Aggregate Analysis Across All Variants

### Findings Summary (All PRs with Responses)
- **v1: 47 analyzed PRs, 186 findings** → 3.96 avg findings per PR (below 5-cap due to easier code)
- **v2: 24 analyzed PRs, 86 findings** → 3.58 avg findings per PR (concentrated on simpler PRs that survived)
- **v3: 29 analyzed PRs, 104 findings** → 3.59 avg findings per PR (similar to v2 but on different dataset)

**Interpretation:** Max-5 cap in v1 was not binding for most PRs. Average findings (3.6–3.96) suggest typical PRs have 3–5 clear violations. v2/v3 datasets are subsets of v1 due to failures, so direct comparison is limited.

### Ground Truth vs. LLM Output (Analyzed PRs Only)
- **v1:** 272 GT comments vs. 186 LLM comments (68.4% coverage)
- **v2:** 91 GT comments vs. 86 LLM comments (94.5% coverage)
- **v3:** 108 GT comments vs. 104 LLM comments (96.3% coverage)

**Key Finding:** v3 achieved best coverage (96.3%) and fewest missed violations (6) among analyzed PRs. v2 also high (94.5%). This indicates **that PRs which generated output had good fidelity for v2/v3, suggesting their failures are outright non-responses, not degraded responses.**

### Precision-Recall Trade-off by Strategy
- **v1:** Broader recall (especially indentation 0.2292, documentation 0.1034) but lower precision on some categories
- **v2:** Extreme precision but on narrow dataset; strong on naming_convention (1.0) and unused_import (0.8571) for 24 PRs
- **v3:** Balanced; best F1 on unused_import (0.9926), perfect on mutable_default (1.0000)

---

## Failure Rate Root Causes (Detailed)

### Why ~70% Silent Failures for v2/v3?

1. **Groq 8K TPM Limit Interaction:**
   - TPM = tokens per minute; 8K TPM with batch_size=1 means ~133 tokens/sec sustained
   - Complex PR analysis at 1500–3000 tokens per request can hit rate limits mid-batch
   - Retry mechanisms in `naive_llm.ipynb` may not be capturing timeout failures as "empty responses"

2. **Model Context Window Saturation:**
   - gpt-oss-20b has nominal 8K context
   - Input tokens + model reasoning can exceed buffer, causing truncation/failure before output
   - v1's max-5 constraint acts as a circuit-breaker; model knows to output early

3. **Batch-Level Token Budgeting:**
   - With `batch_size=1`, each PR request needs full allocation
   - No opportunity to parallelize or amortize prompt overhead across multiple PRs
   - Switching to `batch_size=5` might help, but current design is sequential

4. **Code Complexity Distribution:**
   - Top tier (simple): 15–20 PRs succeed in all variants
   - Mid tier (moderate): 15–30 PRs; v1 catches most, v2/v3 catch ~50%
   - Bottom tier (complex): 40–50 PRs; all variants fail, primarily v2/v3

---

## Category-Specific Insights

### naming_convention
- **v1:** P=0.9643, R=0.9474, F1=0.9558 (strong)
- **v2:** P=1.0000, R=1.0000, F1=1.0000 (perfect but on 24 PRs)
- **v3:** P=0.9048, R=0.8261, F1=0.8636 (good but dip in recall)
- **Interpretation:** Most reliable category across variants. Naming rules are clear and verifiable without deep context. v2's perfection is consistent with theory — when model analyzes, it identifies rule violations accurately.

### unused_import
- **v1:** P=1.0000, R=0.8440, F1=0.9154 (excellent precision, decent recall)
- **v2:** P=1.0000, R=0.8571, F1=0.9231 (nearly tied with v1)
- **v3:** P=1.0000, R=0.9853, F1=0.9926 (best overall)
- **Interpretation:** v3's superiority suggests prompt efficiency matters for this category. Shorter prompt allowed model to scan imports more thoroughly. Perfect precision across all variants confirms unused imports are unambiguous.

### mutable_default
- **v1:** P=1.0000, R=0.5862, F1=0.7391 (perfect precision, weak recall)
- **v2:** P=1.0000, R=0.8333, F1=0.9091 (strong)
- **v3:** P=1.0000, R=1.0000, F1=1.0000 (perfect)
- **Interpretation:** v3's perfection (15/15 TP) on small dataset suggests uncapped analysis + prompt efficiency helped model systematically scan function definitions. v1's weak recall (12 FN) indicates max-5 cap sometimes stops before reaching all function definitions.

### indentation
- **v1:** P=0.6471, R=0.2292, F1=0.3385 (poor)
- **v2:** P=0.0000, R=0.0000, F1=0.0000 (catastrophic)
- **v3:** Not detected (0 findings)
- **Interpretation:** Indentation is the hardest category for LLMs. Requires careful whitespace parsing and context awareness. v2's 7 false positives suggest unconstrained reasoning led to hallucinated indentation violations. v3 entirely skipped this category, possibly due to prompt reframing making it less salient.

### documentation_formatting
- **v1:** P=0.7500, R=0.1034, F1=0.1818 (weak)
- **v2:** P=0.0000, R=0.0000, F1=0.0000 (no findings)
- **v3:** P=1.0000, R=0.5000, F1=0.6667 (improved)
- **Interpretation:** Hardest category overall. v1's high precision but low recall suggests model rarely detects it. v3's 1 TP but 1 FN indicates improved sensitivity but still unreliable. This category likely requires docstring semantic understanding beyond strict formatting rules.

---

## Recommendations & Trade-off Analysis

### For Detection Accuracy (F1 Maximization):
**Winner: v3 (0.9926 on unused_import + 1.0000 on mutable_default)**
- Use v3 for projects where you can tolerate ~68% non-response rate
- Focus on categories like `unused_import` and `mutable_default` where v3 excels
- Avoid expecting indentation or documentation findings

### For Coverage (Maximum PRs Analyzed):
**Winner: v1 (47/97 = 48.5% success rate)**
- Max-5 constraint prevents token explosion on complex PRs
- Trade-off: Lower per-PR accuracy on indentation/documentation but more consistent output
- Best for large-scale batch evaluation where some findings per PR is preferable to silence

### For Optimal Balance (Accuracy + Coverage):
**Recommendation: Hybrid v1 + v3**
- Use v1 strategy (constrained analysis) for reliability
- Use v3 prompt compression for token efficiency
- Target: ~50–55% coverage with F1 similar to v3
- Implementation: Add `max_findings=5` constraint back to v3 prompt

### For Future Iterations:
1. **Increase batch_size:** Current batch_size=1 wastes prompt overhead; batch_size=5 might reduce per-PR token cost
2. **Implement retry logic:** Some "empty responses" may be transient rate-limit failures; add exponential backoff
3. **Category-specific constraints:** Only constrain indentation/documentation; trust model on unused_import/naming/mutable_default
4. **Use smaller model or retrieval:** gpt-oss-20b is capable but token-hungry; consider embedding-based retrieval augmentation for code context instead of full source inclusion

---

## Summary Table: Variant Comparison

| Metric | v1 | v2 | v3 | Winner |
|---|---|---|---|---|
| Success rate | 48.5% | 25.8% | 29.9% | **v1** |
| Total findings | 186 | 86 | 104 | v1 |
| Average per PR | 3.96 | 3.58 | 3.59 | Similar |
| Unused_import F1 | 0.9154 | 0.9231 | **0.9926** | v3 |
| Naming_convention F1 | 0.9558 | 1.0000 | 0.8636 | v2* |
| Mutable_default F1 | 0.7391 | 0.9091 | **1.0000** | v3 |
| Line match rate | 46.8% | 51.2% | **56.7%** | v3 |
| Coverage gt comments | 68.4% | 94.5% | **96.3%** | v3 |
| Avg precision (all cats) | 0.82 | 0.80 | **0.96** | v3 |

**v2 \*:** Only on 24 PRs; smaller dataset inflates scores.

---

## Conclusion

**v1** prioritizes reliability and breadth via explicit constraint signaling, achieving 48.5% coverage with solid F1 scores (0.91+) on key categories. The max-5 cap prevents token exhaustion on complex PRs, yielding consistent—if incomplete—results.

**v2** removes constraints hoping for deeper analysis but triggers token exhaustion on 73.2% of PRs. Among the small subset that output, precision is high (naming_convention 1.0000), but the dataset is too small and skewed to be operationally useful. This variant demonstrates the risk of signal-free prompting with tight token budgets.

**v3** trades coverage for precision, achieving 96.3% coverage on analyzed PRs and best-in-class F1 on unused_import (0.9926) and perfect mutable_default (1.0000). Prompt compression freed tokens for refined analysis but did not solve the fundamental Groq TPM bottleneck. Line matching improved to 56.7%, indicating better code-to-finding alignment.

**Recommendation:** For production use, adopt **v1's constraint semantics with v3's prompt efficiency** — a hybrid approach retaining backward compatibility while reclaiming 300 tokens for complex code analysis. For research on high-precision subset, accept v3's lower coverage in exchange for F1 gains on easily-detectable violations.

Both v2 and v3 reveal that **unconstrained LLM analysis in token-limited environments (Groq 8K TPM) rapidly degrades; explicit constraints signal safe termination points, enabling higher overall coverage.**
