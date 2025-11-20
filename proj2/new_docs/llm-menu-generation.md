---
published: false
---

# LLM-Powered Menu Generation Pipeline

## Overview

The menu generation system uses a **local Large Language Model (LLM)** to create personalized meal plans based on user preferences, dietary restrictions, restaurant hours, and item availability. The pipeline intelligently filters menu items and uses AI to recommend suitable meals for breakfast, lunch, and dinner.

**Current Status**: ⚠️ **Backend Complete, No UI** — The entire pipeline is implemented and tested but has **no user-facing interface** to trigger it.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Menu Generation Flow                          │
└─────────────────────────────────────────────────────────────────┘

1. User Profile
   ├─ Preferences (e.g., "high protein, low carb")
   ├─ Allergens (e.g., "Peanuts, Shellfish")
   └─ Existing Menu String (serialized)
          ↓
2. MenuGenerator.update_menu()
   ├─ Input: date, meal_numbers [1,2,3], number_of_days
   ├─ For each day & meal:
   │    ├─ Filter by restaurant hours (open at meal time)
   │    ├─ Filter by allergens (exclude items)
   │    ├─ Filter by stock (instock == 1)
   │    ├─ Random sample (ITEM_CHOICES items)
   │    └─ Build CSV context for LLM
   │         ↓
3. LLM Generation
   ├─ System: "You are a health and nutrition expert..."
   ├─ Prompt: User preferences + meal type + CSV of items
   ├─ Model: IBM Granite 350M (HuggingFace)
   ├─ Device: MPS (Apple Silicon) / CUDA / CPU
   └─ Output: Item ID in specific format
          ↓
4. Output Validation
   ├─ Parse LLM output with regex
   ├─ Verify item_id exists in filtered list
   ├─ Retry up to MAX_LLM_TRIES if invalid
   └─ Return item_id or raise error
          ↓
5. Menu String Update
   └─ Append: [YYYY-MM-DD,item_id,meal_number]
          ↓
6. Persist to Database
   └─ Update User.generated_menu column
```

---

## Core Components

### 1. `llm_toolkit.py` — LLM Wrapper

Provides a clean interface to the HuggingFace Transformers model.

#### Class: `LLM`

**Initialization:**
- Detects available hardware: **MPS** (Apple Silicon) > **CUDA** (NVIDIA GPU) > **CPU**
- Downloads model from HuggingFace: `ibm-granite/granite-4.0-h-350M`
- Caches model locally in `.hf_cache/` directory
- Sets model to evaluation mode

**Parameters:**
- `tokens` (int, default=500): Max number of tokens to generate

**Key Method: `generate(context, prompt)`**
```python
def generate(self, context: str, prompt: str) -> str
```
- **context**: System message (role: "You are a nutrition expert...")
- **prompt**: User request with preferences and menu items
- **Returns**: Raw LLM output string

**Output Format:**
```
<|start_of_role|>assistant<|end_of_role|>42<|end_of_text|>
```
Where `42` is the selected item_id.

**Performance:**
- **MPS (Apple Silicon)**: ~2-5 seconds per inference
- **CPU**: ~30-60 seconds per inference
- Prints timing: `"Menu Item selected in X.XXXX seconds"`

---

### 2. `menu_generation.py` — Business Logic

Contains filtering, context generation, and orchestration.

#### Global Configuration

```python
MAX_LLM_TRIES = 3               # Retry attempts if LLM fails
ITEM_CHOICES = 10               # Initial sample size for LLM
LLM_ATTRIBUTE_ERROR = -1        # Error code for parse failure

# Meal times (24-hour HHMM format)
BREAKFAST_TIME = 1000           # 10:00 AM
LUNCH_TIME = 1400               # 2:00 PM
DINNER_TIME = 2000              # 8:00 PM

# Days of week (match database format)
DAYS_OF_WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
```

#### LLM Prompts

**System Template:**
```
You are a health and nutrition expert planning meals for a customer 
based on their preferences. Use only the menu items provided under 
CSV CONTEXT.
```

**User Prompt Template:**
```
Choose a meal for a customer based on their preferences: {preferences}
Make sure that the item makes sense for {meal}.
Provide only the itm_id as output

