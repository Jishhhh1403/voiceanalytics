from __future__ import annotations

import json
from typing import Any

import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from ...db.database import jdump
from ...orchestration.run_context import RunContext


def run(ctx: RunContext) -> dict[str, Any]:
    ctx.module_start("module_c_vectorize")
    # use representative accepted insights
    insights = ctx.db.query(
        """
        SELECT i.insight_id, i.feedback_id, i.journey_node_id, i.symptom, i.intent, i.emotion, i.effort_score,
               i.enriched_sentence, i.is_open_set, f.cleaned_text, f.customer_tier, f.duplicate_group_id, f.is_duplicate_representative,
               COALESCE(t.signature_path, 'Unmapped Banking Journey') as signature_path
        FROM extracted_insights i
        JOIN feedback_records f ON f.run_id=i.run_id AND f.feedback_id=i.feedback_id
        LEFT JOIN taxonomy_nodes t ON t.node_id=i.journey_node_id
        WHERE i.run_id=? AND (f.is_duplicate_representative=1 OR f.duplicate_group_id IS NULL)
        ORDER BY i.insight_id
        """,
        (ctx.run_id,),
    )
    if not insights:
        ctx.warn("No insights available for vectorization")
        ctx.module_done("module_c_vectorize", input_count=0, output_count=0, message="no insights")
        return {"insights": 0}

    ids = [r["insight_id"] for r in insights]
    sig_texts = [(r["signature_path"] or "") for r in insights]
    sym_texts = [(r["symptom"] or "") for r in insights]
    txt_texts = [(r["cleaned_text"] or r["enriched_sentence"] or "") for r in insights]

    def fit_vec(texts, max_features):
        vec = TfidfVectorizer(ngram_range=(1,2), sublinear_tf=True, stop_words="english", max_features=max_features)
        try:
            X = vec.fit_transform(texts)
        except ValueError:
            # empty vocabulary fallback
            X = sparse.csr_matrix((len(texts), 1))
        return vec, X

    v_sig, X_sig = fit_vec(sig_texts, 1000)
    v_sym, X_sym = fit_vec(sym_texts, 1500)
    v_txt, X_txt = fit_vec(txt_texts, 5000)

    X = sparse.hstack([0.40*X_sig, 0.35*X_sym, 0.25*X_txt]).tocsr()
    X = normalize(X)
    ctx.artifacts.write_npz("direct/tfidf_matrix.npz", data=X.data, indices=X.indices, indptr=X.indptr, shape=np.array(X.shape))
    cids = ctx.artifacts.write_json("direct/insight_ids.json", ids)
    vocab_meta = {
        "sig_vocab_size": len(getattr(v_sig, "vocabulary_", {})),
        "sym_vocab_size": len(getattr(v_sym, "vocabulary_", {})),
        "txt_vocab_size": len(getattr(v_txt, "vocabulary_", {})),
        "shape": list(X.shape),
        "weights": {"signature": 0.4, "symptom": 0.35, "text": 0.25},
        "note": "Representative insights used (one per duplicate group) per spec baseline; full membership preserved in DB.",
    }
    cm = ctx.artifacts.write_json("direct/vectorizer_metadata.json", vocab_meta)

    # behavioral feature table (scalable: store features, compute distances on demand/blockwise later)
    beh = []
    for r in insights:
        effort = r["effort_score"]
        try:
            e = float(effort) if effort is not None else None
        except Exception:
            e = None
        e_scaled = ((e - 1.0) / 4.0) if e is not None else None
        beh.append({
            "insight_id": r["insight_id"],
            "feedback_id": r["feedback_id"],
            "journey_node_id": r["journey_node_id"] or "OPEN_SET",
            "symptom": (r["symptom"] or "unknown").lower(),
            "emotion": (r["emotion"] or "unknown").lower(),
            "effort_scaled": e_scaled,
            "effort_raw": e,
            "sentiment": r.get("sentiment"),
            "customer_tier": r.get("customer_tier"),
            "is_open_set": r.get("is_open_set", 0),
            "intent": r.get("intent"),
        })
    cb = ctx.artifacts.write_json("direct/behavioral_features.json", beh)
    cman = ctx.artifacts.write_json("direct/distance_manifest.json", {
        "strategy": "on_demand_blockwise_gower",
        "reason": "Avoid materializing dense 15k x 15k matrix; compute pairwise/cluster distances blockwise where required (MDS/H2).",
        "features": ["journey_node_id","symptom","emotion","effort_scaled"],
        "missing_policy": "categorical mismatch on missing; numeric contributes 0 if either missing (documented)",
        "rows": len(beh),
    })

    ctx.record_artifact("module_c_vectorize", "matrix", "direct/tfidf_matrix.npz", "npz", {"shape": list(X.shape)})
    ctx.record_artifact("module_c_vectorize", "ids", "direct/insight_ids.json", cids)
    ctx.record_artifact("module_c_vectorize", "meta", "direct/vectorizer_metadata.json", cm)
    ctx.record_artifact("module_c_vectorize", "behavioral", "direct/behavioral_features.json", cb)
    ctx.module_done("module_c_vectorize", input_count=len(insights), output_count=len(insights), message=f"vectorized {len(insights)} insights", artifacts=vocab_meta)
    return {"insights": len(insights), **vocab_meta}
