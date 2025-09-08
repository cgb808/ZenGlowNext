## Causal Inference Engine

**Purpose:**

Move beyond correlation (e.g., "stress rises before tests") to causation (e.g., "mindfulness reduces stress by 15%").
Uses DoWhy or CausalML to analyze intervention outcomes.

**Code Snippet:**
```python
from dowhy import CausalModel
import pandas as pd

def analyze_causal_effect(child_id):
    # Load historical data: interventions + outcomes
    df = pd.read_sql(f"""
        SELECT
            w.time,
            w.stress_level,
            w.sleep_duration,
            s.event_type AS intervention,
            s.event_time
        FROM wellness_metrics w
        LEFT JOIN school_events s ON
            w.child_id = s.child_id AND
            date_trunc('day', w.time) = date_trunc('day', s.event_time)
        WHERE w.child_id = '{child_id}'
        ORDER BY w.time
    """, db.engine)

    # Define causal model: Did mindfulness reduce stress?
    model = CausalModel(
        data=df,
        treatment='intervention',
        outcome='stress_level',
        common_causes=['sleep_duration', 'time']
    )
    identified_estimand = model.identify_effect()
    estimate = model.estimate_effect(identified_estimand, method_name="backdoor.propensity_score_stratification")
    return estimate.value  # e.g., -0.15 (15% reduction)

# Example usage in Flask
@app.route('/api/causal_insights/<child_id>')
def get_causal_insights(child_id):
    effect = analyze_causal_effect(child_id)
    return jsonify({
        "child_id": child_id,
        "causal_effect": effect,
        "interpretation": f"Interventions reduce stress by {abs(effect)*100:.1f}%"
    })
```

## B. Personalization Engine (Chronotype Detection)

**Purpose:**

Analyze sleep patterns to classify the child as:

*   Early bird (wakes up early, peak energy in morning).
*   Night owl (peak energy in evening).
*   Intermediate (balanced).

Tailor recommendations (e.g., "schedule homework in the evening for night owls").

**Code Snippet:**
```python
from sklearn.cluster import KMeans
import numpy as np

def detect_chronotype(child_id):
    # Load sleep data
    sleep_data = pd.read_sql(f"""
        SELECT
            EXTRACT(HOUR FROM time) AS hour,
            sleep_duration,
            sleep_state
        FROM wellness_metrics
        WHERE child_id = '{child_id}'
        ORDER BY time
    """, db.engine)

    # Cluster sleep/wake times
    X = sleep_data[['hour', 'sleep_duration']].values
    kmeans = KMeans(n_clusters=3).fit(X)
    sleep_data['cluster'] = kmeans.labels_

    # Determine chronotype
    avg_hour = sleep_data.groupby('cluster')['hour'].mean()
    if avg_hour.idxmin() == 0:
        return "early_bird"
    elif avg_hour.idxmax() == 1:
        return "night_owl"
    else:
        return "intermediate"

# Store in child profile
@app.route('/api/update_chronotype/<child_id>')
def update_chronotype(child_id):
    chronotype = detect_chronotype(child_id)
    child = Child.query.get(child_id)
    child.chronotype = chronotype
    db.session.commit()
    return jsonify({"chronotype": chronotype})
```

## C. RLHF Fine-Tuning Loop

**Purpose:**

Use parent feedback (👍/👎) to continuously improve the Gemma/Phi-3 model.
Implements Reinforcement Learning from Human Feedback (RLHF).

**Code Snippet:**
```python
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model
import torch

def fine_tune_with_feedback(child_id):
    # Load feedback data
    feedback = pd.read_sql(f"""
        SELECT
            r.recommendation_id,
            r.text AS recommendation,
            f.was_helpful,
            w.stress_level_before,
            w.stress_level_after
        FROM recommendations r
        JOIN feedback f ON r.id = f.recommendation_id
        JOIN wellness_metrics w ON r.child_id = w.child_id
        WHERE r.child_id = '{child_id}'
        ORDER BY f.timestamp DESC
        LIMIT 100  # Last 100 feedback items
    """, db.engine)

    # Create prompts for fine-tuning
    prompts = []
    for _, row in feedback.iterrows():
        effect = row['stress_level_before'] - row['stress_level_after']
        prompt = f"""
        Recommendation: {row['recommendation']}
        Effect on stress: {'reduced' if effect > 0 else 'increased'} by {abs(effect):.2f}.
        Parent feedback: {'👍' if row['was_helpful'] else '👎'}.
        Generate a better recommendation:
        """
        prompts.append(prompt)

    # Tokenize and fine-tune
    tokenizer = AutoTokenizer.from_pretrained("google/gemma-7b-it")
    model = AutoModelForCausalLM.from_pretrained("google/gemma-7b-it", torch_dtype=torch.float16)

    # Use LoRA for efficient fine-tuning
    lora_config = LoraConfig(
        r=8,
        lora_alpha=16,
        target_modules=["q_proj", "o_proj", "k_proj", "v_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )
    model = get_peft_model(model, lora_config)

    # Tokenize prompts
    inputs = tokenizer(prompts, return_tensors="pt", padding=True, truncation=True, max_length=512).to("cuda")

    # Fine-tune
    training_args = TrainingArguments(
        output_dir="./rlhf_finetune",
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        learning_rate=2e-5,
        num_train_epochs=3,
        save_steps=100,
        logging_steps=10
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=Dataset.from_dict(tokenizer(prompts, return_tensors="pt", padding=True, truncation=True))
    )
    trainer.train()

    # Save the fine-tuned model
    model.save_pretrained(f"./gemma_rlhf_{child_id}")
    return f"./gemma_rlhf_{child_id}"

# Trigger fine-tuning after feedback
@app.route('/api/feedback', methods=['POST'])
def handle_feedback():
    data = request.json
    feedback = RecommendationFeedback(
        recommendation_id=data['recommendation_id'],
        child_id=data['child_id'],
        was_helpful=data['was_helpful']
    )
    db.session.add(feedback)
    db.session.commit()

    # Trigger RLHF fine-tuning every 10 feedback items
    feedback_count = db.session.query(RecommendationFeedback).filter_by(child_id=data['child_id']).count()
    if feedback_count % 10 == 0:
        fine_tune_with_feedback(data['child_id'])

    return jsonify({"status": "feedback received"})
```