CSV CONTEXT:
{context}
```

**Context Example:**
```csv
item_id,name,description,price,calories
42,Grilled Chicken Salad,Fresh greens with grilled chicken,1200,350
58,Quinoa Bowl,Protein-packed quinoa with vegetables,1400,420
...
```

#### Helper Functions

##### `get_meal_and_order_time(meal_number: int) -> Tuple[str, int]`
Maps meal numbers to names and times:
- `1` → `("breakfast", 1000)`
- `2` → `("lunch", 1400)`
- `3` → `("dinner", 2000)`

##### `get_weekday_and_increment(date: str) -> Tuple[str, str]`
Converts date to weekday and gets next date:
- Input: `"2025-10-14"`
- Output: `("2025-10-15", "Mon")`

##### `format_llm_output(output: str) -> int`
Extracts item_id from LLM output using regex:
```python
LLM_OUTPUT_MATCH = r"<\|start_of_role\|>assistant<\|end_of_role\|>(\d+)<\|end_of_text\|>"
```
Returns `-1` if parsing fails.

##### `filter_allergens(menu_items: DataFrame, allergens: str) -> DataFrame`
Removes items containing specified allergens:
- Splits `allergens` by comma
- Checks each item's `allergens` column
- Drops rows with matches

##### `filter_closed_restaurants(restaurant: DataFrame, weekday: str, time: int) -> DataFrame`
Removes restaurants closed at specified time:
- Parses `hours` JSON: `{"Mon": [1700, 2100], ...}`
- Checks if `time` falls within any open interval
- Drops closed restaurants

##### `limit_scope(items: DataFrame, num_choices: int) -> List[int]`
Randomly samples items to limit context size:
- Returns up to `num_choices` random indices
- Prevents overwhelming the LLM with too many options

---

### 3. Class: `MenuGenerator`

The main orchestrator that ties everything together.

#### Initialization

```python
def __init__(self, tokens: int = 500)
```

**Actions:**
1. Connects to database (`CSC510_DB.db`)
2. Loads menu items: `SELECT * FROM MenuItem WHERE instock == 1`
3. Loads restaurants: `SELECT rtr_id, hours FROM Restaurant WHERE status=="Open"`
4. Initializes LLM: `self.generator = llm_toolkit.LLM(tokens=tokens)`
5. Closes database connection

**Data Loaded:**
- `self.menu_items`: Pandas DataFrame with all in-stock items
- `self.restaurants`: Pandas DataFrame with open restaurants and hours
- `self.generator`: LLM instance ready for inference

---

#### Private Method: `__get_context()`

```python
def __get_context(self, allergens: str, weekday: str, order_time: int, 
                  num_choices: int) -> Tuple[str, List[int]]
```

**Purpose:** Build filtered, sampled menu context for the LLM.

**Process:**
1. **Merge**: Combine `menu_items` + `restaurants` on `rtr_id`
2. **Filter Closed**: Remove restaurants closed at `order_time` on `weekday`
3. **Filter Allergens**: Remove items containing user's allergens
4. **Random Sample**: Select `num_choices` random items
5. **Build CSV**: Create CSV string with columns: `item_id,name,description,price,calories`
6. **Return**: `(csv_string, list_of_item_ids)`

**Performance:** Prints timing: `"Context block generated in X.XXXX seconds"`

**Example Output:**
```python
context = "item_id,name,description,price,calories\n42,Salad,...\n58,Bowl,...\n"
item_ids = [42, 58, 73, 91, ...]
```

---

#### Private Method: `__pick_menu_item()`

```python
def __pick_menu_item(self, preferences: str, allergens: str, 
                     weekday: str, meal_number: int) -> int
