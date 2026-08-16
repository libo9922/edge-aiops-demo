# Lightweight Runbook RAG (demo-stage)

The demo does **not** require a full RAG stack. Instead, `mock_runbook.search`
implements a lightweight retrieval that approximates RAG behavior without
embedding models or vector databases.

This document describes the algorithm and the upgrade path to real RAG in
final stage.

---

## 1. What `mock_runbook.search` does today

Given a free-text query (e.g., `"accuracy drop after OTA"`), it returns a
ranked list of Runbook entries from the active scenario.

**Algorithm** (in `mock_tools.py` → `LocalMockTools.search_runbooks`):

1. **Keyword filter**: lower-case query; keep Runbooks whose `title` or any
   `match_terms` contains a query token (substring match).
2. **Tag overlap score**: count query tokens that also appear in the
   Runbook's `tags` array.
3. **Symptom overlap score**: count query tokens that also appear in the
   Runbook's `symptoms` array.
4. **Final score** = `tag_overlap * 2 + symptom_overlap * 1.5 + title_match * 1`.
5. Return top-K (K=3) sorted by score.

The Runbook entry in each scenario JSON has these fields:

```json
{
  "id": "RB-OTA-001",
  "title": "OTA fan-out without canary caused accuracy regression",
  "match_terms": ["accuracy_drop", "ota", "v3.2.1", "v3.2.0"],
  "tags": ["ota", "model", "rollback"],
  "symptoms": ["accuracy_drop", "p99_latency_high"],
  "recommendation": "Rollback to previous version, add canary stage, ..."
}
```

This is intentionally **simple** but **useful**: the Agent gets a ranked list
of relevant Runbooks with concrete recommendations it can cite in the RCA
output.

---

## 2. Why not full RAG yet?

| Reason | Detail |
|--------|--------|
| Vector DB infra | ChromaDB / FAISS / pgvector requires extra services |
| Embedding model | Adds cold-start latency; not free |
| Runbook corpus size | Demo corpus is 1-2 entries per scenario; keyword match is enough |
| Reproducibility | Mock must be deterministic for graders |

For a 2-3 entry corpus, keyword + tag overlap scores match what an embedding
model would return. We accept the trade-off and defer vector search to final
stage.

---

## 3. Upgrade path (final stage)

When the Runbook corpus grows to ≥10 docs and the embedding cost is acceptable:

1. **At build time**: chunk each Runbook markdown into 256-token passages,
   embed with `sentence-transformers/all-MiniLM-L6-v2`, store in ChromaDB.
2. **At query time**: embed the query, cosine-similarity top-K=5 from Chroma.
3. **Hybrid score**: combine cosine score + tag overlap (BM25-style) for better
   recall.
4. **Interface** stays the same: `POST /tools/{scenario}/mock_runbook.search`
   with `{"query": "..."}` → list of `{id, title, recommendation, score}`.

The Agent never knows the difference.

---

## 4. Demo scenario enhancement

To make the demo Runbook retrieval visible, `edge_diagnostician` is expected
to call `mock_runbook.search` with a query derived from the incident
symptoms. The returned Runbook's `recommendation` field is cited as evidence
in the RCA `top_candidate.evidence` list, satisfying the **evidence citation
quality gate** in the Skill.

Example trace for `model_drift` scenario:

```
[edge_diagnostician]
  → mock_runbook.search(query="accuracy drop after OTA")
  ← [
       {id: "RB-OTA-001", title: "OTA fan-out without canary caused accuracy regression",
        recommendation: "Rollback to previous version, add canary stage, ...",
        score: 0.85}
     ]
  → rca_result.top_candidate.evidence.append("runbook:RB-OTA-001")
```

This is enough for the Skill quality gate: **every recommendation must cite
at least one Runbook**.

---

## 5. Quality Gate (Skill-level)

`log-trace-rca/SKILL.md` requires:

> Every candidate must have at least one piece of evidence. ... Never invent log
> lines or metric values; if evidence is missing, report a data gap.

`recovery-verify/SKILL.md` requires:

> Postmortem notes must include at least one process improvement and one
> observability improvement.

Lightweight RAG output satisfies both gates because each Runbook entry has a
traceable `id` and a concrete `recommendation` that can be quoted verbatim.