"""AI health data insight MVP mockup API and page."""

from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

from app.templating import templates

router = APIRouter(tags=['healthtest'])


class HealthInput(BaseModel):
    model_config = ConfigDict(extra='forbid')

    gender: Literal['female', 'male', 'other']
    age: int = Field(ge=1, le=120)
    height_cm: float = Field(ge=80, le=230)
    weight_kg: float = Field(ge=20, le=250)
    systolic_bp: int = Field(ge=70, le=250)
    diastolic_bp: int = Field(ge=40, le=150)
    fasting_glucose: float = Field(ge=40, le=500)
    medication: Literal['yes', 'no']
    symptoms: str = Field(default='', max_length=500)
    smoking: Literal['yes', 'no']
    alcohol: Literal['none', 'monthly', 'weekly', 'often']
    exercise: Literal['none', 'low', 'moderate', 'high']


def _mock_result(payload: HealthInput) -> dict:
    """Fixed demo result; replace this adapter with a real inference client later."""
    today = date.today()
    return {
        'score': 78,
        'risk_level': '낮음',
        'summary': '입력된 건강 정보를 기준으로 현재 종합 지표는 양호한 수준입니다.',
        'blood_pressure_note': '혈압 관련 지표는 정상 범위에 가깝지만, 지속적인 측정과 생활습관 관리가 필요합니다.',
        'indicators': {'blood_pressure': 72, 'blood_sugar': 81, 'lifestyle': 76, 'medication': 84},
        'trend': [
            {'date': (today - timedelta(days=4 - i)).isoformat(), 'value': value}
            for i, value in enumerate([71, 74, 75, 77, 78])
        ],
        'recommendations': ['규칙적인 혈압 측정을 권장합니다.', '주 3회 이상 가벼운 유산소 운동을 권장합니다.', '충분한 수분 섭취와 수면 관리를 권장합니다.'],
        'input_summary': {
            'gender': {'female': '여성', 'male': '남성', 'other': '기타'}[payload.gender],
            'age': payload.age, 'height_cm': payload.height_cm, 'weight_kg': payload.weight_kg,
            'systolic_bp': payload.systolic_bp, 'diastolic_bp': payload.diastolic_bp,
            'fasting_glucose': payload.fasting_glucose,
        },
        'is_mock': True,
        'disclaimer': '본 결과는 서비스 화면 예시를 위한 목업 데이터이며, 의료적 진단이나 치료를 대신하지 않습니다.',
    }


@router.get('/healthtest/', response_class=HTMLResponse)
async def healthtest_page(request: Request):
    return templates.TemplateResponse(request, 'healthtest/index.html', {})


@router.get('/api/health')
async def health_api():
    return {'status': 'ok', 'service': 'health-insight-mock', 'is_mock': True}


@router.post('/api/analyze')
async def analyze_api(payload: HealthInput):
    return _mock_result(payload)