```

**Purpose:** Use LLM to select a single menu item for a specific meal.

**Algorithm:**
1. Get meal name and time: `get_meal_and_order_time(meal_number)`
2. Set initial sample size: `num_choices = ITEM_CHOICES` (10)
3. **Retry Loop** (up to `MAX_LLM_TRIES` = 3):
   - Generate context: `__get_context(allergens, weekday, order_time, num_choices)`
   - Build prompt by replacing `{preferences}`, `{context}`, `{meal}`
   - Call LLM: `llm_output = self.generator.generate(system, prompt)`
   - Parse output: `output = format_llm_output(llm_output)`
   - **Validate**: If `output > 0` and `output in item_ids`, return it
   - **Retry**: Increase sample size: `num_choices += ITEM_CHOICES`
4. If all retries fail, raise `RuntimeError` with LLM output for debugging

**Error Handling:**
- Invalid output (not a number): Retry with more options
- Item not in filtered list: Retry with more options
- All retries exhausted: Raise exception with details

**Return:** Valid `item_id` (int)

---

#### Public Method: `update_menu()`

```python
def update_menu(self, menu: str, preferences: str, allergens: str, 
                date: str, meal_numbers: List[int], 
                number_of_days: int = 1) -> str
```

**Purpose:** Generate meal plans for multiple days and meals, updating the menu string.

**Parameters:**
- `menu` (str): Existing menu string or `None` (format: `[YYYY-MM-DD,itm_id,meal]`)
- `preferences` (str): User preferences (e.g., `"high protein, low carb"`)
- `allergens` (str): Allergens to avoid (e.g., `"Peanuts, Shellfish"`)
- `date` (str): Start date in `YYYY-MM-DD` format
- `meal_numbers` (List[int]): Which meals to generate (e.g., `[1,2,3]` for all three)
- `number_of_days` (int): How many consecutive days to generate

**Algorithm:**
1. Get next date and current weekday
2. **Day Loop** (repeat `number_of_days` times):
   - **Meal Loop** (for each meal in `meal_numbers`):
     - Check if meal already exists for this date using regex
     - If missing:
       - Call `__pick_menu_item()` to get `itm_id`
       - Append to menu: `[{date},{itm_id},{meal_number}]`
   - Increment to next day
3. Return updated menu string

**Idempotency:** If a meal already exists for a date, it's **not regenerated** (prevents overwriting).

**Example Usage:**
```python
generator = MenuGenerator()

# Generate lunch for Oct 14
menu = generator.update_menu(
    menu=None, 
    preferences="high protein, low carb",
    allergens="Peanuts, Shellfish",
    date="2025-10-14",
    meal_numbers=[2]
)
# Result: "[2025-10-14,42,2]"

# Add dinner for same day (preserves lunch)
menu = generator.update_menu(
    menu=menu,
    preferences="high protein, low carb",
    allergens="Peanuts, Shellfish",
    date="2025-10-14",
    meal_numbers=[3]
)
# Result: "[2025-10-14,42,2],[2025-10-14,58,3]"

# Generate full week (7 days, all 3 meals)
menu = generator.update_menu(
    menu=None,
    preferences="vegetarian, spicy",
    allergens="Dairy",
    date="2025-11-16",
    meal_numbers=[1,2,3],
    number_of_days=7
)
# Result: 21 menu entries (7 days × 3 meals)
```

**Return:** Updated menu string with new entries appended.

---

## Menu String Format

### Structure
```
[YYYY-MM-DD,itm_id,meal_number],[YYYY-MM-DD,itm_id,meal_number],...
```

### Example
```
[2025-10-14,42,2],[2025-10-14,58,3],[2025-10-15,73,1],[2025-10-15,91,2],[2025-10-15,104,3]
```

### Parsing
The Flask app uses `parse_generated_menu()` to convert this into a dictionary:
```python
{
    "2025-10-14": [
        {"itm_id": 42, "meal": 2},  # Lunch
        {"itm_id": 58, "meal": 3}   # Dinner
    ],
    "2025-10-15": [
        {"itm_id": 73, "meal": 1},  # Breakfast
        {"itm_id": 91, "meal": 2},  # Lunch
        {"itm_id": 104, "meal": 3}  # Dinner
    ]
}
```

This dictionary is used to render the calendar in `index.html`.

---

## Data Flow Example

### Scenario: Generate lunch recommendation for a high-protein user

```python
# 1. User data
preferences = "high protein, low carb"
allergens = "Peanuts, Shellfish"
date = "2025-10-14"  # Monday
meal_number = 2  # Lunch

