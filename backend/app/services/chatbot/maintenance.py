"""
Maintenance Job — Auto-Calibration Loop
=========================================
Scheduled maintenance tasks for the self-learning chatbot system.

Run daily (or on-demand) via:
  - python -m app.services.chatbot.maintenance
  - POST /corrections/maintenance  (admin endpoint)

Tasks performed:
  1. decay_patterns()        — time-based score decay + prune dead patterns
  2. recompute_confidence()  — rebalance hypothesis stats vs graph weights
  3. auto_suppress_bugs()    — apply suppression_factor *= 0.8 for >= 3 bug reports
  4. rebalance_weights()     — renormalize graph edge weights to prevent drift
  5. compact_storage()       — remove duplicate entries from JSON files

After 100 interactions, system should reach:
  - LOW tier < 5% of responses
  - MEDIUM tier < 15%
  - HIGH tier > 80%
"""
from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

_BASE = Path(__file__).parents[3]
_LEARNING_DIR = _BASE / "data" / "learning"
_PATTERNS_FILE = _LEARNING_DIR / "learned_patterns.json"
_BUGS_FILE = _LEARNING_DIR / "bug_suggestions.json"
_HYP_STATS_FILE = _LEARNING_DIR / "hypothesis_stats.json"
_ENTITY_MEMORY_FILE = _LEARNING_DIR / "entity_memory.json"
_WEAK_PATTERNS_FILE = _LEARNING_DIR / "weak_patterns.json"
_MAINTENANCE_LOG_FILE = _LEARNING_DIR / "maintenance_log.json"


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_daily_maintenance(dry_run: bool = False) -> Dict[str, Any]:
    """
    Run all maintenance tasks.

    dry_run=True: compute changes but do NOT write files.

    Returns a report dict with per-task statistics.
    """
    start = datetime.now(tz=timezone.utc)
    report: Dict[str, Any] = {
        "started_at": start.isoformat(),
        "dry_run": dry_run,
        "tasks": {},
    }

    logger.info(f"Maintenance: starting daily calibration (dry_run={dry_run})")

    # Task 1: Pattern decay
    try:
        decay_stats = _decay_patterns(dry_run=dry_run)
        report["tasks"]["decay_patterns"] = decay_stats
        logger.info(f"Maintenance: decay_patterns → {decay_stats}")
    except Exception as e:
        report["tasks"]["decay_patterns"] = {"error": str(e)}
        logger.error(f"Maintenance: decay_patterns failed: {e}")

    # Task 2: Recompute hypothesis confidence scores
    try:
        conf_stats = _recompute_confidence(dry_run=dry_run)
        report["tasks"]["recompute_confidence"] = conf_stats
        logger.info(f"Maintenance: recompute_confidence → {conf_stats}")
    except Exception as e:
        report["tasks"]["recompute_confidence"] = {"error": str(e)}
        logger.error(f"Maintenance: recompute_confidence failed: {e}")

    # Task 3: Auto-suppress from bug patterns (>=3 occurrences)
    try:
        suppress_stats = _auto_suppress_from_bugs(dry_run=dry_run)
        report["tasks"]["auto_suppress_bugs"] = suppress_stats
        logger.info(f"Maintenance: auto_suppress_bugs → {suppress_stats}")
    except Exception as e:
        report["tasks"]["auto_suppress_bugs"] = {"error": str(e)}
        logger.error(f"Maintenance: auto_suppress_bugs failed: {e}")

    # Task 4: Rebalance graph edge weights
    try:
        rebal_stats = _rebalance_graph_weights(dry_run=dry_run)
        report["tasks"]["rebalance_weights"] = rebal_stats
        logger.info(f"Maintenance: rebalance_weights → {rebal_stats}")
    except Exception as e:
        report["tasks"]["rebalance_weights"] = {"error": str(e)}
        logger.error(f"Maintenance: rebalance_weights failed: {e}")

    # Task 5: Compact / deduplicate JSON files
    try:
        compact_stats = _compact_storage(dry_run=dry_run)
        report["tasks"]["compact_storage"] = compact_stats
        logger.info(f"Maintenance: compact_storage \u2192 {compact_stats}")
    except Exception as e:
        report["tasks"]["compact_storage"] = {"error": str(e)}
        logger.error(f"Maintenance: compact_storage failed: {e}")

    # Task 6: Compute tier distribution (no writes)
    try:
        dist = _compute_tier_distribution()
        report["tasks"]["tier_distribution"] = dist
    except Exception as e:
        report["tasks"]["tier_distribution"] = {"error": str(e)}

    # Task 7: Promote weak patterns that meet the threshold
    try:
        promo_stats = _promote_weak_patterns(dry_run=dry_run)
        report["tasks"]["promote_weak_patterns"] = promo_stats
        logger.info(f"Maintenance: promote_weak_patterns \u2192 {promo_stats}")
    except Exception as e:
        report["tasks"]["promote_weak_patterns"] = {"error": str(e)}
        logger.error(f"Maintenance: promote_weak_patterns failed: {e}")

    # Task 8: Drift detection
    try:
        drift_stats = _detect_drift(dry_run=dry_run)
        report["tasks"]["drift_detection"] = drift_stats
        if drift_stats.get("drift_detected"):
            logger.warning(f"Maintenance: MODEL DRIFT DETECTED \u2014 {drift_stats}")
        else:
            logger.info(f"Maintenance: drift_detection \u2192 {drift_stats}")
    except Exception as e:
        report["tasks"]["drift_detection"] = {"error": str(e)}
        logger.error(f"Maintenance: drift_detection failed: {e}")

    report["finished_at"] = datetime.now(tz=timezone.utc).isoformat()
    elapsed_s = (datetime.now(tz=timezone.utc) - start).total_seconds()
    report["elapsed_seconds"] = round(elapsed_s, 2)

    if not dry_run:
        _append_maintenance_log(report)

    logger.info(f"Maintenance: complete in {elapsed_s:.1f}s — {report['tasks']}")
    return report