## D. Enhanced Gemma/Phi-3 Prompt with Personalization

**Purpose:**

Generate highly personalized recommendations using:

*   Child’s chronotype.
*   Causal insights (e.g., "mindfulness reduces stress by 15%").
*   Historical patterns (e.g., "stress spikes before tests").

**Code Snippet:**
```python
def generate_personalized_recommendation(child_id, forecast):
    # Load child profile and causal insights
    child = Child.query.get(child_id)
    causal_effect = analyze_causal_effect(child_id)
    chronotype = child.chronotype

    # Retrieve historical context from Weaviate
    context = retrieve_context_from_weaviate(child_id)

    # Generate prompt
    prompt = f"""
    Child Profile:
    - Age: {child.age}
    - Chronotype: {chronotype}
    - Baseline Stress: {child.baseline_stress}
    - Causal Insight: Interventions reduce stress by {abs(causal_effect)*100:.1f}%.

    Current Context:
    - Forecast: {forecast}
    - Historical Patterns: {context}

    Generate a 2-sentence recommendation.
    Tailor it for a '{chronotype}' and leverage the causal insight.
    If the child is a 'night_owl', suggest evening activities.
    If the child is an 'early_bird', suggest morning activities.
    """

    # Generate recommendation
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    outputs = model.generate(**inputs, max_new_tokens=120)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

# Example usage in Flask
@app.route('/api/recommendation/<child_id>')
def get_recommendation(child_id):
    forecast = forecast(child_id, hours=24)
    recommendation = generate_personalized_recommendation(child_id, forecast)
    return jsonify({
        "forecast": forecast,
        "recommendation": recommendation
    })
```

## 2. Parent’s Mobile Device: Feedback Loop

### New Features

*   **Feedback Buttons**👍/👎 buttons next to each recommendation.
*   **Real-Time Updates**WebSocket updates when new recommendations are generated.
*   **Avatar Expressions**Visual cues for chronotype (e.g., owl for night owls, sun for early birds).

**Code Snippet (Swift/iOS):**
```swift
// Send feedback to Flask backend
func sendFeedback(recommendationID: String, wasHelpful: Bool) {
    let feedbackData: [String: Any] = [
        "recommendation_id": recommendationID,
        "child_id": "child_123",
        "was_helpful": wasHelpful
    ]
    APIClient.shared.post(to: "/api/feedback", body: feedbackData) { response in
        print("Feedback sent:", response)
    }
}

// Update avatar based on chronotype
func updateAvatar(chronotype: String) {
    switch chronotype {
    case "early_bird":
        avatar.setTheme(to: .sun)
    case "night_owl":
        avatar.setTheme(to: .moon)
    default:
        avatar.setTheme(to: .neutral)
    }
}

// WebSocket for real-time updates
func connectWebSocket() {
    socket = WebSocket(url: URL(string: "wss://your-flask-app/api/alerts")!)
    socket.onMessage = { message in
        if let data = message.data(using: .utf8),
           let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            DispatchQueue.main.async {
                self.showAlert(message: json["message"] as? String ?? "")
            }
        }
    }
    socket.connect()
}
```

## 3. Data Flow with Feedback Loop

1.  Wearable → Child’s Mobile → Cloud (as before)
2.  Cloud → Parent’s Mobile: Recommendation + Forecast
3.  Parent’s Mobile → Cloud: Feedback (👍/👎)
    *   Feedback stored in `recommendation_feedback` table.
    *   Triggers RLHF fine-tuning every 10 feedback items.
4.  Cloud:
    *   Updates causal insights and personalization profiles.
    *   Generates improved recommendations for future queries.

## 4. Database Schema Updates

### New Tables for Feedback and Personalization