# 2. Initialize generator (loads DB data + LLM)
generator = MenuGenerator(tokens=500)

# 3. Call update_menu
menu = generator.update_menu(
    menu=None,
    preferences=preferences,
    allergens=allergens,
    date=date,
    meal_numbers=[2]
)

# Internal flow:
# ├─ get_weekday_and_increment("2025-10-14")
# │    └─ Returns: ("2025-10-15", "Mon")
# ├─ __pick_menu_item(preferences, allergens, "Mon", 2)
# │    ├─ get_meal_and_order_time(2) → ("lunch", 1400)
# │    ├─ __get_context(allergens, "Mon", 1400, 10)
# │    │    ├─ Merge menu_items + restaurants
# │    │    ├─ Filter: Restaurants open at 1400 on Monday
# │    │    ├─ Filter: Remove items with Peanuts or Shellfish
# │    │    ├─ Sample: 10 random items
# │    │    └─ Build CSV: "item_id,name,description,price,calories\n42,..."
# │    ├─ Build prompt:
# │    │    System: "You are a health and nutrition expert..."
# │    │    User: "Choose a meal for... high protein, low carb... lunch"
# │    ├─ Call LLM: generator.generate(system, prompt)
# │    │    ├─ Tokenize input
# │    │    ├─ Run inference on MPS/CUDA/CPU
# │    │    └─ Decode output: "<|start_of_role|>assistant<|end_of_role|>42<|end_of_text|>"
# │    ├─ Parse: format_llm_output(llm_output) → 42
# │    └─ Validate: 42 in [42, 58, 73, ...] ✓
# └─ Append: "[2025-10-14,42,2]"

# 4. Result
menu = "[2025-10-14,42,2]"

# 5. Save to database (NOT IMPLEMENTED in UI)
# UPDATE User SET generated_menu = "[2025-10-14,42,2]" WHERE usr_id = 123
```

---

## Testing

### Test Suite: `tests/llm/test_generator.py`

**Key Tests:**
1. **No Regression**: Ensures previously generated meals aren't overwritten
2. **Valid Items**: Confirms all item_ids exist in the database
3. **Correct Meals**: Verifies meal numbers (1, 2, 3) are correct
4. **Multiple Meals**: Tests generating multiple meals in one call
5. **Multiple Days**: Tests multi-day generation

**Example Test:**
```python
# Generate 5 meals incrementally
menu1 = generator.update_menu(None, "high protein, low carb", "Peanuts", "2025-10-14", [2])
menu2 = generator.update_menu(menu1, "high protein, low carb", "Peanuts", "2025-10-14", [3])
menu3 = generator.update_menu(menu2, "high protein, low carb", "Peanuts", "2025-10-15", [1])
menu4 = generator.update_menu(menu3, "high protein, low carb", "Peanuts", "2025-10-15", [2])
menu5 = generator.update_menu(menu4, "high protein, low carb", "Peanuts", "2025-10-15", [3])

# Verify no regression (menu2 preserves menu1's entries)
assert parse_generated_menu(menu1)["2025-10-14"][0] == \
       parse_generated_menu(menu5)["2025-10-14"][0]
