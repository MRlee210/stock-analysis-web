import os
import asyncio
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Ensure .env is loaded correctly regardless of execution directory
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
load_dotenv(env_path)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def _get_model_name(ai_level: str) -> str:
    mapping = {
        "상": "gemini-3.1-pro-preview",
        "중": "gemini-2.5-pro",
        "하": "gemini-3.1-flash-lite-preview"
    }
    return mapping.get(ai_level, "gemini-3.1-pro-preview")

async def get_ai_opinion_async(ticker: str, detailed_advice: str, ai_level: str = "상", market: str = "KR") -> str:
    if not GEMINI_API_KEY:
        return "⚠️ 오류: 시스템에 `GEMINI_API_KEY`가 설정되지 않아 AI 코멘트를 불러올 수 없습니다."
    
    market_context = "미국(US) 주식" if market == "US" else "한국(KRX) 주식"
    
    prompt = f"""
당신은 최고의 주식 전문 트레이더 AI입니다. 
다음은 특정 {market_context} 종목({ticker})에 대해 퀀트/로직 기반 알고리즘 분석기로부터 도출된 기술적 분석 요약 내용입니다:

---
{detailed_advice}
---

위의 데이터를 읽고, 이 종목에 대해 전문 트레이더의 시각에서 다음 사항을 고려해 최종 조언을 해 주세요:
1) 현재 이 종목의 위험도와 대응 전략 아이디어
2) 이 종목에 대해 지금 취해야 할 최적의 권장 행동
3) 추가로 실제 트레이더가 꼭 참고해야 할 꿀팁이나 보충 의견

[중요 작성 규칙 - 필독]
- 내용을 줄줄이 길게 연결하는 문자열 덩어리(Wall of text) 스타일은 **절대 금지**합니다.
- 반드시 가독성을 최우선으로 하여, 각 내용을 **항목별 불릿 포인트(-)**로 짧고 명확하게 끊어서 보여주세요.
- 내용 구분을 위해 Markdown 상위 제목(예: ### 📉 1. 리스크 및 대응 전략)을 넣어주세요.
- 친절하지만 확신 있는 '전문가 톤(해요체/하십시오체)'으로 작성해 주세요.
- **가장 중요**: 제공된 퀀트/지표 데이터(이평선 값, 지표 값, 캔들 패턴 등)와 사실에 기반해서만 분석하세요. 주어진 요약에 없는 지표 값(예: 스토캐스틱 수치, MACD 데드크로스, 존재하지 않는 캔들 패턴, 잘못된 배열 상태 등)이나 허위 차트 형태를 지어내어(할루시네이션) 설명하는 것은 **엄격히 금지**됩니다. 객관적 수치와 상태를 왜곡하지 마세요.
"""
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        model_name = _get_model_name(ai_level)
        response = await client.aio.models.generate_content(
            model=model_name,
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"⚠️ 오류: AI 코멘트를 생성하는 중 문제가 발생했습니다 ({str(e)})"

async def get_news_summary_async(ticker: str, ai_level: str = "상", requirements: str = "") -> str:
    if not GEMINI_API_KEY:
        return "⚠️ 오류: 시스템에 `GEMINI_API_KEY`가 설정되지 않아 뉴스를 불러올 수 없습니다."
        
    req_text = f"특별 요구사항: {requirements}" if requirements.strip() else ""
    
    prompt = f"""
최근 1주일 동안의 '{ticker}' 관련 국내외 주요 뉴스를 구글 검색을 통해 찾아주세요.
{req_text}

[중요 작성 규칙 - 필독]
- 반드시 검색 결과 항목마다 기사 헤드라인, 핵심 요약(1~2줄), 그리고 해당 기사의 원본 링크를 포함하세요.
- 각 기사는 가독성 좋게 Markdown 불릿 포인트나 숫자로 구분해 주세요.
- 기사 헤드라인에는 Markdown 링크 문법을 사용하여 즉시 클릭하여 이동할 수 있게 만들어주세요. (예: [삼성전자 사상 최대 실적 달성](http://example.com))
- 정보를 찾지 못했다면 찾지 못했다고 명확히 알려주세요.
"""
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        model_name = _get_model_name(ai_level)
        response = await client.aio.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}],
                temperature=0.3
            )
        )
        return response.text
    except Exception as e:
        return f"⚠️ 오류: 뉴스 정보를 가져오는 중 문제가 발생했습니다 ({str(e)})"
