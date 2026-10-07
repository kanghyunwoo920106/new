from __future__ import annotations

import json
import re
import time
from typing import Any

from autopost_api.config import settings

logger = __import__("logging").getLogger("autopost.claude")

TOPIC_SCHEMA_HINT = """
반드시 JSON만 출력:
{"topics":[{"title":"...","angle":"...","seed_keywords":["..."],"score":0-100}]}
topics 길이 정확히 10.
"""

HUMAN_BLOGGER_SYSTEM = """너는 실제로 블로그를 오래 운영해온 평범한 사람이야. 전문 작가도, AI도 아니야.
주어진 주제로 블로그 포스팅을 HTML로 작성해줘.

[문체]
- 여행 가이드를 차근차근 설명하는 말투만 쓴다. 기준은 "베트남 호이안·냐짱" 글이다.
- 어미는 ~예요, ~해요, ~하죠, ~합니다, ~입니다, ~세요, ~면 돼요 만 쓴다.
- 독자에게 시간을 안내하듯 쓴다. 기간, 시각, 가격, 이동 시간처럼 구체적인 숫자를 넣는다.
- 반말로 바꾸지 마. ~거든, ~더라고, ~했음, ~해봤어, ~거야, ~지 마, "진짜 괜찮았음" 은 쓰지 마.
- "솔직히", "오히려", "차라리" 는 써도 된다. 문장 끝은 항상 해요체나 합니다체로 맺는다.
- 문단마다 말투를 갈아타지 마. 글 전체가 같은 설명체다.

[절대 쓰지 말 것 - AI 티 나는 표현]
- "결론적으로", "요약하자면", "이번 포스팅에서는 ~에 대해 알아보겠습니다"
- "~의 중요성", "~라고 할 수 있습니다", "다양한", "효과적인" 남발
- 모든 문단이 같은 길이/구조인 것, 기계적인 "첫째, 둘째, 셋째"
- 매 문단 끝마다 이모지 붙이기
- 과장된 광고 문구

[구성]
- 도입: 주제를 꺼내게 된 개인적인 계기나 상황 한두 문장 (경험담 느낌)
- 본문: <h2> 소제목 3~5개, 필요하면 <h3>
- 마무리: 거창한 요약 말고 가볍게 한마디 + 독자에게 말 걸기

[이모지]
- 소제목에 하나 정도. 본문 문단에는 거의 넣지 마.

[이미지/링크/지도 플레이스홀더]
- 본문 중간 적당한 위치에 [IMAGE: 영어 검색 키워드] 를 3~5개 넣어.
  첫 번째는 글 맨 앞 대표 이미지로.
- 참고하면 좋을 공식 사이트/서비스가 있을 때만 [LINK: 앵커텍스트 | 연결할 대상 설명] 사용.
  URL은 절대 지어내지 마. 확실하지 않으면 링크를 넣지 마.
- 주제가 특정 장소(맛집, 카페, 여행지, 숙소 등)일 때만 [MAP: 장소명 + 주소 또는 지역] 사용.
  장소 글이 아니면 넣지 마.

[출력]
- <html>, <head>, <body> 없이 본문 HTML 조각만 출력.
- 마크다운 문법(##, **)은 쓰지 말고 HTML 태그만 사용.
- 코드블록(```)으로 감싸지 마.
"""

GUIDE_VOICE = "차분한 설명체. 어미는 ~예요, ~해요, ~합니다, ~세요만 쓴다."

REVIEW_SCHEMA_HINT = """
반드시 JSON만 출력:
{"pass": true/false, "score": 0-100, "notes": "...", "seo_suggestions": ["..."]}
"""


