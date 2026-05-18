"""모기 생리학·매개체·방역 과학 지식 베이스.

AI 행정 판단 / AI 위험도 예보 등 보고서 작성 시 GPT 프롬프트에 주입.
출처: WHO Vector Surveillance, 질병관리청 매개체 감시 지침, KCDC 매개모기 자료.
"""

# ─ 모기 생리학 — 기온 기반 우화기간 (Aedes albopictus / Culex pipiens 평균) ─
THERMAL_BIOLOGY = {
    'temperature_zones': [
        {'range': (10, 15), 'effect': '우화 정지·산란 중단', 'larval_days': '>30', 'adult_lifespan': '5~7일'},
        {'range': (15, 20), 'effect': '우화 지연 (느림)', 'larval_days': '15~20', 'adult_lifespan': '7~14일'},
        {'range': (20, 25), 'effect': '우화 적정 하한', 'larval_days': '8~12', 'adult_lifespan': '14~18일'},
        {'range': (25, 28), 'effect': '우화 최적 (성충 발생 폭증 가능)', 'larval_days': '5~7', 'adult_lifespan': '18~28일'},
        {'range': (28, 32), 'effect': '우화 빠름·활동성 저하', 'larval_days': '4~5', 'adult_lifespan': '10~15일'},
        {'range': (32, 40), 'effect': '성충 활동·산란 억제', 'larval_days': '3~4', 'adult_lifespan': '5~10일'},
    ],
    'humidity_thresholds': [
        {'range': (75, 100), 'effect': '성충 생존 매우 유리 (수명 연장)'},
        {'range': (60, 75), 'effect': '성충 생존 적정'},
        {'range': (40, 60), 'effect': '성충 수명 단축'},
        {'range': (0, 40), 'effect': '성충 활동 크게 위축'},
    ],
    'precipitation_lag': {
        'description': '강수 후 새 산란지 형성 → 5~7일 후 1차 우화 피크, 12~14일 후 2차 피크',
        'optimal_rainfall_mm': '10~30mm 단발성 (과도하면 유충 휩쓸림)',
    },
}

# ─ 매개체별 활동 조건 + 위험 질병 ─
VECTORS = [
    {
        'species': '작은빨간집모기 (Culex tritaeniorhynchus)',
        'diseases': ['일본뇌염', '웨스트나일열'],
        'peak_temp': (24, 28),
        'peak_humidity': 70,
        'active_hours': '19:00~24:00',
        'breeding_site': '논·습지·축사 주변',
        'risk_note': '8~10월 일본뇌염 매개종. 평균기온 25°C 이상 + 누적강수 100mm 이상 시 폭증.',
    },
    {
        'species': '얼룩날개모기 (Anopheles sinensis)',
        'diseases': ['삼일열말라리아'],
        'peak_temp': (18, 22),
        'peak_humidity': 65,
        'active_hours': '18:00~22:00',
        'breeding_site': '논·연못·저수지',
        'risk_note': '주로 야간 22시 이전 활동. 강수 1~2주 후 우화 피크.',
    },
    {
        'species': '흰줄숲모기 (Aedes albopictus)',
        'diseases': ['뎅기열', '지카', '치쿤구니야'],
        'peak_temp': (25, 30),
        'peak_humidity': 75,
        'active_hours': '주간 (해질녘 + 새벽)',
        'breeding_site': '인공용기·폐타이어·화분받침',
        'risk_note': '주간 활동성. 도심 인공용기 제거가 핵심. 해외유입 환자 발생시 국지 전파 위험.',
    },
    {
        'species': '빨간집모기 (Culex pipiens)',
        'diseases': ['웨스트나일열', '상시 흡혈피해'],
        'peak_temp': (25, 28),
        'peak_humidity': 70,
        'active_hours': '18:00~05:00 (야간)',
        'breeding_site': '하수·정화조·도시 고인물',
        'risk_note': '도시 우점종. 민원 다발 매개종.',
    },
]


def assess_vector_risks(avg_temp, avg_humidity, recent_rainfall_mm=0):
    """기상 조건으로 매개체별 활동 위험 점수 (0~100) 산출."""
    if avg_temp is None or avg_humidity is None:
        return []
    risks = []
    for v in VECTORS:
        # 기온 적합도 (0~100)
        t_lo, t_hi = v['peak_temp']
        t_center = (t_lo + t_hi) / 2
        t_dist = abs(avg_temp - t_center) / max(1, (t_hi - t_lo))
        t_score = max(0, 100 - t_dist * 50)
        # 습도 적합도
        h_diff = abs(avg_humidity - v['peak_humidity'])
        h_score = max(0, 100 - h_diff * 1.5)
        # 강수 보너스 (말라리아·일본뇌염은 강수 의존)
        rain_bonus = 0
        if recent_rainfall_mm and v['species'].startswith(('작은빨간', '얼룩날개')):
            rain_bonus = min(20, recent_rainfall_mm * 1.5)
        risk = round(min(100, t_score * 0.6 + h_score * 0.3 + rain_bonus), 1)
        if risk >= 70:
            level = '높음'
        elif risk >= 50:
            level = '보통'
        elif risk >= 30:
            level = '낮음'
        else:
            level = '매우 낮음'
        risks.append({
            'species': v['species'],
            'diseases': v['diseases'],
            'active_hours': v['active_hours'],
            'breeding_site': v['breeding_site'],
            'risk_score': risk,
            'risk_level': level,
            'note': v['risk_note'],
        })
    risks.sort(key=lambda x: -x['risk_score'])
    return risks


# ─ 방역 방법 효과 지속성 (인용용) ─
REMEDY_SCIENCE = {
    'Bti 살포': '유충제 (Bacillus thuringiensis israelensis). 유충 단계 표적, 48시간 내 사망률 90%+. 효과 7~10일.',
    '잔류분무': '성충 표적. 벽면 분무 후 14~21일간 접촉 사멸. 옥내·축사 효과적.',
    'ULV 연막': '공간분무. 즉시 살충 효과. 야간 18~22시 시행이 효율 최대.',
    '용기제거': '서식지 차단. 인공용기 제거 시 흰줄숲모기 95% 감소 가능. 흡혈피해 30~50% 감소.',
}


def thermal_zone_for(temp):
    """기온 → 우화 영역 매핑."""
    if temp is None:
        return None
    for zone in THERMAL_BIOLOGY['temperature_zones']:
        lo, hi = zone['range']
        if lo <= temp < hi:
            return zone
    return THERMAL_BIOLOGY['temperature_zones'][-1] if temp >= 32 else THERMAL_BIOLOGY['temperature_zones'][0]


def humidity_zone_for(h):
    if h is None:
        return None
    for zone in THERMAL_BIOLOGY['humidity_thresholds']:
        lo, hi = zone['range']
        if lo <= h <= hi:
            return zone
    return None
