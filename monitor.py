# -*- coding: utf-8 -*-
"""
시장 버블 모니터링 + 텔레그램 알림.
- 야후 파이낸스(yfinance) / FRED 에서 지표 수집
- config.py 의 임계치와 비교
- '기준선을 넘는 순간'에만 1회 알림 (스팸 방지)
- 상태는 state.json 에 저장되어 매 실행 사이에 유지됨

환경변수(깃허브 Secrets):
  TELEGRAM_TOKEN   : 텔레그램 봇 토큰 (필수)
  TELEGRAM_CHAT_ID : 내 채팅 ID (필수)
  FRED_API_KEY     : FRED API 키 (선택, 없으면 fred 지표만 건너뜀)
"""
import os
import json
import datetime as dt

import requests

import config

STATE_FILE = "state.json"
SEV_ICON = {"경계": "🟡", "위험": "🔴"}


# ──────────────────────────────────────────────────────────────
# 데이터 수집
# ──────────────────────────────────────────────────────────────
def collect_yf_ids():
    ids = set()
    for ind in config.INDICATORS:
        if ind["source"] == "yf":
            ids.add(ind["id"])
        elif ind["source"] == "derived":
            a, b = ind["id"].split("/")
            ids.add(a); ids.add(b)
    return sorted(ids)


def fetch_yf(ids):
    """{id: {'last': float, 'prev': float}} 반환. 실패한 티커는 제외."""
    import yfinance as yf
    out = {}
    if not ids:
        return out
    data = yf.download(ids, period="7d", interval="1d",
                       group_by="ticker", progress=False, threads=True)
    for tkr in ids:
        try:
            if len(ids) == 1:
                closes = data["Close"].dropna()
            else:
                closes = data[tkr]["Close"].dropna()
            if len(closes) >= 1:
                last = float(closes.iloc[-1])
                prev = float(closes.iloc[-2]) if len(closes) >= 2 else last
                out[tkr] = {"last": last, "prev": prev}
        except Exception as e:
            print(f"[warn] yfinance 수집 실패: {tkr} ({e})")
    return out


def fetch_fred(series_id, api_key):
    """FRED 최신 관측치(float) 반환. 실패 시 None."""
    if not api_key:
        return None
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {"series_id": series_id, "api_key": api_key, "file_type": "json",
              "sort_order": "desc", "limit": 5}
    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        for obs in r.json().get("observations", []):
            if obs["value"] not in (".", "", None):
                return float(obs["value"])
    except Exception as e:
        print(f"[warn] FRED 수집 실패: {series_id} ({e})")
    return None


# ──────────────────────────────────────────────────────────────
# 값 조회 / 판정
# ──────────────────────────────────────────────────────────────
def get_value(ind, yf_data, fred_cache, fred_key):
    """(현재값, 전일대비변동%) 반환."""
    src = ind["source"]
    if src == "yf":
        d = yf_data.get(ind["id"])
        if not d:
            return None, None
        last, prev = d["last"], d["prev"]
        chg = (last - prev) / prev * 100 if prev else None
        return last, chg
    if src == "fred":
        sid = ind["id"]
        if sid not in fred_cache:
            fred_cache[sid] = fetch_fred(sid, fred_key)
        return fred_cache[sid], None
    if src == "derived":
        a, b = ind["id"].split("/")
        da, db = yf_data.get(a), yf_data.get(b)
        if not da or not db or not db["last"]:
            return None, None
        last = da["last"] / db["last"]
        prev = (da["prev"] / db["prev"]) if db["prev"] else last
        chg = (last - prev) / prev * 100 if prev else None
        return last, chg
    return None, None


def is_triggered(ind, value, change):
    t = ind["type"]
    if t == "level":
        if value is None:
            return None
        return value > ind["threshold"] if ind["op"] == "above" else value < ind["threshold"]
    if t == "change":
        if change is None:
            return None
        th, op = ind["threshold"], ind["op"]
        if op == "abs":
            return abs(change) >= th
        if op == "down":
            return change <= -th
        if op == "up":
            return change >= th
    return None


