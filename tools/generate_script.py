"""
Script Generation Tool
Generates high-retention video scripts using Gemini API.
"""

import json
import os
import sys
import re
import time
import datetime
import google.generativeai as genai
from dotenv import load_dotenv

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

load_dotenv()

PROMPT_TEMPLATE = """You are a YouTube scriptwriter specializing in high-retention short-form content.

TASK: Write a 60-90 second video script on the topic: "{topic}"

REQUIREMENTS:
1. Hook: Start with an attention-grabbing question or bold statement (5 seconds)
2. Structure: 3-5 clear, concise points with smooth transitions
3. Tone: Conversational, energetic, educational
4. Call-to-Action: End with a subscribe prompt or teaser (5 seconds)
5. Segmentation: Break into 5-7 segments (1-3 sentences each)

For each segment, provide:
- The narration text
- Estimated speaking duration in seconds
- 2-3 visual keywords (concrete nouns: objects, places, things) for sourcing stock footage
- A specific visual search query for stock footage websites (3-4 words)

OUTPUT FORMAT (strict JSON, no markdown):
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

Generate the script now for: "{topic}"
"""


def generate_script(topic):
    """Generate a video script for the given topic using Gemini API."""
    if not topic or topic.strip() == "":
        raise ValueError("Topic cannot be empty")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        raise ValueError("GEMINI_API_KEY not configured in .env")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = PROMPT_TEMPLATE.format(topic=topic)

    # Attempt generation with retries
    max_retries = 5
    last_error = None

    for attempt in range(max_retries):
        try:
            temperature = 0.7 if attempt == 0 else 0.5
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=4000,
                    response_mime_type="application/json",
                ),
            )

            raw_text = response.text.strip()

            # Extract JSON from potential markdown or text
            start_idx = raw_text.find('{')
            end_idx = raw_text.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                raw_text = raw_text[start_idx:end_idx+1]
            else:
                # Fallback to stripping fences if braces not found (unlikely for valid JSON)
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
            if "quota" in error_str or "429" in error_str or "resource" in error_str:
                wait_time = 15 * (2 ** attempt)  # 15s, 30s, 60s, 120s, 240s
                print(f"⚠️  Quota/rate limit hit (attempt {attempt + 1}). Waiting {wait_time}s...")
                time.sleep(wait_time)
                last_error = f"Quota exceeded (attempt {attempt + 1})"
            else:
                last_error = f"Generation error (attempt {attempt + 1}): {e}"
                print(f"⚠️  {last_error}")

    raise RuntimeError(f"Script generation failed after {max_retries} attempts: {last_error}")


if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else "The Science Behind Black Holes"
    result = generate_script(topic)
    print(json.dumps(result, indent=2, ensure_ascii=False))
