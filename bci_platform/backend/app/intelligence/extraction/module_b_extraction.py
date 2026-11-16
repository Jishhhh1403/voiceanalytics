from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from typing import Any

from ...db.database import jdump
from ...orchestration.run_context import RunContext
from .taxonomy import Taxonomy

INTENT_PATTERNS = {
    "make_payment": ["pay", "payment", "transfer", "send money", "upi", "imps", "neft", "rtgs"],
    "login_access": ["login", "log in", "sign in", "password", "otp", "biometric", "session", "access"],
    "check_balance": ["balance", "statement", "transaction", "history", "passbook"],
    "manage_card": ["card", "credit card", "debit card", "limit", "block card", "pin"],
    "get_support": ["support", "help", "complaint", "call", "agent", "chat"],
    "update_profile": ["profile", "kyc", "update", "change details", "address"],
}
SYMPTOM_PATTERNS = {
    "failed": ["fail", "failed", "declined", "rejected", "not working", "unable", "cannot", "can't", "error"],
    "slow": ["slow", "taking too long", "delay", "delayed", "hang", "stuck", "loading"],
    "confusing": ["confusing", "unclear", "hard to find", "not visible", "missing", "complicated"],
    "charged": ["charged", "deducted", "debited", "fee", "money cut"],
    "crash": ["crash", "crashed", "freeze", "frozen", "bug"],
}
EMOTION_PATTERNS = {
    "anger": ["angry", "frustrat", "annoy", "irritat", "worst", "ridiculous"],
    "anxiety": ["worried", "scared", "anxious", "panic", "urgent"],
    "sadness": ["disappointed", "unhappy", "sad"],
    "satisfaction": ["happy", "good", "great", "love", "satisfied", "convenient", "clear"],
}
WORKAROUNDS = {
    "BRANCH_VISIT": ["branch", "teller", "in-person", "counter"],
    "CALL_CENTER": ["call center", "call centre", "helpline", "phone support", "ivr", "customer care", "call support"],
    "MANUAL_EXPORT": ["excel", "csv", "spreadsheet", "download statement", "manually", "manual"],
    "SCREENSHOT_PROOF": ["screenshot", "screen shot", "photo of receipt", "pdf proof"],
    "THIRD_PARTY_CHAT": ["whatsapp", "email support", "twitter", "x.com", "social media"],
}


def _find_span(text: str, phrase: str) -> tuple[int, int] | None:
    if not phrase:
        return None
    i = text.lower().find(phrase.lower())
    if i < 0:
        return None
    return i, i + len(phrase)


def _detect_label(text: str, patterns: dict[str, list[str]], default: str) -> tuple[str, float, str | None]:
    t = text.lower()
    best_label = default
    best_score = 0.0
    best_phrase = None
    for label, keys in patterns.items():
        for k in keys:
            if k in t:
                sc = 1.0 + 0.1 * len(k)
                if sc > best_score:
                    best_score = sc
                    best_label = label
                    best_phrase = k
    conf = min(0.95, 0.4 + 0.15 * best_score) if best_score else 0.3
    return best_label, conf, best_phrase


def _sentiment(text: str) -> float:
    t = text.lower()
    neg = ["fail", "declined", "error", "slow", "crash", "bad", "worst", "angry", "frustrat", "unable", "cannot", "can't", "deducted", "charged", "stuck", "confusing", "missing", "not working"]
    pos = ["good", "great", "easy", "happy", "love", "fast", "smooth", "convenient", "clear", "satisfied"]
    n = sum(1 for w in neg if w in t)
    p = sum(1 for w in pos if w in t)
    if n == 0 and p == 0:
        return -0.1
    score = (p - n) / max(1, p + n)
    return max(-1.0, min(1.0, score))


def _effort(text: str) -> float:
    t = text.lower()
    score = 2.5
    for w, v in [("urgent", 1.0), ("again", 0.5), ("second time", 0.7), ("waiting", 0.5), ("call", 0.8), ("branch", 0.8), ("many times", 0.8), ("still", 0.4)]:
        if w in t:
            score += v
    for w, v in [("easy", -0.5), ("clear", -0.3), ("convenient", -0.3), ("happy", -0.4)]:
        if w in t:
            score -= v
    return max(1.0, min(5.0, round(score, 2)))


def _workarounds(text: str) -> list[dict[str, Any]]:
    t = text.lower()
    found = []
    for tag, keys in WORKAROUNDS.items():
        for k in keys:
            if k in t:
                span = _find_span(text, k)
                found.append({"tag": tag, "match": k, "start": span[0] if span else None, "end": span[1] if span else None})
                break
    return found


def _outcome(text: str) -> str | None:
    t = text.lower()
    if any(w in t for w in ["resolved", "fixed", "completed", "success"]):
        return "resolved"
    if any(w in t for w in ["failed", "declined", "not resolved", "pending", "waiting"]):
        return "unresolved"
    return None


