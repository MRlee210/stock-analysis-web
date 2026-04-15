import os
import asyncio
from google import genai
from dotenv import load_dotenv

# Ensure .env is loaded correctly regardless of execution directory
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
load_dotenv(env_path)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

async def get_ai_opinion_async(ticker: str, detailed_advice: str) -> str:
    if not GEMINI_API_KEY:
        return "⚠️ 오류: 시스템에 `GEMINI_API_KEY`가 설정되지 않아 AI 코멘트를 불러올 수 없습니다. 프로젝트 최상위 폴더에 `.env` 파일을 만들고 키를 설정해 주세요!"
    
    prompt = f"""
당신은 최고의 주식 전문 트레이더 AI입니다. 
다음은 특정 종목({ticker})에 대해 퀀트/로직 기반 알고리즘 분석기로부터 도출된 기술적 분석 요약 내용입니다:

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
"""
    try:
        # 새로운 google-genai SDK 적용
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = await client.aio.models.generate_content(
            model='gemini-3.1-pro-preview',
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"⚠️ 오류: AI 코멘트를 생성하는 중 문제가 발생했습니다 ({str(e)})"
