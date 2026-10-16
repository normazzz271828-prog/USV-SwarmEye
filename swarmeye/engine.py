"""Engineering demonstration rules, NOT a reproduction of the research papers.

Coordinates: east/north metres. Every decision consumes only received observations.
Hidden truth is exposed separately, exclusively for completed-run review.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from functools import lru_cache
import json
import math
import uuid

VERSION = "demo-0.1.0"
DURATION = 180
TURN_AT = 90
DOMAIN_A, DOMAIN_B = 60.0, 35.0
MAX_AGE = 30
HORIZON = 60
WARNING_DISTANCE = 150.0
HARD_DISTANCE = 2 * DOMAIN_A
SHIPS = ("OS", "T1", "T2", "T3")
LABELS = {"OS": "本船", "T1": "外部船 01", "T2": "外部船 02", "T3": "外部船 03"}
PARAMETERS = {
    "duration_s": DURATION, "sample_s": 1, "turn_at_s": TURN_AT,
    "domain_a_m": DOMAIN_A, "domain_b_m": DOMAIN_B,
    "cluster_distance_m": 120, "cluster_heading_deg": 15,
    "cluster_speed_m_s": 1, "max_observation_age_s": MAX_AGE,
    "prediction_horizon_s": HORIZON, "warning_dcpa_m": WARNING_DISTANCE,
    "hard_distance_m": HARD_DISTANCE, "warning_enter_samples": 3,
    "clear_samples": 5, "warning_exit_dcpa_m": 170,
    "world_m": [-620, 500, -450, 650],
    "source": "工程演示假设，非实船参数或安全标准",
}


def truth(t: int) -> dict:
    """Synthetic motion. The turn is continuous in position, idealized in velocity."""
    result = {"OS": {"x": 0.0, "y": -400.0 + 4*t, "vx": 0.0, "vy": 4.0}}
    for i, ship in enumerate(SHIPS[1:]):
        elapsed = max(0, t - TURN_AT)
        result[ship] = {
            "x": -450.0 - i*40 + 4.5*min(t, TURN_AT) + 1.5*elapsed,
            "y": 120.0 + (25 if i == 1 else 0) + 4.0*elapsed,
            "vx": 4.5 if t < TURN_AT else 1.5,
            "vy": 0.0 if t < TURN_AT else 4.0,
        }
    return result


@lru_cache(maxsize=2)
def observations(delay: int) -> tuple:
    if delay not in (0, 20):
        raise ValueError("仅支持 0 秒或 20 秒延迟配对场景")
    return tuple(
        {"ship": ship, "observed_at": t,
         "received_at": t + (0 if ship == "OS" else delay), **state}
        for t in range(DURATION + 1) for ship, state in truth(t).items()
    )


def latest_received(records, now: int) -> dict:
    latest = {}
    for row in records:
        if row["received_at"] > now or row["observed_at"] > now:
            continue
        old = latest.get(row["ship"])
        if old is None or row["observed_at"] > old["observed_at"]:
            latest[row["ship"]] = row
    states = {}
    for ship, row in latest.items():
        age = now - row["observed_at"]
        states[ship] = {**row, "age": age,
                        "x": row["x"] + row["vx"] * age,
                        "y": row["y"] + row["vy"] * age}
    return states


def cluster(states: dict) -> list[list[str]]:
    """Connected components using only observed distance, heading and speed."""
    pending = set(states) - {"OS"}
    groups = []
    while pending:
        group = [min(pending)]
        pending.remove(group[0])
        for a in group:
            for b in sorted(pending):
                p, q = states[a], states[b]
                angle = abs((math.degrees(math.atan2(p["vy"], p["vx"]) - math.atan2(q["vy"], q["vx"])) + 180) % 360 - 180)
                if (math.hypot(p["x"]-q["x"], p["y"]-q["y"]) <= 120
                    and angle <= 15
                    and abs(math.hypot(p["vx"], p["vy"]) - math.hypot(q["vx"], q["vy"])) <= 1):
                    group.append(b)
                    pending.remove(b)
        groups.append(sorted(group))
    return groups


def pair_metrics(own: dict, target: dict) -> dict:
    rx, ry = target["x"]-own["x"], target["y"]-own["y"]
    vx, vy = target["vx"]-own["vx"], target["vy"]-own["vy"]
    vv = vx*vx + vy*vy
    distance = math.hypot(rx, ry)
    tcpa = -(rx*vx + ry*vy)/vv if vv > 1e-9 else None
    dcpa = math.hypot(rx+vx*tcpa, ry+vy*tcpa) if tcpa is not None else distance
    return {"distance": round(distance, 3), "dcpa": round(dcpa, 3),
            "tcpa": round(tcpa, 3) if tcpa is not None else None,
            "closing": rx*vx + ry*vy < -1e-9}


def evaluate(records, now: int) -> dict:
    states = latest_received(records, now)
    valid = all(s in states and states[s]["age"] <= MAX_AGE for s in SHIPS)
    pairs = {s: pair_metrics(states["OS"], states[s]) for s in SHIPS[1:]
             if "OS" in states and s in states}
    level, rule = 0, "DQ-01"
    if valid:
        hard = any(m["distance"] <= HARD_DISTANCE for m in pairs.values())
        warning = any(m["tcpa"] is not None and 0 < m["tcpa"] <= HORIZON
                      and m["dcpa"] < WARNING_DISTANCE for m in pairs.values())
        level, rule = (3, "RISK-01") if hard else ((2, "RISK-02") if warning else (1, "CLEAR-01"))
    return {"time": now, "states": states, "groups": cluster(states), "pairs": pairs,
            "quality": "有效" if valid else "不足或过时", "valid": valid,
            "raw_level": level, "rule": rule,
            "min_distance": min((m["distance"] for m in pairs.values()), default=None)}


def new_run(delay: int = 20) -> dict:
    observations(delay)  # validate
    run = {"schema": 1, "version": VERSION, "id": uuid.uuid4().hex[:12],
           "created_at": datetime.now(timezone.utc).isoformat(), "delay": delay,
           "time": -1, "history": [], "events": [], "decisions": [], "reviews": [],
           "warning_count": 0, "clear_count": 0}
    return advance(run, 0)


def advance(run: dict, until: int) -> dict:
    if type(until) is not int or not run["time"] <= until <= DURATION:
        raise ValueError("演练时钟只能向前，范围为 0–180 秒")
    records = observations(run["delay"])
    for t in range(run["time"] + 1, until + 1):
        snapshot = evaluate(records, t)
        active = next((e for e in reversed(run["events"]) if e["end"] is None), None)
        raw = snapshot["raw_level"]
        run["warning_count"] = run["warning_count"]+1 if raw == 2 else 0
        level = raw
        if raw == 2 and not active and run["warning_count"] < 3:
            level = 1
        # Hysteresis: an active event clears only after 5 valid, unambiguous samples.
        near = any(m["distance"] <= HARD_DISTANCE or
                   (m["tcpa"] is not None and 0 < m["tcpa"] <= HORIZON and m["dcpa"] < 170)
                   for m in snapshot["pairs"].values())
        clear = snapshot["valid"] and not near
        run["clear_count"] = run["clear_count"]+1 if clear else 0
        if active and not snapshot["valid"]:
            level = active["updates"][-1]["level"]
        elif active and raw == 1 and run["clear_count"] < 5:
            # A valid sample with no current hard invasion cannot keep L3 latched.
            level = min(2, active["updates"][-1]["level"])
        if active and run["clear_count"] >= 5:
            active["end"] = t
            active["updates"].append({"time": t, "level": 1, "rule": "CLEAR-01"})
            active = None
            level = 1
        snapshot["level"] = level
        if level >= 2 and snapshot["valid"]:
            if active is None:
                active = {"id": f"EV-{len(run['events'])+1:03d}", "start": t,
                          "end": None, "participants": list(SHIPS), "peak": level,
                          "snapshot": deepcopy(snapshot), "updates": []}
                run["events"].append(active)
            if not active["updates"] or active["updates"][-1]["level"] != level:
                active["updates"].append({"time": t, "level": level, "rule": snapshot["rule"]})
            active["peak"] = max(active["peak"], level)
        run["history"].append(snapshot)
        run["time"] = t
    return run


def decide(run: dict, event_id: str, action: str, reason: str, revisit: str = "") -> None:
    event = next((e for e in run["events"] if e["id"] == event_id), None)
    if not event or event["end"] is not None or run["time"] == DURATION:
        raise ValueError("该事件已结束，请在复盘中追加意见")
    if action not in ("采纳建议", "暂缓处理", "驳回建议"):
        raise ValueError("未知处置类型")
    reason, revisit = reason.strip(), revisit.strip()
    if not 2 <= len(reason) <= 1000:
        raise ValueError("请填写 2–1000 字的处置理由")
    if action == "暂缓处理" and not 2 <= len(revisit) <= 300:
        raise ValueError("暂缓处理需要填写复核时点或条件")
    run["decisions"].append({"event_id": event_id, "time": run["time"],
                              "action": action, "reason": reason, "revisit": revisit,
                              "evidence": deepcopy(run["history"][-1])})


def review(run: dict, event_id: str, status: str, note: str) -> None:
    if run["time"] != DURATION:
        raise ValueError("完成演练后再查看完整经过和复核")
    if event_id not in {e["id"] for e in run["events"]}:
        raise ValueError("事件不存在")
    if status not in ("原判断得到支持", "需要修订", "证据不足") or not 2 <= len(note.strip()) <= 1000:
        raise ValueError("请选择复核状态并填写 2–1000 字的依据")
    run["reviews"].append({"event_id": event_id, "status": status, "note": note.strip(),
                            "recorded_at": datetime.now(timezone.utc).isoformat()})


def export_run(run: dict) -> str:
    return json.dumps({**run, "parameters": PARAMETERS}, ensure_ascii=False, indent=2, allow_nan=False)


def restore_run(raw: str) -> dict:
    """Recompute evidence; never trust uploaded computed values or execute content."""
    if len(raw.encode("utf-8")) > 2_000_000:
        raise ValueError("记录不能超过 2 MB")
    try:
        source = json.loads(raw)
        if not isinstance(source, dict) or source["schema"] != 1 or source["version"] != VERSION:
            raise ValueError("记录格式或方法版本不兼容")
        if type(source["delay"]) is not int or type(source["time"]) is not int or not 0 <= source["time"] <= DURATION:
            raise ValueError("场景或时钟不合法")
        if not isinstance(source["id"], str) or len(source["id"]) != 12 or any(c not in "0123456789abcdef" for c in source["id"]):
            raise ValueError("运行编号不合法")
        datetime.fromisoformat(source["created_at"])
        run = new_run(source["delay"])
        run["id"], run["created_at"] = source["id"], source["created_at"]
        for decision in source["decisions"]:
            if type(decision["time"]) is not int or decision["time"] > source["time"]:
                raise ValueError("处置时间不合法")
            advance(run, decision["time"])
            decide(run, decision["event_id"], decision["action"], decision["reason"], decision["revisit"])
        advance(run, source["time"])
        for item in source["reviews"]:
            review(run, item["event_id"], item["status"], item["note"])
            datetime.fromisoformat(item["recorded_at"])
            run["reviews"][-1]["recorded_at"] = item["recorded_at"]
        for key in ("events", "history", "decisions", "parameters"):
            expected = PARAMETERS if key == "parameters" else run[key]
            if source.get(key) != expected:
                raise ValueError("记录证据与重算结果不一致，无法恢复")
        return run
    except (KeyError, TypeError, AttributeError, OverflowError, json.JSONDecodeError) as exc:
        raise ValueError("无法读取记录，请选择本网站导出的完整 JSON 文件") from exc


def convex_hull(points):
    pts = sorted(set(points))
    if len(pts) <= 1:
        return pts
    def cross(o, a, b):
        return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def domain_points(state):
    heading = math.atan2(state["vy"], state["vx"])
    return [(state["x"] + DOMAIN_A*math.cos(i*math.tau/48)*math.cos(heading) - DOMAIN_B*math.sin(i*math.tau/48)*math.sin(heading),
             state["y"] + DOMAIN_A*math.cos(i*math.tau/48)*math.sin(heading) + DOMAIN_B*math.sin(i*math.tau/48)*math.cos(heading))
            for i in range(48)]