```sql
-- Feedback table
CREATE TABLE recommendation_feedback (
    id SERIAL PRIMARY KEY,
    recommendation_id INT REFERENCES recommendations(id),
    child_id VARCHAR(50) REFERENCES children(id),
    was_helpful BOOLEAN NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Personalization traits
ALTER TABLE children ADD COLUMN chronotype VARCHAR(20);
ALTER TABLE children ADD COLUMN preferred_interventions JSONB;
```

## 5. Deployment Architecture

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                                                                                   │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐    ┌─────────────┐   │
│   │  Flask App  │    │ TimescaleDB  │    │   Weaviate      │    │  Gemma/Phi-3 │   │
│   │ (Gunicorn)  │    │ (Time-Series)│    │  (Vector DB)    │    │ (RLHF Model) │   │
│   └─────────────┘    └─────────────┘    └─────────────────┘    └─────────────┘   │
│       │                    │                    │                    │       │
│       └────────────────────┘                    └────────────────────┘       │
│               │                                            │               │
│               ▼                                            ▼               │
│   ┌─────────────────────┐                      ┌─────────────────────┐   │
│   │   Redis (Caching)   │                      │   Celery (Tasks)    │   │
│   │ - Forecast cache    │                      │ - RLHF fine-tuning  │   │
│   │ - Rate limiting     │                      │ - Causal analysis   │   │
│   └─────────────────────┘                      └─────────────────────┘   │
│                                                                                   │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 6. Example: Full End-to-End Flow

*   Wearable detects high stress (stress_level: 0.75) during a math test.
*   Child’s Mobile adds context (event: math_test, sleep_duration: 6h).
*   Cloud:
    *   Darts predicts stress will peak at 0.85 tomorrow.
    *   Causal Inference Engine notes that "mindfulness reduces stress by 15%".
    *   Personalization Engine identifies the child as a night_owl.
    *   Gemma/Phi-3 generates:
        ```json
        {
          "forecast": {"stress": [0.75, 0.8, 0.85], "sleep": [6.0, 5.5, 5.0]},
          "recommendation": "Your child’s stress is rising ahead of tomorrow’s math test. "
                            "Since they’re a night owl, schedule a mindfulness exercise at 7 PM tonight "
                            "(historically reduces stress by 15%). Aim for bed by 9 PM to counter sleep disruption.",
          "causal_insight": "Mindfulness reduces stress by 15% for this child.",
          "personalization": {"chronotype": "night_owl", "preferred_time": "evening"}
        }
        ```


*   Parent’s Mobile:
    *   Shows recommendation + 👍/👎 buttons.
    *   Avatar displays a moon theme (night owl).


*   Parent provides feedback (👍) → Cloud triggers RLHF fine-tuning.


## 7. Key Enhancements Summary

| Feature | Before | After |
|---|---|---|
| Recommendations | Generic, correlation-based | Personalized, causal, RLHF-fine-tuned |
| Data Analysis | Descriptive (what happened?) | Causal (why did it happen?) |
| Personalization | None | Chronotype + intervention preferences |
| Feedback Loop | None | Parent feedback → model improvement |
| Avatar | Static expressions | Dynamic (chronotype + stress/sleep states) |

## 8. Tools and Libraries Summary

| Component | Tools/Libraries |
|---|---|
| Causal Inference | DoWhy, CausalML |
| Personalization | Scikit-learn, PyTorch |
| RLHF Fine-Tuning | Hugging Face Transformers, PEFT, TRLX |
| Vector DB | Weaviate, FlagEmbedding (BGE-Large) |
| Time-Series DB | TimescaleDB, InfluxDB |
| Real-Time Updates | Flask-SocketIO, WebSocket |
| Task Queue | Celery, Redis |
| Deployment | Docker, Gunicorn, Nginx |

## 9. Final Recommendations

**Start with the Feedback Loop:**

*   Implement 👍/👎 buttons and RLHF fine-tuning first (highest impact).


**Add Causal Inference:**

*   Use DoWhy to analyze interventions (e.g., "Does mindfulness work?").


**Personalize with Chronotypes:**

*   Cluster sleep data to detect early birds vs. night owls.


**Optimize Performance:**

*   Cache forecasts in Redis.
*   Run causal analysis and personalization as background tasks (Celery).


**Monitor and Iterate:**

*   Track recommendation accuracy over time.
*   Use A/B testing to compare old vs. new models.




## 10. Example: A/B Testing Recommendations

```python
@app.route('/api/recommendation/<child_id>')
def get_recommendation(child_id):
    # 50% chance to use the new RLHF-finetuned model
    use_new_model = random.random() < 0.5

    if use_new_model:
        model_path = f"./gemma_rlhf_{child_id}"
    else:
        model_path = "google/gemma-7b-it"

    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForCausalLM.from_pretrained(model_path, torch_dtype=torch.float16)

    # Generate recommendation (as before)
    recommendation = generate_personalized_recommendation(child_id, forecast, model, tokenizer)

    return jsonify({
        "recommendation": recommendation,
        "model_version": "rlhf" if use_new_model else "base",
        "forecast": forecast
    })
```