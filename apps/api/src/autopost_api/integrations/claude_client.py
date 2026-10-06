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

POST_SCHEMA_HINT = """
반드시 JSON만 출력:
{
  "title": "...",
  "excerpt": "...",
  "body_markdown": "...",
  "seo_tags": ["..."],
  "meta_description": "..."
}
"""

REVIEW_SCHEMA_HINT = """
반드시 JSON만 출력:
{"pass": true/false, "score": 0-100, "notes": "...", "seo_suggestions": ["..."]}
"""


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
    data = _extract_json(msg.content[0].text)
    data["_usage"] = {
        "input_tokens": getattr(msg.usage, "input_tokens", 0),
        "output_tokens": getattr(msg.usage, "output_tokens", 0),
    }
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
        data = _mock_post(title, angle, keywords, category_name, min_chars)
        return data, {"mock": True, "model": "mock-haiku"}
    logger.info("Claude live: generate_deep_post model=%s", settings.claude_model_generate)

    system = (
        "당신은 AdSense 친화적 한국어 전문 블로그 작가입니다. "
        "사실에 기반한 심층 설명, 소제목(H2/H3), 요약, FAQ를 포함합니다. "
        "저작권 침해·의료/금융 단정 조언·자극적 허위정보를 피합니다. "
        f"본문(body_markdown)은 공백 제외 {min_chars}자 이상을 목표로 합니다.\n"
        + POST_SCHEMA_HINT
    )
    user = {
        "title": title,
        "angle": angle,
        "keywords": keywords,
        "category": category_name,
        "structure": ["도입", "핵심개념", "실전팁", "주의점", "FAQ", "결론"],
    }
    msg = _client().messages.create(
        model=settings.claude_model_generate,
        max_tokens=8192,
        system=system,
        messages=[{"role": "user", "content": json.dumps(user, ensure_ascii=False)}],
    )
    data = _extract_json(msg.content[0].text)
    meta = {
        "model": settings.claude_model_generate,
        "input_tokens": getattr(msg.usage, "input_tokens", 0),
        "output_tokens": getattr(msg.usage, "output_tokens", 0),
    }
    return data, meta


def review_post_sample(*, title: str, excerpt: str, body_markdown: str, seo_tags: list[str]) -> dict[str, Any]:
    if settings.use_mock_claude:
        logger.info("Claude mock: review_post_sample (set ANTHROPIC_API_KEY for live Sonnet)")
        return _mock_review()
    logger.info("Claude live: review_post_sample model=%s", settings.claude_model_review)

    system = (
        "당신은 SEO·품질 검수 편집자입니다. 저품질·키워드 스터핑·민감 주제 여부를 평가하세요.\n"
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
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": json.dumps(user, ensure_ascii=False)}],
    )
    data = _extract_json(msg.content[0].text)
    data["model"] = settings.claude_model_review
    return data
