"""Non-sensitive category allowlist. Medical/investment/legal/adult are blocked."""

from __future__ import annotations

ALLOWED_CATEGORIES: list[dict[str, str]] = [
    {
        "name": "여행",
        "slug": "travel",
        "description": "국내외 여행 팁, 일정 짜기, 현지 문화와 교통 안내",
        "adsense_slot_hint": "in-article-travel",
    },
    {
        "name": "음식·요리",
        "slug": "food",
        "description": "홈쿠킹 레시피, 재료 고르기, 주방 팁과 맛집 탐방",
        "adsense_slot_hint": "in-article-food",
    },
    {
        "name": "취미·공예",
        "slug": "hobby",
        "description": "사진, DIY, 독서, 보드게임 등 취미 입문과 심화",
        "adsense_slot_hint": "in-article-hobby",
    },
    {
        "name": "생활·정리",
        "slug": "lifestyle",
        "description": "정리수납, 루틴, 가사 효율, 일상 라이프핵",
        "adsense_slot_hint": "in-article-lifestyle",
    },
    {
        "name": "디지털·생산성",
        "slug": "productivity",
        "description": "노트 앱, 업무 도구, 집중법, 디지털 미니멀",
        "adsense_slot_hint": "in-article-productivity",
    },
    {
        "name": "반려동물",
        "slug": "pets",
        "description": "반려견·반려묘 일상 케어, 훈련 기초, 용품 고르기(의료 진단 제외)",
        "adsense_slot_hint": "in-article-pets",
    },
    {
        "name": "환경·제로웨이스트",
        "slug": "eco",
        "description": "친환경 생활 습관, 재활용, 지속가능한 소비",
        "adsense_slot_hint": "in-article-eco",
    },
    {
        "name": "문화·예술",
        "slug": "culture",
        "description": "전시, 공연, 영화, 도서 리뷰와 감상 가이드",
        "adsense_slot_hint": "in-article-culture",
    },
]

BLOCKED_CATEGORY_KEYWORDS = (
    "의료",
    "병원",
    "진단",
    "처방",
    "투자",
    "주식",
    "코인",
    "재테크",
    "법률",
    "소송",
    "성인",
    "도박",
    "보험상품",
)


def is_blocked_category_name(name: str) -> bool:
    lowered = name.strip().lower()
    return any(k.lower() in lowered for k in BLOCKED_CATEGORY_KEYWORDS)