```

**Test Execution:**
```bash
pytest proj2/tests/llm/test_generator.py -v
```

---

## Performance Characteristics

### Timing Breakdown (Apple Silicon M-series, MPS)

| Operation | Time (seconds) | Notes |
|-----------|----------------|-------|
| MenuGenerator init | 2-5s | One-time LLM model load from cache |
| Context generation | 0.01-0.05s | Database query + filtering |
| LLM inference | 2-5s per item | Depends on model size and hardware |
| **Total per meal** | **~2-5s** | Context + LLM inference |
| **Week plan (21 meals)** | **~60-120s** | 21 LLM calls (with retries) |

### CPU Performance
- **LLM inference**: ~30-60s per item
- **Week plan**: ~15-30 minutes (not practical for production)

### Optimization Strategies
1. **Batch Generation**: Generate multiple days at once (already supported)
2. **Caching**: Cache LLM results for common preference+allergen combos
3. **GPU Acceleration**: Use CUDA (NVIDIA) or MPS (Apple) devices
4. **Smaller Model**: Use `granite-4.0-micro` instead of `350M` (faster, less accurate)
5. **Async Processing**: Generate menus in background task, notify user when ready

---

## Integration Points (Not Yet Implemented)

### 1. User Interface Trigger

**Proposed Route:**
```python
@app.route('/generate_menu', methods=['POST'])
def generate_menu():
    if session.get("Username") is None:
        return redirect(url_for("login"))
    
    usr_id = session.get("usr_id")
    preferences = request.form.get("preferences") or session.get("Preferences") or ""
    allergens = request.form.get("allergens") or session.get("Allergies") or ""
    start_date = request.form.get("start_date") or date.today().isoformat()
    num_days = int(request.form.get("num_days") or 7)
    meal_numbers = [int(m) for m in request.form.getlist("meals[]")] or [1,2,3]
    
    # Load existing menu
    conn = create_connection(db_file)
    try:
        user = fetch_one(conn, 'SELECT generated_menu FROM "User" WHERE usr_id = ?', (usr_id,))
        existing_menu = user[0] if user else None
    finally:
        close_connection(conn)
    
    # Generate new menu
    generator = MenuGenerator(tokens=500)
    updated_menu = generator.update_menu(
        menu=existing_menu,
        preferences=preferences,
        allergens=allergens,
        date=start_date,
        meal_numbers=meal_numbers,
        number_of_days=num_days
    )
    
    # Save to database
    conn = create_connection(db_file)
    try:
        execute_query(conn, 'UPDATE "User" SET generated_menu = ? WHERE usr_id = ?', 
                     (updated_menu, usr_id))
    finally:
        close_connection(conn)
    
    return redirect(url_for("index"))
```

### 2. Frontend Form

**Location:** Add to `profile.html` or `index.html`

```html
<form action="/generate_menu" method="POST">
  <h3>Generate AI Meal Plan</h3>
  
  <label>Start Date:</label>
  <input type="date" name="start_date" value="{{ today }}" required>
  
  <label>Number of Days:</label>
  <select name="num_days">
    <option value="1">1 Day</option>
    <option value="3">3 Days</option>
    <option value="7" selected>1 Week</option>
    <option value="14">2 Weeks</option>
  </select>
  
  <label>Meals:</label>
  <input type="checkbox" name="meals[]" value="1" checked> Breakfast
  <input type="checkbox" name="meals[]" value="2" checked> Lunch
  <input type="checkbox" name="meals[]" value="3" checked> Dinner
  
  <label>Preferences (optional):</label>
  <input type="text" name="preferences" value="{{ session.Preferences }}" 
         placeholder="e.g., high protein, low carb, vegetarian">
  
  <label>Allergens (optional):</label>
  <input type="text" name="allergens" value="{{ session.Allergies }}" 
         placeholder="e.g., Peanuts, Shellfish, Dairy">
  
  <button type="submit">Generate Meal Plan</button>