def run(ctx: RunContext) -> dict[str, Any]:
    ctx.module_start("module_b_extraction")
    tax = Taxonomy.load(ctx.settings.taxonomy_path)
    feedback = ctx.db.query(
        "SELECT feedback_id, raw_text, cleaned_text FROM feedback_records WHERE run_id=? AND ingestion_status='accepted'",
        (ctx.run_id,),
    )
    # persist taxonomy nodes
    ctx.db.executemany(
        "INSERT OR REPLACE INTO taxonomy_nodes(node_id,parent_id,module,feature,stage,node_type,display_name,description,signature_path,synonyms_json,status,taxonomy_version) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        [(n.node_id,n.parent_id,n.module,n.feature,n.stage,n.node_type,n.display_name,n.description,n.signature_path,jdump(n.synonyms),n.status,n.taxonomy_version) for n in tax.nodes]
    )

    insights_rows = []
    open_set = 0
    evidence_ok = 0
    for fb in feedback:
        raw = fb["raw_text"] or ""
        cleaned = fb["cleaned_text"] or raw
        intent, intent_conf, intent_phrase = _detect_label(cleaned, INTENT_PATTERNS, "general_inquiry")
        symptom, sym_conf, sym_phrase = _detect_label(cleaned, SYMPTOM_PATTERNS, "issue_reported")
        emotion, emo_conf, _ = _detect_label(cleaned, EMOTION_PATTERNS, "neutral")
        aspect = intent.replace("_", " ")
        sent = _sentiment(cleaned)
        effort = _effort(cleaned)
        outcome = _outcome(cleaned)
        workarounds = _workarounds(cleaned)

        # evidence span: prefer symptom phrase else intent phrase else first 120 chars
        ev_phrase = sym_phrase or intent_phrase or cleaned[:120]
        span = _find_span(raw, ev_phrase) or _find_span(cleaned, ev_phrase)
        if span and raw[span[0]:span[1]].lower() == ev_phrase.lower()[: span[1]-span[0] ]:
            evidence_span = raw[span[0]:span[1]]
            es, ee = span
            evidence_ok += 1
        else:
            # fallback to first sentence slice guaranteed in raw
            evidence_span = raw[: min(len(raw), 160)]
            es, ee = 0, len(evidence_span)

        journey_node_id, j_conf, is_open, top_j = tax.map_text(cleaned, threshold=ctx.settings.taxonomy_confidence_threshold)
        if is_open:
            open_set += 1
        sig_path = tax.by_id[journey_node_id].signature_path if journey_node_id and journey_node_id in tax.by_id else "Unmapped Banking Journey"
        enriched = f"Under {sig_path}, the customer experiences {symptom} and states: {cleaned}"

        iid_src = f"{ctx.run_id}|{fb['feedback_id']}|0"
        insight_id = "INS-" + hashlib.sha1(iid_src.encode()).hexdigest()[:16]
        insights_rows.append((
            insight_id, ctx.run_id, fb["feedback_id"], journey_node_id, j_conf, intent, aspect, symptom,
            float(sent), emotion, float(effort), outcome, jdump(workarounds), evidence_span, es, ee,
            enriched, 1 if is_open else 0, float(min(0.95, (intent_conf + sym_conf + j_conf) / 3.0)),
            jdump({"intent": intent_conf, "symptom": sym_conf, "emotion": emo_conf, "journey": j_conf, "top_journey": top_j}),
            ctx.settings.extraction_model_version, tax.version, "ok", None
        ))

    ctx.db.executemany(
        """INSERT OR REPLACE INTO extracted_insights
        (insight_id,run_id,feedback_id,journey_node_id,journey_confidence,intent,aspect,symptom,sentiment,emotion,effort_score,outcome,
         workarounds_json,evidence_span,evidence_start,evidence_end,enriched_sentence,is_open_set,extraction_confidence,field_confidence_json,
         model_version,taxonomy_version,extraction_status,error)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        insights_rows,
    )

    report = {
        "total_feedback": len(feedback),
        "insights": len(insights_rows),
        "open_set": open_set,
        "open_set_rate": (open_set / len(insights_rows)) if insights_rows else 0,
        "evidence_exact_or_fallback": evidence_ok,
        "model_version": ctx.settings.extraction_model_version,
        "extraction_provider": ctx.settings.extraction_provider,
        "note": "Rule-based provisional extractor (deterministic, auditable). BERT task models not supplied; fields emitted with confidences and verifiable evidence spans.",
        "taxonomy_version": tax.version,
    }
    c = ctx.artifacts.write_json("extraction/extraction_quality_report.json", report)
    ctx.record_artifact("module_b_extraction", "report", "extraction/extraction_quality_report.json", c, {"insights": len(insights_rows)})
    ctx.module_done("module_b_extraction", input_count=len(feedback), output_count=len(insights_rows), message="extraction complete", artifacts={"report": "extraction/extraction_quality_report.json"})
    return report
