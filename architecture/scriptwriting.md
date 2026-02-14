# Architecture SOP: Scriptwriting

**Component:** Script Generation (Layer 3 Tool)  
**Owner:** `tools/generate_script.py`  
**Purpose:** Generate high-retention video scripts from user-provided topics using Gemini 1.5 Flash

---

## 📋 Input Schema

```json
{
  "topic": "string (user-provided topic/title)"
}
```

**Example:** `{"topic": "The Science Behind Black Holes"}`

---

## 📤 Output Schema

```json
{
  "topic": "string",
  "full_script": "string (complete narration text)",
  "segments": [
    {
      "text": "string (sentence or paragraph)",
      "duration_estimate": "float (estimated seconds)",
      "keywords": ["string", "string"]
    }
  ],
  "total_duration_estimate": "float (total seconds)",
  "generated_at": "ISO 8601 datetime"
}
```

---

## 🎯 Behavioral Rules

### 1. Script Structure
The LLM must generate scripts optimized for **high retention**:
- **Hook (First 5 seconds):** Attention-grabbing opening question or statement
- **Body (60-90 seconds):** 3-5 key points with clear transitions
- **Call-to-Action (Last 5 seconds):** Subscribe prompt or teaser for next video

### 2. Tone & Style
- **Conversational:** Natural speech patterns (contractions, simple vocabulary)
- **Energetic:** Active voice, dynamic pacing
- **Educational:** Clear explanations without jargon overload

### 3. Duration Target
- **Target:** 60-90 seconds total
- **Rationale:** Optimal for YouTube Shorts and attention span
- **Flexibility:** Allow ±10 seconds variance

### 4. Segmentation Logic
Break the script into **segments** for visual mapping:
- Each segment = 1-3 sentences (10-20 seconds)
- Segment boundaries = natural pauses or topic shifts
- Extract 2-3 **visual keywords** per segment for media sourcing

---

## 🧠 LLM Prompt Template

```
You are a YouTube scriptwriter specializing in high-retention short-form content.

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
- 2-3 visual keywords (nouns: objects, places, concepts) for sourcing stock footage

OUTPUT FORMAT:
Return a JSON object with:
{
  "full_script": "complete script text",
  "segments": [
    {
      "text": "segment narration",
      "duration_estimate": 12.5,
      "keywords": ["black hole", "galaxy", "space"]
    }
  ]
}

EXAMPLE OUTPUT:
{
  "full_script": "Have you ever wondered what happens when you fall into a black hole? ...",
  "segments": [
    {
      "text": "Have you ever wondered what happens when you fall into a black hole?",
      "duration_estimate": 5.0,
      "keywords": ["black hole", "space", "astronaut"]
    },
    {
      "text": "A black hole is a region of spacetime where gravity is so strong that nothing, not even light, can escape.",
      "duration_estimate": 8.0,
      "keywords": ["gravity", "spacetime", "light"]
    }
  ]
}

Now generate the script for: "{topic}"
```

---

## ⚙️ Tool Implementation Logic

### Step 1: Input Validation
- Verify `topic` is a non-empty string
- Sanitize input (remove special characters if needed)

### Step 2: LLM Call
- Use Gemini 1.5 Flash via Antigravity's native integration
- Temperature: 0.7 (balance creativity and coherence)
- Max tokens: 1500 (sufficient for script + metadata)

### Step 3: Post-Processing
- Parse JSON response
- Calculate `total_duration_estimate` (sum of segment durations)
- Add `generated_at` timestamp
- Validate: Ensure total duration is 50-100 seconds

### Step 4: Keyword Extraction Fallback
If LLM doesn't provide keywords per segment:
- Extract nouns from each segment using NLP (e.g., spaCy)
- Filter: Keep only concrete nouns (avoid abstract terms)
- Limit: 2-3 keywords per segment

### Step 5: Output
- Save JSON to `.tmp/script.json`
- Return script object

---

## 🐛 Error Handling

### Error: LLM returns invalid JSON
- **Action:** Retry with temperature = 0.5 (more deterministic)
- **Fallback:** Parse text manually using regex to extract segments

### Error: Script too short (<50 seconds)
- **Action:** Retry with prompt: "Expand the script to 60-90 seconds with more detail"

### Error: Script too long (>100 seconds)
- **Action:** Retry with prompt: "Condense the script to 60-90 seconds, keeping only key points"

### Error: No keywords provided
- **Action:** Use keyword extraction fallback (NLP-based noun extraction)

---

## 🧪 Test Cases

### Test 1: Science Topic
- **Input:** `{"topic": "Black Holes"}`
- **Expected:** 60-90 second script with 5-7 segments, space-related keywords

### Test 2: Technology Topic
- **Input:** `{"topic": "Quantum Computing"}`
- **Expected:** Technical but accessible script with compute/tech keywords

### Test 3: Lifestyle Topic
- **Input:** `{"topic": "Morning Routines"}`
- **Expected:** Practical, conversational script with daily life keywords

---

## 📊 Success Criteria

- ✅ Script duration estimate: 60-90 seconds (±10s tolerance)
- ✅ Segments: 5-7 segments
- ✅ Keywords: 2-3 per segment
- ✅ JSON structure matches schema exactly
- ✅ Hook present in first segment
- ✅ CTA present in last segment

---

**Last Updated:** 2026-02-14  
**Self-Annealing Log:** None yet
