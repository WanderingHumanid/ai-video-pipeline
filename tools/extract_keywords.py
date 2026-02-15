"""Extracts visual search keywords from script segments for media sourcing."""

import json
import os
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

ABSTRACT_NOUNS = {
    "idea", "concept", "freedom", "way", "thing", "stuff", "item",
    "time", "fact", "point", "part", "lot", "kind", "type", "example",
    "question", "answer", "reason", "result", "problem", "issue",
    "moment", "ability", "power", "sense", "world", "life", "end",
}

CATEGORY_FALLBACKS = {
    "science": ["space", "lab", "microscope"],
    "technology": ["computer", "digital", "robot"],
    "nature": ["forest", "ocean", "mountain"],
    "history": ["ancient", "monument", "battlefield"],
    "health": ["hospital", "exercise", "nutrition"],
    "finance": ["money", "stock market", "office"],
    "education": ["classroom", "books", "university"],
}


def extract_keywords_from_segments(script_data):
    topic = script_data.get("topic", "")
    segments = script_data.get("segments", [])

    if not segments:
        raise ValueError("No segments provided")

    keywords_by_segment = []
    all_keywords = []

    for i, segment in enumerate(segments):
        text = segment.get("text", "")
        llm_keywords = segment.get("keywords", [])

        valid_keywords = []
        for kw in llm_keywords:
            kw_lower = kw.lower().strip()
            if kw_lower and kw_lower not in ABSTRACT_NOUNS and len(kw_lower) > 2:
                valid_keywords.append(kw_lower)

        if len(valid_keywords) < 2:
            text_keywords = _extract_nouns_simple(text)
            for kw in text_keywords:
                if kw not in valid_keywords:
                    valid_keywords.append(kw)
                if len(valid_keywords) >= 3:
                    break

        if not valid_keywords:
            valid_keywords = [w.lower() for w in topic.split() if len(w) > 3][:3]

        if not valid_keywords:
            valid_keywords = ["nature", "technology", "abstract"]

        valid_keywords = valid_keywords[:3]

        segment_entry = {
            "segment_index": i,
            "text": text,
            "keywords": valid_keywords,
            "primary_keyword": valid_keywords[0],
            "visual_search_query": segment.get("visual_search_query", valid_keywords[0])
        }
        keywords_by_segment.append(segment_entry)

        for kw in valid_keywords:
            if kw not in all_keywords:
                all_keywords.append(kw)

    output = {
        "keywords_by_segment": keywords_by_segment,
        "all_keywords": all_keywords,
    }

    os.makedirs(".tmp", exist_ok=True)
    with open(".tmp/keywords.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"✅ Keywords extracted: {len(keywords_by_segment)} segments, "
          f"{len(all_keywords)} unique keywords")
    return output


def _extract_nouns_simple(text):
    """Extract likely nouns from text using a simple heuristic."""
    words = re.findall(r"\b[A-Za-z]+\b", text)
    candidates = []

    for word in words:
        w_lower = word.lower()
        if len(w_lower) <= 3:
            continue
        if w_lower in ABSTRACT_NOUNS:
            continue
        if w_lower in {"have", "been", "will", "would", "could", "should",
                        "just", "very", "really", "also", "even", "more",
                        "most", "than", "then", "when", "where", "what",
                        "that", "this", "with", "from", "into", "about",
                        "your", "they", "them", "their", "some", "like",
                        "make", "know", "take", "come", "want", "look",
                        "think", "call", "does", "made", "find", "here",
                        "many", "well", "only", "tell", "much", "before",
                        "after", "over", "such", "good", "each", "those",
                        "said", "never", "ever", "didn", "can", "still"}:
            continue
        if w_lower not in candidates:
            candidates.append(w_lower)

    return candidates[:5]


def get_simplified_keyword(keyword):
    keyword_lower = keyword.lower()

    for category, fallbacks in CATEGORY_FALLBACKS.items():
        if category in keyword_lower or keyword_lower in fallbacks:
            return fallbacks[0]

    words = keyword_lower.split()
    if len(words) > 1:
        return words[-1]

    return keyword_lower


if __name__ == "__main__":
    script_path = ".tmp/script.json"
    if not os.path.exists(script_path):
        print("❌ No script found. Run generate_script.py first.")
        sys.exit(1)

    with open(script_path, "r", encoding="utf-8") as f:
        script_data = json.load(f)

    result = extract_keywords_from_segments(script_data)
    print(json.dumps(result, indent=2, ensure_ascii=False))
