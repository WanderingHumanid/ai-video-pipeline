# Architecture SOP: Keyword Extraction

**Component:** Keyword Extraction (Layer 3 Tool)  
**Owner:** `tools/extract_keywords.py`  
**Purpose:** Extract visual search keywords from script segments for media sourcing

---

## 📋 Input Schema

```json
{
  "topic": "string",
  "segments": [
    {
      "text": "string (narration text)",
      "duration_estimate": "float",
      "keywords": ["string"] (optional, may be pre-extracted by LLM)
    }
  ]
}
```

---

## 📤 Output Schema

```json
{
  "keywords_by_segment": [
    {
      "segment_index": 0,
      "text": "string (segment narration)",
      "keywords": ["keyword1", "keyword2", "keyword3"],
      "primary_keyword": "keyword1 (most relevant)"
    }
  ],
  "all_keywords": ["unique", "keywords", "across", "all", "segments"]
}
```

---

## 🎯 Behavioral Rules

### 1. Keyword Quality
Keywords must be:
- **Concrete nouns:** Objects, places, people (NOT abstract concepts like "freedom")
- **Visual:** Things that can be filmed or photographed
- **Searchable:** Terms likely to return results on Pexels (common stock footage)

### 2. Keyword Count
- **Per Segment:** 2-3 keywords
- **Primary Keyword:** The most relevant/visual keyword per segment
- **Fallback Keywords:** Generic alternatives if primary fails on Pexels

### 3. Prioritization
Order keywords by:
1. **Visual specificity:** "astronaut" > "person"
2. **Search likelihood:** "ocean waves" > "water movement"
3. **Topic relevance:** Keywords central to the topic first

---

## ⚙️ Extraction Logic

### Option A: LLM Pre-Extracted (Preferred)
If the script JSON already contains `keywords` per segment:
1. Validate keywords (ensure they're concrete nouns)
2. Select `primary_keyword` (first in list)
3. Return as-is

### Option B: NLP-Based Extraction (Fallback)
If keywords are missing:
1. **Tokenize:** Split segment text into words
2. **POS Tagging:** Identify nouns using spaCy or NLTK
3. **Filter:**
   - Remove abstract nouns (use predefined list: "idea", "concept", "freedom")
   - Remove generic nouns (use predefined list: "thing", "stuff", "item")
   - Keep proper nouns (e.g., "Einstein", "Mars")
4. **Rank:** By frequency and relevance to topic
5. **Select:** Top 2-3 nouns per segment

### Option C: Hybrid (Best Accuracy)
1. Start with LLM keywords if available
2. Use NLP to extract additional candidates
3. Cross-validate: Ensure NLP keywords align with LLM keywords
4. Merge and deduplicate

---

## 🔄 Keyword Simplification (Pexels Fallback)

When Pexels returns no results for a keyword, apply this fallback chain:

### Step 1: Remove Adjectives
- **Original:** "black hole"
- **Simplified:** "hole" (or fallback to "space")

### Step 2: Use Category Generics
Map specific keywords to generic categories:
- **Science:** "space", "lab", "microscope"
- **Technology:** "computer", "chip", "robot"
- **Nature:** "forest", "ocean", "mountain"
- **Urban:** "city", "building", "traffic"

### Step 3: AI-Generated Fallback
If both fail:
- Use Antigravity's `generate_image` tool
- Prompt: "Generate a realistic image of [keyword]"
- Save to `.tmp/media/ai_generated_[index].png`

---

## ⚙️ Tool Implementation Logic

### Step 1: Input Validation
- Verify segment array is non-empty
- Check if keywords already exist in input

### Step 2: Keyword Extraction
- If keywords exist: Validate and format
- If keywords missing: Use NLP extraction (spaCy)

### Step 3: Primary Keyword Selection
For each segment:
- Rank keywords by visual specificity and frequency
- Select top keyword as `primary_keyword`

### Step 4: Deduplication
- Create `all_keywords` list (unique values across segments)
- Remove duplicates while preserving order

### Step 5: Output
- Save JSON to `.tmp/keywords.json`
- Return keywords object

---

## 🐛 Error Handling

### Error: No keywords extracted from segment
- **Action:** Use topic as fallback keyword
- **Example:** Topic = "Black Holes" → Keyword = "black hole"

### Error: All keywords are abstract
- **Action:** Use generic category fallback
- **Example:** "philosophy" → "books", "thinking person"

### Error: Keyword list is empty
- **Action:** Use universal fallback: "nature", "abstract", "technology"

---

## 🧪 Test Cases

### Test 1: Pre-Extracted Keywords
- **Input:** Segment with `keywords: ["ocean", "waves", "beach"]`
- **Expected:** Primary keyword = "ocean", no NLP processing needed

### Test 2: NLP Extraction
- **Input:** Segment = "The ocean waves crash on the sandy beach"
- **Expected:** Extracted keywords = ["ocean", "waves", "beach"]

### Test 3: Abstract Keyword Filtering
- **Input:** Segment = "Freedom is a powerful concept in philosophy"
- **Expected:** No direct keywords → Fallback = "books", "thinking"

---

## 📊 Success Criteria

- ✅ Every segment has 2-3 keywords
- ✅ Primary keyword is the most visual/specific
- ✅ No abstract nouns in final keyword list
- ✅ Keywords are searchable on Pexels (validated in Link phase)
- ✅ Fallback logic documented for edge cases

---

**Last Updated:** 2026-02-14  
**Self-Annealing Log:** None yet