def fmt_value(ind, value, change):
    if value is None:
        return "데이터 없음"
    if ind["type"] == "change" and change is not None:
        return f"{value:,.2f} (전일 {change:+.2f}%)"
    return f"{value:,.2f}"


# ──────────────────────────────────────────────────────────────
# 텔레그램
# ──────────────────────────────────────────────────────────────
def send_telegram(text):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[error] TELEGRAM_TOKEN / TELEGRAM_CHAT_ID 미설정")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": chat_id, "text": text,
                                     "parse_mode": "HTML",
                                     "disable_web_page_preview": True}, timeout=20)
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"[error] 텔레그램 전송 실패: {e}")
        return False


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ──────────────────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────────────────
def main(yf_data=None, fred_key=None):
    fred_key = fred_key if fred_key is not None else os.environ.get("FRED_API_KEY", "")
    yf_data = yf_data if yf_data is not None else fetch_yf(collect_yf_ids())
    fred_cache = {}

    prev_state = load_state()
    first_run = not prev_state
    new_state = {}

    results = []   # (ind, value, change, triggered)
    for ind in config.INDICATORS:
        value, change = get_value(ind, yf_data, fred_cache, fred_key)
        trig = is_triggered(ind, value, change)
        new_state[ind["key"]] = bool(trig) if trig is not None else prev_state.get(ind["key"], False)
        results.append((ind, value, change, trig))

    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M KST")

    # 첫 실행: 현황만 요약, 알림 폭탄 방지
    if first_run:
        if config.SETTINGS.get("send_startup_summary", True):
            lines = [f"✅ <b>시장 모니터링 시작</b>  ({now})", ""]
            for ind, value, change, trig in results:
                mark = "🔔발동" if trig else ("· 정상" if trig is not None else "데이터없음")
                lines.append(f"{ind['label']}: {fmt_value(ind, value, change)} → {mark}")
            send_telegram("\n".join(lines))
        save_state(new_state)
        print("첫 실행 — 기준선 설정 완료")
        return

    # 신규 발동 / 복귀 감지
    fired, recovered = [], []
    for ind, value, change, trig in results:
        if trig is None:
            continue
        was = prev_state.get(ind["key"], False)
        if trig and not was:
            fired.append((ind, value, change))
        elif not trig and was and config.SETTINGS.get("alert_on_recovery", True):
            recovered.append((ind, value, change))

    # 복합 신호
    composite_msgs = []
    for comp in config.COMPOSITES:
        cur = sum(1 for k in comp["members"] if new_state.get(k))
        was = sum(1 for k in comp["members"] if prev_state.get(k))
        if cur >= comp["min_count"] and was < comp["min_count"]:
            active = [k for k in comp["members"] if new_state.get(k)]
            composite_msgs.append(
                f"🚨 <b>{comp['label']}</b>\n동시 발동 {cur}/{len(comp['members'])}개: "
                + ", ".join(active))

    # 메시지 조립
    blocks = []
    if fired:
        lines = [f"⚠️ <b>임계치 돌파 알림</b>  ({now})", ""]
        for ind, value, change in fired:
            icon = SEV_ICON.get(ind["severity"], "🟡")
            cond = ("하락" if ind.get("op") == "down" else
                    "급변동" if ind.get("op") == "abs" else
                    f"{ind['op']} {ind['threshold']}")
            lines.append(f"{icon} <b>{ind['label']}</b> [{ind['severity']}]\n"
                         f"   현재 {fmt_value(ind, value, change)}  (조건: {cond})")
        blocks.append("\n".join(lines))
    if composite_msgs:
        blocks.append("\n".join(composite_msgs))
    if recovered:
        lines = ["🟢 <b>정상 복귀</b>", ""]
        for ind, value, change in recovered:
            lines.append(f"· {ind['label']}: {fmt_value(ind, value, change)}")
        blocks.append("\n".join(lines))

    if blocks:
        send_telegram("\n\n".join(blocks))
        print(f"알림 전송: 발동 {len(fired)} / 복귀 {len(recovered)} / 복합 {len(composite_msgs)}")
    else:
        print("변동 없음 — 알림 미전송")

    save_state(new_state)


if __name__ == "__main__":
    main()
