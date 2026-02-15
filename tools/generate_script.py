"""
Script Generation Tool
Generates high-retention video scripts using Groq API (Llama 3.1 8B).
"""

import json
import os
import sys
import re
import time
import datetime
from groq import Groq
from dotenv import load_dotenv

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

load_dotenv()

PROMPT_TEMPLATE = """You are a professional narrator and educational scriptwriter.

TASK: Write a concise 60-90 second narration script about: "{topic}"

REQUIREMENTS:
1. Opening: Start with an engaging question or compelling statement (5-8 seconds)
2. Body: Present 3-5 clear, informative points with smooth transitions
3. Tone: Conversational yet authoritative, educational, and engaging
4. Ending: Conclude naturally with a thoughtful closing remark or key takeaway — do NOT include any call-to-action, promotional language, or viewer engagement prompts (no "subscribe", "like", "comment", "watch more", "check out", "channel", "video", etc.)
5. Segmentation: Break into 5-7 segments (1-3 sentences each)
6. Focus: Stay on-topic and deliver genuine insight — this is an informational narration, not a social media video

For each segment, provide:
- The narration text
- Estimated speaking duration in seconds
- 2-3 visual keywords (concrete nouns: objects, places, things) for sourcing stock footage
- A specific visual search query for stock footage websites (3-4 words)

OUTPUT FORMAT (strict JSON, no markdown, no code fences):
{{
  "full_script": "complete script text here",
  "segments": [
    {{
      "text": "segment narration text",
      "duration_estimate": 12.5,
      "visual_search_query": "futuristic space station rendering",
      "keywords": ["keyword1", "keyword2"]
    }}
  ]
}}

IMPORTANT: Return ONLY the raw JSON object. No markdown, no ```json fences, no extra text.
Do NOT include any references to YouTube, subscribing, liking, commenting, or any social media engagement language.

Generate the script now for: "{topic}"
"""


def generate_script(topic):
    """Generate a video script for the given topic using Groq API."""
    if not topic or topic.strip() == "":
        raise ValueError("Topic cannot be empty")

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        raise ValueError("GROQ_API_KEY not configured in .env")

    client = Groq(api_key=api_key)

    prompt = PROMPT_TEMPLATE.format(topic=topic)

    # Attempt generation with retries
    max_retries = 3
    last_error = None

    for attempt in range(max_retries):
        try:
            temperature = 0.7 if attempt == 0 else 0.5

            # Respect Groq free-tier rate limits: add a small delay between retries
            if attempt > 0:
                wait_time = 5 * attempt
                print(f"⏳ Waiting {wait_time}s before retry...")
                time.sleep(wait_time)

            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a JSON-only response bot. You MUST respond with valid JSON only. No markdown, no code fences, no explanations."
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model="llama-3.1-8b-instant",
                temperature=temperature,
                max_tokens=4000,
                response_format={"type": "json_object"},
            )

            raw_text = chat_completion.choices[0].message.content.strip()

            # Extract JSON from potential markdown or text
            start_idx = raw_text.find('{')
            end_idx = raw_text.rfind('}')

            if start_idx != -1 and end_idx != -1:
                raw_text = raw_text[start_idx:end_idx+1]
            else:
                # Fallback to stripping fences if braces not found
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                raw_text = re.sub(r"\s*```$", "", raw_text)

            script_data = json.loads(raw_text)

            # Validate structure
            if "full_script" not in script_data or "segments" not in script_data:
                raise ValueError("Missing required fields in LLM response")

            if not script_data["segments"]:
                raise ValueError("No segments in LLM response")

            # Calculate totals
            total_duration = sum(
                seg.get("duration_estimate", 10) for seg in script_data["segments"]
            )

            # Build output object
            output = {
                "topic": topic,
                "full_script": script_data["full_script"],
                "segments": script_data["segments"],
                "total_duration_estimate": round(total_duration, 1),
                "generated_at": datetime.datetime.now().isoformat(),
            }

            # Ensure each segment has keywords (fallback to topic words)
            topic_words = topic.lower().split()
            for seg in output["segments"]:
                if "keywords" not in seg or not seg["keywords"]:
                    seg["keywords"] = topic_words[:3]
                if "duration_estimate" not in seg:
                    seg["duration_estimate"] = len(seg["text"].split()) / 2.5

            # Save to .tmp
            os.makedirs(".tmp", exist_ok=True)
            with open(".tmp/script.json", "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)

            print(f"✅ Script generated: {len(output['segments'])} segments, "
                  f"~{output['total_duration_estimate']}s estimated duration")
            return output

        except json.JSONDecodeError as e:
            last_error = f"JSON parse error (attempt {attempt + 1}): {e}"
            print(f"⚠️  {last_error}")
        except Exception as e:
            last_error = f"Error (attempt {attempt + 1}): {e}"
            print(f"⚠️  {last_error}")
            error_str = str(e).lower()
            if "rate_limit" in error_str or "429" in error_str or "quota" in error_str:
                wait_time = 15 * (attempt + 1)  # 15s, 30s, 45s
                print(f"⚠️  Rate limit hit. Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                last_error = f"Generation error (attempt {attempt + 1}): {e}"
                print(f"⚠️  {last_error}")

    raise RuntimeError(f"Script generation failed after {max_retries} attempts: {last_error}")


if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else "The Science Behind Black Holes"
    result = generate_script(topic)
    print(json.dumps(result, indent=2, ensure_ascii=False))
