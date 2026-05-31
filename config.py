# -*- coding: utf-8 -*-
"""
모니터링 설정 파일.
이 파일의 숫자만 바꾸면 됩니다. monitor.py 는 건드릴 필요 없습니다.

[type]
  "level"  : 값이 기준선을 above(위로)/below(아래로) 넘으면 발동
  "change" : 전일대비 변동률(%)이 조건을 넘으면 발동
             op="down" 하락, op="up" 상승, op="abs" 방향무관 급변동

[source]
  "yf"      : 야후 파이낸스 (yfinance)
  "fred"    : 미국 세인트루이스 연준 FRED (무료 API 키 필요)
  "derived" : 두 종목으로 계산 (예: 금/은 비율)
"""

SETTINGS = {
    "alert_on_recovery": True,      # 임계치 정상 복귀 시에도 한 번 알림
    "send_startup_summary": True,   # 첫 실행/상태초기화 시 전체 현황 1회 전송
}

INDICATORS = [
    # ── 변동성 ────────────────────────────────────────────────
    {"key": "vix20", "label": "VIX 공포지수", "source": "yf", "id": "^VIX",
     "type": "level", "op": "above", "threshold": 20, "severity": "경계"},
    {"key": "vix30", "label": "VIX 공포지수", "source": "yf", "id": "^VIX",
     "type": "level", "op": "above", "threshold": 30, "severity": "위험"},

    # ── 금리·채권 ─────────────────────────────────────────────
    {"key": "us10y", "label": "미국 10년물 금리", "source": "yf", "id": "^TNX",
     "type": "level", "op": "above", "threshold": 4.8, "severity": "경계"},
    {"key": "us30y", "label": "미국 30년물 금리", "source": "yf", "id": "^TYX",
     "type": "level", "op": "above", "threshold": 5.0, "severity": "경계"},
    {"key": "curve", "label": "장단기 금리차(10Y-2Y)", "source": "fred", "id": "T10Y2Y",
     "type": "level", "op": "below", "threshold": 0.0, "severity": "경계"},

    # ── 신용 스프레드 (FRED) ──────────────────────────────────
    {"key": "hyoas4", "label": "하이일드 스프레드(OAS)", "source": "fred", "id": "BAMLH0A0HYM2",
     "type": "level", "op": "above", "threshold": 4.0, "severity": "경계"},
    {"key": "hyoas5", "label": "하이일드 스프레드(OAS)", "source": "fred", "id": "BAMLH0A0HYM2",
     "type": "level", "op": "above", "threshold": 5.0, "severity": "위험"},
    {"key": "hyg_drop", "label": "하이일드 ETF(HYG)", "source": "yf", "id": "HYG",
     "type": "change", "op": "down", "threshold": 1.5, "severity": "경계"},

    # ── 환율 ──────────────────────────────────────────────────
    {"key": "krw", "label": "원/달러 환율", "source": "yf", "id": "KRW=X",
     "type": "level", "op": "above", "threshold": 1500, "severity": "경계"},
    {"key": "jpy_move", "label": "엔/달러(엔캐리 청산)", "source": "yf", "id": "JPY=X",
     "type": "change", "op": "abs", "threshold": 1.5, "severity": "경계"},
    {"key": "dxy", "label": "달러인덱스(DXY)", "source": "yf", "id": "DX-Y.NYB",
     "type": "level", "op": "above", "threshold": 108, "severity": "경계"},

    # ── 안전자산·원자재 ───────────────────────────────────────
    {"key": "gold_drop", "label": "금 급락(현금화 신호)", "source": "yf", "id": "GC=F",
     "type": "change", "op": "down", "threshold": 3.0, "severity": "경계"},
    {"key": "gs_ratio", "label": "금/은 비율", "source": "derived", "id": "GC=F/SI=F",
     "type": "level", "op": "above", "threshold": 85, "severity": "경계"},
    {"key": "copper_drop", "label": "구리 급락(경기둔화)", "source": "yf", "id": "HG=F",
     "type": "change", "op": "down", "threshold": 4.0, "severity": "경계"},

    # ── 위험자산·증시 ─────────────────────────────────────────
    {"key": "spx_drop", "label": "S&P500 급락", "source": "yf", "id": "^GSPC",
     "type": "change", "op": "down", "threshold": 3.0, "severity": "경계"},
    {"key": "sox_drop", "label": "필라델피아 반도체(SOX)", "source": "yf", "id": "^SOX",
     "type": "change", "op": "down", "threshold": 4.0, "severity": "경계"},
    {"key": "rut_drop", "label": "러셀2000(소형주)", "source": "yf", "id": "^RUT",
     "type": "change", "op": "down", "threshold": 3.0, "severity": "경계"},
    {"key": "kre_drop", "label": "지역은행 ETF(KRE)", "source": "yf", "id": "KRE",
     "type": "change", "op": "down", "threshold": 4.0, "severity": "경계"},
    {"key": "btc_drop", "label": "비트코인 급락", "source": "yf", "id": "BTC-USD",
     "type": "change", "op": "down", "threshold": 7.0, "severity": "경계"},
]

# 복합 신호: 아래 멤버 중 min_count개 이상이 '동시에' 발동되면 시스템 리스크 경보
COMPOSITES = [
    {"key": "systemic", "label": "시스템 리스크 복합경보",
     "members": ["vix20", "hyoas4", "hyg_drop", "krw"], "min_count": 2},
]