# ─────────────────────────────────────────────────────────────────────────────
# Task implementations
# ─────────────────────────────────────────────────────────────────────────────

def _decay_patterns(dry_run: bool = False) -> Dict[str, int]:
    """
    Time-based decay on learned patterns.
    Delegates to LearningLoop.decay_patterns() to keep logic centralised.
    """
    if dry_run:
        # Simulate without writing
        if not _PATTERNS_FILE.exists():
            return {"decayed": 0, "pruned": 0, "kept": 0, "dry_run": True}
        try:
            data = json.loads(_PATTERNS_FILE.read_text(encoding="utf-8"))
            patterns = data.get("patterns", [])
            now = datetime.now(tz=timezone.utc)
            stats = {"decayed": 0, "pruned": 0, "kept": 0, "dry_run": True}
            for p in patterns:
                try:
                    age = (now - datetime.fromisoformat(p.get("created_at", ""))).days
                except Exception:
                    age = 0
                score = p.get("confidence", 0.85)
                if age > 14:
                    score *= 0.98
                    stats["decayed"] += 1
                if age > 60:
                    score *= 0.90
                if score < 0.20:
                    stats["pruned"] += 1
                else:
                    stats["kept"] += 1
            return stats
        except Exception:
            return {"dry_run": True}

    from app.services.chatbot.learning_loop import learning_loop
    return learning_loop.decay_patterns(inactive_days=14, prune_threshold=0.20)


