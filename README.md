# 시장 버블 모니터링 알림 봇

야후 파이낸스·FRED에서 시장 지표를 수집해, **임계치를 넘는 순간** 텔레그램으로 알림을 보냅니다.
GitHub Actions로 30분마다 클라우드에서 자동 실행되므로 **내 PC를 켜둘 필요가 없습니다.**

---

## 무엇을 감시하나

- 변동성: VIX (20·30 단계)
- 금리: 미국 10년·30년물, 장단기 금리차(10Y-2Y, FRED)
- 신용: 하이일드 스프레드 OAS(FRED), 하이일드 ETF(HYG)
- 환율: 원/달러, 엔/달러(엔캐리 청산 급변동), 달러인덱스
- 안전자산·원자재: 금 급락, 금/은 비율, 구리 급락
- 증시·위험자산: S&P500·반도체(SOX)·러셀2000·지역은행(KRE)·비트코인 급락
- **복합경보**: VIX·하이일드·HYG·원달러 중 2개 이상 동시 발동 시 시스템 리스크 경보

임계치는 전부 `config.py` 의 숫자만 바꾸면 됩니다. (코드는 안 건드려도 됨)

---

## 설치 (약 15분, 한 번만)

### 1) 텔레그램 봇 만들기
1. 텔레그램에서 **@BotFather** 검색 → `/newbot` → 이름 정하기 → **봇 토큰** 복사
   (형태: `1234567890:AAH...`)
2. 방금 만든 내 봇과 대화 시작 → 아무 메시지나 한 번 보냄
3. 내 **chat id** 확인: 브라우저에서 아래 주소 접속 (토큰 자리에 본인 토큰)
   `https://api.telegram.org/bot<봇토큰>/getUpdates`
   결과 JSON에서 `"chat":{"id": 숫자}` 의 숫자가 chat id 입니다.

### 2) FRED API 키 (선택, 무료)
- https://fredaccount.stlouisfed.org/apikeys 에서 무료 발급
- 없어도 동작합니다 (장단기 금리차·하이일드 OAS 두 항목만 건너뜀)

### 3) GitHub 저장소 만들기
1. github.com 에서 새 저장소 생성
   - **Public(공개) 권장** → Actions 무료 무제한. (비밀키는 코드가 아니라 Secrets에 저장하므로 공개해도 안전)
   - Private이면 무료 한도 월 2,000분 → cron을 `0 * * * *`(1시간) 정도로 낮추세요
2. 이 폴더의 파일들(`monitor.py`, `config.py`, `requirements.txt`, `.github/`)을 업로드/푸시

### 4) 비밀키 등록
저장소 → **Settings → Secrets and variables → Actions → New repository secret** 에서 등록:
| 이름 | 값 |
|------|-----|
| `TELEGRAM_TOKEN` | 봇 토큰 |
| `TELEGRAM_CHAT_ID` | 내 chat id |
| `FRED_API_KEY` | FRED 키 (선택) |

### 5) 동작 확인
- 저장소 → **Actions** 탭 → `market-alert` → **Run workflow**(수동 실행)
- 첫 실행 시 텔레그램으로 **"✅ 시장 모니터링 시작" 현황 요약**이 옵니다.
- 이후 30분마다 자동 점검 → **임계치를 넘을 때만** 알림이 옵니다.

---

## 임계치 바꾸기
`config.py` 에서 해당 줄의 `threshold` 숫자만 수정 후 저장소에 푸시하면 즉시 반영됩니다.
예: VIX 경보를 18로 낮추려면 `"key": "vix20"` 줄의 `"threshold": 20` → `18`.

알림이 너무 잦으면 `change` 타입의 `threshold`(%)를 올리고,
복귀 알림이 불필요하면 `config.py` 의 `"alert_on_recovery": False`.

---

## 알아둘 점 (한계)

- **데이터는 약 15분 지연**됩니다. 매크로 모니터링엔 충분하지만 초단타용은 아닙니다.
- `yfinance`는 비공식 라이브러리라 가끔 일부 티커가 일시적으로 안 받아질 수 있습니다(해당 항목만 자동 스킵, 프로그램은 계속 동작).
- GitHub의 예약 실행은 **정시 정확도가 아니라 최선노력(best-effort)**이라 몇 분 늦을 수 있습니다.
- 저장소가 **60일간 활동이 없으면 예약 실행이 자동 중지**됩니다(아무 커밋이나 하면 재개).
- MOVE 지수·Put/Call은 깔끔한 무료 API가 없어 제외했습니다. 필요하면 별도 소스 연동이 필요합니다.
- 이 봇은 **감시·알림**까지입니다. 매매를 대신하지 않으며, 투자 판단·책임은 본인에게 있습니다.

---

## 로컬 PC에서 테스트로 한 번 돌려보기 (선택)
```bash
pip install -r requirements.txt
export TELEGRAM_TOKEN="봇토큰"
export TELEGRAM_CHAT_ID="챗아이디"
export FRED_API_KEY="프레드키"   # 선택
python monitor.py
```
