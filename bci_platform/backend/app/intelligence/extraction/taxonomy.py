from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class TaxonomyNode:
    node_id: str
    parent_id: str | None
    module: str
    feature: str
    stage: str
    node_type: str
    display_name: str
    description: str
    signature_path: str
    synonyms: list[str]
    status: str
    taxonomy_version: str


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


class Taxonomy:
    def __init__(self, nodes: list[TaxonomyNode], version: str) -> None:
        self.nodes = nodes
        self.version = version
        self.by_id = {n.node_id: n for n in nodes}
        self.by_module = {}
        for n in nodes:
            self.by_module.setdefault(n.module.lower(), n)

    @classmethod
    def load(cls, path: str | Path) -> "Taxonomy":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        version = str(data.get("version") or "1.0.0")
        raw_nodes = data.get("nodes") or []
        # two-pass to resolve modules/features
        id_to_raw = {n.get("node_id"): n for n in raw_nodes}
        def module_name(n):
            pid = n.get("parent_id")
            if not pid:
                return n.get("display_name") or n.get("node_id")
            parent = id_to_raw.get(pid)
            if parent and not parent.get("parent_id"):
                return parent.get("display_name") or pid
            # climb
            cur = parent
            while cur and cur.get("parent_id"):
                cur = id_to_raw.get(cur.get("parent_id"))
            return (cur or {}).get("display_name") or pid
        def feature_name(n):
            if not n.get("parent_id"):
                return n.get("display_name") or n.get("node_id")
            return n.get("display_name") or n.get("node_id")
        nodes: list[TaxonomyNode] = []
        for n in raw_nodes:
            mod = module_name(n)
            feat = feature_name(n) if n.get("parent_id") else "General"
            stage = feat
            sig = f"{mod} > {feat}" if feat != "General" else mod
            nodes.append(TaxonomyNode(
                node_id=str(n.get("node_id")),
                parent_id=n.get("parent_id"),
                module=str(mod),
                feature=str(feat),
                stage=str(stage),
                node_type=str(n.get("node_type") or "feature"),
                display_name=str(n.get("display_name") or n.get("node_id")),
                description=str(n.get("description") or ""),
                signature_path=sig,
                synonyms=[str(s) for s in (n.get("synonyms") or [])],
                status=str(n.get("status") or "active"),
                taxonomy_version=version,
            ))
        return cls(nodes, version)

    def map_text(self, text: str, threshold: float = 0.55) -> tuple[str | None, float, bool, list[dict[str, Any]]]:
        t = _norm(text)
        if not t:
            return None, 0.0, True, []
        scored = []
        for n in self.nodes:
            if n.status != "active":
                continue
            score = 0.0
            dn = _norm(n.display_name)
            if dn and dn in t:
                score += 3.0
            for syn in n.synonyms:
                sn = _norm(syn)
                if sn and sn in t:
                    score += 2.2
            toks = set(re.findall(r"[a-z0-9]+", t))
            name_toks = set(re.findall(r"[a-z0-9]+", dn + " " + " ".join(n.synonyms)))
            desc_toks = set(re.findall(r"[a-z0-9]+", _norm(n.description)))
            overlap_name = len(toks & name_toks)
            overlap_desc = len(toks & desc_toks)
            score += 0.5 * overlap_name + 0.25 * overlap_desc
            if n.node_type == "module":
                score *= 0.92
            if score > 0:
                scored.append((n, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        top = [{"node_id": n.node_id, "signature_path": n.signature_path, "score": round(s, 4)} for n, s in scored[:5]]
        if not scored:
            return None, 0.0, True, []
        best, best_score = scored[0]
        # normalize confidence roughly to 0-1 by soft cap
        conf = min(1.0, best_score / 5.0)
        if conf < threshold:
            return None, conf, True, top
        return best.node_id, conf, False, top