def _recompute_confidence(dry_run: bool = False) -> Dict[str, Any]:
    """
    Recompute composite confidence_score for every tracked hypothesis.
    Updates suppression_factor based on bug frequency.
    """
    if not _HYP_STATS_FILE.exists():
        return {"updated": 0, "message": "No hypothesis stats file"}

    try:
        raw = json.loads(_HYP_STATS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"updated": 0, "error": "Cannot read hypothesis_stats.json"}

    updated = 0
    for hyp_id, hdata in raw.items():
        s_total = hdata.get("success_count", 0) + hdata.get("failure_count", 0)
        if s_total == 0:
            continue
        sr = hdata.get("success_count", 0) / s_total
        visit_boost = math.log(1 + hdata.get("visit_count", 0)) * 0.08
        new_score = min(1.0, max(0.0, sr * 0.7 + visit_boost)) * hdata.get("suppression_factor", 1.0)
        hdata["computed_confidence"] = round(new_score, 4)
        updated += 1

    if not dry_run:
        _HYP_STATS_FILE.write_text(
            json.dumps(raw, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return {"updated": updated, "total": len(raw)}


def _auto_suppress_from_bugs(
    dry_run: bool = False,
    threshold: int = 3,
    suppression_multiplier: float = 0.80,
) -> Dict[str, Any]:
    """
    For every hypothesis with >= threshold bug reports:
      suppression_factor *= 0.80 per extra occurrence
    Persists to hypothesis_stats.json AND graph_weights.json.
    """
    if not _BUGS_FILE.exists():
        return {"suppressed": 0}

    try:
        bugs_data = json.loads(_BUGS_FILE.read_text(encoding="utf-8"))
        bugs = bugs_data.get("bug_suggestions", [])
    except Exception:
        return {"suppressed": 0, "error": "Cannot read bug_suggestions.json"}

    # Count occurrences per hypothesis
    count: Dict[str, int] = {}
    for bug in bugs:
        hyp_id = (bug.get("related_patterns") or [None])[0]
        if hyp_id:
            count[hyp_id] = count.get(hyp_id, 0) + 1

    suppressed: List[str] = []
    factors: Dict[str, float] = {}

    for hyp_id, n in count.items():
        if n < threshold:
            continue
        # Each occurrence beyond threshold → multiply factor by 0.80
        extra = n - threshold + 1
        factor = suppression_multiplier ** extra
        factors[hyp_id] = round(factor, 4)
        suppressed.append(hyp_id)

    if dry_run or not suppressed:
        return {"suppressed": len(suppressed), "factors": factors, "dry_run": dry_run}

    # Apply to hypothesis stats
    if _HYP_STATS_FILE.exists():
        try:
            raw = json.loads(_HYP_STATS_FILE.read_text(encoding="utf-8"))
            for hyp_id, factor in factors.items():
                if hyp_id not in raw:
                    raw[hyp_id] = {
                        "hypothesis_id": hyp_id,
                        "visit_count": 0,
                        "success_count": 0,
                        "failure_count": 0,
                        "last_seen": "",
                        "suppression_factor": 1.0,
                    }
                raw[hyp_id]["suppression_factor"] = round(
                    raw[hyp_id].get("suppression_factor", 1.0) * factor, 4
                )
            _HYP_STATS_FILE.write_text(
                json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"Maintenance: could not update hyp_stats: {e}")

    # Apply to graph weights
    try:
        from app.services.chatbot.incident_graph import incident_graph
        for hyp_id, factor in factors.items():
            # suppress = apply a negative delta proportional to (1 - factor)
            incident_graph.suppress(hyp_id, delta=1.0 - factor)
    except Exception as e:
        logger.warning(f"Maintenance: graph suppress failed: {e}")

    return {"suppressed": len(suppressed), "factors": factors}


def _rebalance_graph_weights(dry_run: bool = False) -> Dict[str, Any]:
    """
    Prevent edge weight drift: renormalise edges so max weight per node = 1.0.
    Prevents a single heavily-reinforced path from dominating all others.
    """
    weights_file = _LEARNING_DIR / "graph_weights.json"
    if not weights_file.exists():
        return {"edges_rebalanced": 0, "message": "No graph_weights.json"}

    try:
        data = json.loads(weights_file.read_text(encoding="utf-8"))
    except Exception:
        return {"edges_rebalanced": 0, "error": "Cannot read graph_weights.json"}

    edges = data.get("edges", {})
    if not edges:
        return {"edges_rebalanced": 0}

    # Find max weight
    max_weight = max((e.get("weight", 1.0) for e in edges.values()), default=1.0)
    # Only normalise if drift detected (max > 1.05 indicates accumulated reinforcement)
    if max_weight <= 1.05:
        return {"edges_rebalanced": 0, "max_weight": round(max_weight, 4)}

    rebalanced = 0
    for eid, edata in edges.items():
        old_w = edata.get("weight", 1.0)
        new_w = round(old_w / max_weight, 4)
        if old_w != new_w:
            edata["weight"] = new_w
            rebalanced += 1

    if not dry_run:
        weights_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # Force graph reload on next query
        try:
            from app.services.chatbot.incident_graph import incident_graph
            incident_graph._loaded = False
        except Exception:
            pass

    return {"edges_rebalanced": rebalanced, "max_weight_before": round(max_weight, 4)}


def _compact_storage(dry_run: bool = False) -> Dict[str, Any]:
    """
    Deduplicate entries in JSON list files and remove oversized arrays.
    Keeps the most recent N entries per file to prevent unbounded growth.
    """
    limits: Dict[str, Tuple[str, int]] = {
        str(_PATTERNS_FILE): ("patterns", 500),
        str(_BUGS_FILE): ("bug_suggestions", 200),
        str(_WEAK_PATTERNS_FILE): ("weak_patterns", 300),
    }
    stats: Dict[str, int] = {}

    for fpath_str, (key, max_items) in limits.items():
        fpath = Path(fpath_str)
        if not fpath.exists():
            continue
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
            items = data.get(key, [])
            original_count = len(items)

            # Deduplicate by id
            seen_ids: set = set()
            deduped: List[Dict] = []
            for item in items:
                item_id = item.get("id", "")
                if item_id and item_id in seen_ids:
                    continue
                seen_ids.add(item_id)
                deduped.append(item)

            # Keep most recent max_items
            final = deduped[-max_items:] if len(deduped) > max_items else deduped
            removed = original_count - len(final)
            stats[fpath.name] = removed

            if not dry_run and removed > 0:
                data[key] = final
                fpath.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
                )
        except Exception as e:
            stats[fpath.name] = -1
            logger.warning(f"Maintenance: compact failed for {fpath}: {e}")

    return stats


def _compute_tier_distribution() -> Dict[str, Any]:
    """
    Estimate current tier distribution from hypothesis stats.
    HIGH = confidence_score >= 0.70
    MEDIUM = 0.40 <= confidence_score < 0.70
    LOW = confidence_score < 0.40
    """
    if not _HYP_STATS_FILE.exists():
        return {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "total": 0}

    try:
        raw = json.loads(_HYP_STATS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "total": 0}

    dist = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for hdata in raw.values():
        s_total = hdata.get("success_count", 0) + hdata.get("failure_count", 0)
        if s_total == 0:
            continue
        sr = hdata.get("success_count", 0) / s_total
        visit_boost = math.log(1 + hdata.get("visit_count", 0)) * 0.08
        score = min(1.0, max(0.0, sr * 0.7 + visit_boost)) * hdata.get("suppression_factor", 1.0)
        if score >= 0.70:
            dist["HIGH"] += 1
        elif score >= 0.40:
            dist["MEDIUM"] += 1
        else:
            dist["LOW"] += 1

    dist["total"] = sum(dist.values())
    if dist["total"] > 0:
        dist["HIGH_pct"] = round(dist["HIGH"] / dist["total"] * 100, 1)
        dist["MEDIUM_pct"] = round(dist["MEDIUM"] / dist["total"] * 100, 1)
        dist["LOW_pct"] = round(dist["LOW"] / dist["total"] * 100, 1)

    return dist


def _promote_weak_patterns(dry_run: bool = False) -> Dict[str, Any]:
    """
    Promote weak patterns with >= 3 occurrences and success_rate > 70%
    into full LearnedPatterns.
    Delegates to LearningLoop.promote_weak_patterns().
    """
    try:
        from app.services.chatbot.learning_loop import learning_loop
        return learning_loop.promote_weak_patterns(
            min_count=3,
            min_success_rate=0.70,
            dry_run=dry_run,
        )
    except Exception as e:
        logger.warning(f"Maintenance: promote_weak_patterns error: {e}")
        return {"promoted": 0, "skipped": 0, "error": str(e)}


_DRIFT_LOG_FILE = _LEARNING_DIR / "drift_log.json"
_DRIFT_WINDOW_DAYS = 7       # rolling window for baseline
_DRIFT_THRESHOLD = 0.15      # 15% drop triggers alert


def _detect_drift(dry_run: bool = False) -> Dict[str, Any]:
    """
    Drift Detection.

    Compares today's average validation score (from hypothesis_stats.json)
    against the 7-day rolling average stored in drift_log.json.

    If avg_score drops > 15% vs rolling baseline: drift_detected = True.
    Appends a drift entry to drift_log.json (last 60 entries kept).

    Returns: {drift_detected, today_avg, baseline_avg, delta_pct, alert}
    """
    _LEARNING_DIR.mkdir(parents=True, exist_ok=True)

    # Load hypothesis stats to compute today's average score
    if not _HYP_STATS_FILE.exists():
        return {"drift_detected": False, "message": "No hypothesis stats available"}

    try:
        raw = json.loads(_HYP_STATS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"drift_detected": False, "error": "Cannot read hypothesis_stats.json"}

    scores: List[float] = []
    for hdata in raw.values():
        s_total = hdata.get("success_count", 0) + hdata.get("failure_count", 0)
        if s_total == 0:
            continue
        sr = hdata.get("success_count", 0) / s_total
        vb = math.log(1 + hdata.get("visit_count", 0)) * 0.08
        score = min(1.0, max(0.0, sr * 0.7 + vb)) * hdata.get("suppression_factor", 1.0)
        scores.append(score)

    if not scores:
        return {"drift_detected": False, "message": "No scored hypotheses yet"}

    today_avg = round(sum(scores) / len(scores), 4)
    today_str = datetime.now(tz=timezone.utc).date().isoformat()

    # Load drift log for baseline
    if _DRIFT_LOG_FILE.exists():
        try:
            drift_data = json.loads(_DRIFT_LOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            drift_data = {"entries": []}
    else:
        drift_data = {"entries": []}

    entries: List[Dict] = drift_data.get("entries", [])

    # Compute 7-day rolling baseline (exclude today)
    window_cutoff = datetime.now(tz=timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ).isoformat()
    recent = [
        e["avg_score"] for e in entries[-_DRIFT_WINDOW_DAYS:]
        if e.get("date", "") < today_str
    ]
    baseline_avg = round(sum(recent) / len(recent), 4) if recent else today_avg

    # Compute delta
    if baseline_avg > 0:
        delta_pct = round((baseline_avg - today_avg) / baseline_avg, 4)  # positive = drop
    else:
        delta_pct = 0.0

    drift_detected = delta_pct > _DRIFT_THRESHOLD

    result: Dict[str, Any] = {
        "date": today_str,
        "today_avg": today_avg,
        "baseline_avg": baseline_avg,
        "delta_pct": delta_pct,
        "drift_detected": drift_detected,
        "hypothesis_count": len(scores),
    }

    if drift_detected:
        result["alert"] = (
            f"\u26a0\ufe0f MODEL DRIFT SUSPECTED — avg score dropped {delta_pct:.1%} "
            f"vs 7-day baseline ({baseline_avg:.3f} \u2192 {today_avg:.3f})"
        )
        logger.warning(result["alert"])

    # Persist entry to drift log
    if not dry_run:
        entries.append(result)
        drift_data["entries"] = entries[-60:]  # keep last 60 days
        _DRIFT_LOG_FILE.write_text(
            json.dumps(drift_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    return result


def _append_maintenance_log(report: Dict[str, Any]) -> None:
    _LEARNING_DIR.mkdir(parents=True, exist_ok=True)
    if _MAINTENANCE_LOG_FILE.exists():
        try:
            data = json.loads(_MAINTENANCE_LOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {"runs": []}
    else:
        data = {"runs": []}

    # Keep last 30 maintenance runs
    data["runs"].append(report)
    data["runs"] = data["runs"][-30:]
    _MAINTENANCE_LOG_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Standalone execution
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    dry = "--dry-run" in sys.argv
    print(f"\n{'═' * 60}")
    print("  MAINTENANCE JOB — Auto-Calibration Loop")
    print(f"  Mode: {'DRY RUN (no writes)' if dry else 'LIVE'}")
    print(f"{'═' * 60}\n")

    result = run_daily_maintenance(dry_run=dry)

    for task, stats in result.get("tasks", {}).items():
        icon = "✅" if "error" not in stats else "❌"
        print(f"  {icon} {task}: {stats}")

    print(f"\n  Elapsed: {result.get('elapsed_seconds', 0):.2f}s")
    tier_dist = result.get("tasks", {}).get("tier_distribution", {})
    if tier_dist.get("total", 0) > 0:
        print(f"\n  📊 Hypothesis Tier Distribution:")
        print(f"     HIGH:   {tier_dist.get('HIGH_pct', 0)}%")
        print(f"     MEDIUM: {tier_dist.get('MEDIUM_pct', 0)}%")
        print(f"     LOW:    {tier_dist.get('LOW_pct', 0)}%")
    print()