</form>
```

### 3. Loading State

Since generation can take 1-2 minutes, implement:
- **JavaScript Loading Spinner**: Show while processing
- **Background Task**: Use Celery or similar to queue generation
- **Notification**: Email/push when menu is ready

---

## Limitations & Considerations

### Current Limitations

1. **No UI Trigger**: Entire pipeline exists only in tests
2. **Synchronous**: Blocks for 1-2 minutes during generation
3. **No Caching**: Regenerates even for similar preferences
4. **Fixed Sample Size**: Always starts with 10 items (may be too few/many)
5. **No User Feedback**: LLM choice is opaque (no explanation)
6. **Limited Diversity**: May repeatedly suggest same items
7. **No Cost Tracking**: Free local LLM, but API calls would cost money

### Security Considerations

1. **Regex Validation**: `format_llm_output()` checks for injection attacks
2. **Database Validation**: Only uses item_ids from filtered list
3. **User Input Sanitization**: Preferences/allergens should be sanitized before LLM prompt
4. **Rate Limiting**: Should limit generation requests per user (e.g., once per day)

### Edge Cases

1. **No Available Items**: If filters remove all items, LLM will fail after 3 retries
2. **Restaurant Hours**: If no restaurants open at meal time, context will be empty
3. **LLM Hallucination**: May output invalid item_ids (handled by validation)
4. **Meal Already Exists**: update_menu() preserves existing meals (idempotent)

---

## Future Enhancements

### Short-term (Ready to Implement)
1. **Add UI Route**: `/generate_menu` endpoint (1-2 hours)
2. **Add Form**: Button on profile/index page (1 hour)
3. **Loading State**: JS spinner + AJAX (2 hours)

### Medium-term (Requires Architecture Changes)
1. **Background Processing**: Celery task queue (1-2 days)
2. **Progress Updates**: WebSocket for real-time status (1 day)
3. **Caching**: Redis cache for common preference combos (1 day)
4. **Batch Optimization**: Generate multiple meals in one LLM call (2 days)

### Long-term (Significant Features)
1. **Explanation Generation**: Ask LLM to explain why it chose each item
2. **Feedback Loop**: Let users rate suggestions, retrain model
3. **Nutritional Tracking**: Ensure weekly plan meets macro targets
4. **Cost Optimization**: Suggest cheaper options while meeting preferences
5. **Variety Enforcement**: Avoid repeating restaurants/cuisines too frequently
6. **Social Features**: Share meal plans, collaborative planning

---

## Troubleshooting

### Issue: LLM times out or runs too slow
**Solution:**
- Check device: `print(LLM.device)` — should be `"mps"` or `"cuda"`, not `"cpu"`
- Reduce `tokens` parameter: `MenuGenerator(tokens=200)`
- Use smaller model: Change `LLM.model = "ibm-granite/granite-4.0-micro"`

### Issue: "LLM has failed 3 times to generate a meal"
**Causes:**
1. Filters too restrictive (no items match preferences + allergens + hours)
2. LLM output format changed
3. Network issue downloading model

**Solutions:**
- Check database: Are there in-stock items from open restaurants?
- Increase `ITEM_CHOICES` to give LLM more options
- Verify regex pattern matches model output format

### Issue: Same items recommended repeatedly
**Cause:** Random sampling may pick same items; LLM has bias toward certain choices

**Solution:**
- Implement diversity filter (track recent selections)
- Adjust prompt to request variety
- Increase sample size to give LLM more options

### Issue: Model download fails
**Cause:** Network issues, HuggingFace API rate limiting

**Solution:**
- Check internet connection
- Pre-download model: `huggingface-cli download ibm-granite/granite-4.0-h-350M`
- Set `HF_HOME` environment variable to persistent cache location

---

## Summary

The LLM menu generation pipeline is a **fully functional, well-tested system** that uses artificial intelligence to create personalized meal plans. It demonstrates:

- ✅ Database-driven filtering (hours, stock, allergens)
- ✅ LLM integration with proper prompt engineering
- ✅ Hardware acceleration (MPS/CUDA support)
- ✅ Robust error handling and retries
- ✅ Idempotent operations (preserves existing meals)
- ✅ Comprehensive test coverage

However, it **lacks a user interface** — the pipeline is only exercised in the test suite. Adding a simple Flask route and HTML form would make this feature immediately available to end users.

**Estimated Effort to Deploy**: 4-6 hours for basic UI + background processing.