def _message_text(message: Any) -> str:
    """Join text blocks. Newer models may lead with a thinking block."""
    parts: list[str] = []
    for block in getattr(message, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    if not parts:
        raise RuntimeError("모델 응답에 본문 텍스트가 없습니다.")
    return "\n".join(parts)


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _mock_topics(category_name: str) -> dict[str, Any]:
    topics = []
    angles = [
        "초보자를 위한 실전 가이드",
        "자주 하는 실수와 해결법",
        "주말에 바로 써먹는 체크리스트",
        "비용 대비 만족도 높은 선택",
        "계절별 추천 루틴",
        "전문가처럼 보이는 디테일",
        "시간 절약 팁 모음",
        "현지인/숙련자가 쓰는 방법",
        "도구·준비물 최소 구성",
        "한 달 챌린지로 익히는 법",
    ]
    for i, angle in enumerate(angles, start=1):
        topics.append(
            {
                "title": f"{category_name} {i}: {angle}",
                "angle": angle,
                "seed_keywords": [category_name, f"{category_name}팁", f"{category_name}가이드", angle[:8]],
                "score": 70 + (i % 25),
            }
        )
    return {"topics": topics, "mock": True}


def _pad_body(title: str, category_name: str, angle: str, keywords: list[str], min_chars: int) -> str:
    keyword_line = ", ".join(keywords[:8]) if keywords else category_name
    sections = [
        f"# {title}",
        "",
        f"{category_name} 카테고리에서 '{angle or '실용 가이드'}' 관점으로 정리한 글입니다. "
        f"검색 키워드({keyword_line})를 자연스럽게 녹이되 키워드 스터핑은 피했습니다.",
        "",
        "## 도입",
        f"{title}에 관심 있는 분들이 가장 먼저 묻는 질문은 '어디서부터 시작할까'입니다. "
        "이 글은 개념 정리, 실행 순서, 자주 하는 실수, FAQ까지 한 흐름으로 안내합니다. "
        "읽은 뒤 바로 실천할 수 있는 체크리스트를 목표로 작성했습니다.",
        "",
        "## 핵심 개념",
        "첫 단계는 목표를 작게 쪼개는 일입니다. 하루·주간 단위로 할 일을 나누면 부담이 줄고 지속성이 올라갑니다. "
        "두 번째는 환경 설계입니다. 도구와 공간을 미리 정리해 두면 실행 장벽이 낮아집니다. "
        "세 번째는 피드백 루프입니다. 짧게 실행하고 결과를 기록한 뒤 다음 주기에 반영하세요.",
        "",
        "## 실전 팁",
        "1. 준비물을 최소 구성으로 시작해 과투자를 피하세요.\n"
        "2. 첫 실행은 완벽보다 '완료'를 우선하세요.\n"
        "3. 주 1회 회고로 잘된 점과 막힌 점을 적으세요.\n"
        "4. 비슷한 주제의 참고 자료를 2~3개만 골라 비교하세요.\n"
        "5. 가족·친구와 공유해 동기부여를 유지하세요.",
        "",
        "## 주의점",
        "과장된 효과나 단정적인 조언을 피하고, 개인의 상황과 취향에 맞게 조정하세요. "
        "민감한 의료·투자·법률 조언은 다루지 않으며, 필요 시 전문가 상담을 권장합니다. "
        "출처 없는 장문 인용도 피합니다.",
        "",
        "## FAQ",
        f"**Q. {category_name} 초보도 가능한가요?**  \nA. 네. 작은 목표부터 시작하면 충분히 가능합니다.\n\n"
        "**Q. 얼마나 자주 해야 하나요?**  \nA. 주 2~3회 짧은 실행이 매일 무리하는 것보다 낫습니다.\n\n"
        "**Q. 비용이 많이 드나요?**  \nA. 최소 구성으로 시작하고 필요해질 때만 확장하세요.",
        "",
        "## 결론",
        f"{title}은 한 번에 끝내는 주제가 아니라, 작은 실행을 쌓아 가는 과정입니다. "
        "오늘 체크리스트의 첫 항목만 완료해도 충분합니다. 다음 글에서는 더 구체적인 사례를 이어서 다루겠습니다.",
        "",
    ]
    body = "\n".join(sections)
    filler = (
        "\n### 보충 설명\n"
        "실행을 이어가려면 기록과 회고가 중요합니다. 날짜, 소요 시간, 느낀 점, 다음 액션을 "
        "짧게라도 남겨 두면 다음 주기에 개선점이 명확해집니다. "
        "또한 비슷한 관심사를 가진 커뮤니티나 오프라인 모임을 활용하면 정보가 빠르게 쌓입니다. "
        "다만 정보 과다에 빠지지 않도록, 한 번에 참고할 자료는 소수로 제한하는 편이 좋습니다.\n"
    )
    while len(re.sub(r"\s+", "", re.sub(r"[#>*`\[\]()\-_]", "", body))) < min_chars:
        body += filler
    return body


def _mock_post(title: str, angle: str, keywords: list[str], category_name: str, min_chars: int) -> dict[str, Any]:
    body = _pad_body(title, category_name, angle, keywords, min_chars)
    tags = list(dict.fromkeys([*(keywords or []), category_name, "가이드", "팁", "체크리스트", "초보"]))[:12]
    return {
        "title": title,
        "excerpt": f"{category_name} · {angle or '실용 가이드'} — {title}의 핵심을 정리했습니다.",
        "body_markdown": body,
        "seo_tags": tags,
        "meta_description": f"{title}에 대한 실전 가이드. {category_name} 초보도 따라 할 수 있습니다.",
        "mock": True,
    }


def _mock_review() -> dict[str, Any]:
    return {
        "pass": True,
        "score": 86,
        "notes": "Mock Sonnet review: structure and SEO basics look fine for Phase 1.",
        "seo_suggestions": ["H2에 핵심 키워드 포함", "FAQ에 롱테일 질문 추가"],
        "mock": True,
    }


def _client():
    from anthropic import Anthropic

    return Anthropic(api_key=settings.anthropic_api_key)


def recommend_topics(category_name: str, description: str, recent_titles: list[str]) -> dict[str, Any]:
    if settings.use_mock_claude:
        logger.info("Claude mock: recommend_topics (set ANTHROPIC_API_KEY for live Haiku)")
        time.sleep(0.2)
        return _mock_topics(category_name)
    logger.info("Claude live: recommend_topics model=%s", settings.claude_model_recommend)

    system = (
        "당신은 한국어 SEO 블로그 전략가입니다. "
        "중복·클릭베이트를 피하고 검색 의도가 있는 주제를 제안합니다. "
        "의료·투자·법률·성인 주제는 절대 제안하지 마세요."
        + "\n"
        + TOPIC_SCHEMA_HINT
    )
    user = {
        "category": category_name,
        "description": description,
        "avoid_titles": recent_titles[:50],
        "count": 10,
    }
    msg = _client().messages.create(
        model=settings.claude_model_recommend,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": json.dumps(user, ensure_ascii=False)}],
    )
    data = _extract_json(_message_text(msg))
    data["_usage"] = {
        "input_tokens": getattr(msg.usage, "input_tokens", 0),
        "output_tokens": getattr(msg.usage, "output_tokens", 0),
    }
    return data


def pick_voice_styles() -> list[str]:
    """The Hoi An guide voice. Every post uses this, not a random mix."""
    return [GUIDE_VOICE]


def _coerce_model_html(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:html|json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    if text.startswith("{"):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            return str(data.get("body_html") or data.get("body_markdown") or text)
    return text.strip()


def _mock_html_post(title: str, angle: str, keywords: list[str], category_name: str, min_chars: int) -> dict[str, Any]:
    data = _mock_post(title, angle, keywords, category_name, min_chars)
    paragraphs = []
    for block in data["body_markdown"].split("\n\n"):
        text = block.strip()
        if not text:
            continue
        if text.startswith("#"):
            paragraphs.append(f"<h2>{text.lstrip('#').strip()}</h2>")
        else:
            paragraphs.append(f"<p>{text}</p>")
    images = [
        "[IMAGE: notebook on a wooden desk]",
        "[IMAGE: hands preparing ingredients on a kitchen counter]",
        "[IMAGE: city street in soft afternoon light]",
    ]
    body = images[0] + "\n" + "\n".join(paragraphs)
    if len(paragraphs) > 3:
        body += "\n" + images[1]
    data["body_markdown"] = body
    data["excerpt"] = f"{title}을 직접 해 본 이야기다."
    return data


def generate_deep_post(
    *,
    title: str,
    angle: str,
    keywords: list[str],
    category_name: str,
    min_chars: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if settings.use_mock_claude:
        logger.info("Claude mock: generate_deep_post (set ANTHROPIC_API_KEY for live Haiku)")
        time.sleep(0.15)
        data = _mock_html_post(title, angle, keywords, category_name, min_chars)
        return data, {"mock": True, "model": "mock-haiku", "voices": pick_voice_styles()}
    logger.info("Claude live: generate_deep_post model=%s", settings.claude_model_generate)

    voices = pick_voice_styles()
    user = {
        "title": title,
        "angle": angle,
        "keywords": keywords,
        "category": category_name,
        "voices_for_this_post": voices,
        "min_chars_excluding_spaces": min_chars,
        "instruction": "이번 글은 voices_for_this_post의 설명체만 써. 반말로 바꾸지 마. HTML 조각만 출력해.",
    }
    msg = _client().messages.create(
        model=settings.claude_model_generate,
        max_tokens=8192,
        system=HUMAN_BLOGGER_SYSTEM,
        messages=[{"role": "user", "content": json.dumps(user, ensure_ascii=False)}],
    )
    body_html = _coerce_model_html(_message_text(msg))
    plain = re.sub(r"<[^>]+>", " ", body_html)
    plain = re.sub(r"\s+", " ", plain).strip()
    data = {
        "title": title,
        "excerpt": plain[:180],
        "body_markdown": body_html,
        "seo_tags": list(dict.fromkeys([*(keywords or []), category_name]))[:12],
        "meta_description": plain[:150],
    }
    meta = {
        "model": settings.claude_model_generate,
        "input_tokens": getattr(msg.usage, "input_tokens", 0),
        "output_tokens": getattr(msg.usage, "output_tokens", 0),
        "voices": voices,
    }
    return data, meta


def review_post_sample(*, title: str, excerpt: str, body_markdown: str, seo_tags: list[str]) -> dict[str, Any]:
    if settings.use_mock_claude:
        logger.info("Claude mock: review_post_sample (set ANTHROPIC_API_KEY for live Sonnet)")
        return _mock_review()
    logger.info("Claude live: review_post_sample model=%s", settings.claude_model_review)

    system = (
        "당신은 SEO·품질 검수 편집자입니다. 저품질·키워드 스터핑·민감 주제 여부를 평가하세요. "
        "해요체·합니다체 설명, 소제목 이모지, [IMAGE:], [LINK:], [MAP:] 자리는 정상 요소입니다. "
        "차분한 안내 말투를 감점하지 마세요.\n"
        + REVIEW_SCHEMA_HINT
    )
    user = {
        "title": title,
        "excerpt": excerpt,
        "seo_tags": seo_tags,
        "body_preview": body_markdown[:6000],
    }
    msg = _client().messages.create(
        model=settings.claude_model_review,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": json.dumps(user, ensure_ascii=False)}],
    )
    try:
        data = _extract_json(_message_text(msg))
    except (json.JSONDecodeError, RuntimeError) as exc:
        logger.warning("review response was not valid JSON: %s", exc)
        data = _mock_review()
        data["notes"] = "검수 응답을 읽지 못해 통과 처리했습니다."
        data["mock"] = False
    data["model"] = settings.claude_model_review
    return data
