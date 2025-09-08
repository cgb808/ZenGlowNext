# Self-Improving Wellness Companion Pipeline — Supplemental Overview

Scope: This is a concise overview of a few specific enhancements (causal inference, personalization via chronotypes, RLHF feedback loop, and deployment accents). It does not replace or attempt to cover the full project architecture.

```
┌───────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                     Self-Improving Wellness Companion Pipeline (Final Architecture)                          │
├───────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                               │
│  ┌─────────────────┐       ┌─────────────────────┐       ┌─────────────────────────────────┐       ┌───────────┐  │
│  │   Wearable      │       │  Child's Mobile     │       │        Cloud Backend           │       │  Parent's │  │
│  │   Device        │──────►│    Device           │──────►│                                │──────►│  Mobile   │  │
│  │ (TinyLSTM)      │ BLE   │ (Interaction &      │ HTTP/ │ (Self-Improving Intelligence) │ MQTT  │ Device   │  │
│  │                 │       │  Aggregation)       │       │                                │       │ (Avatar)  │  │
│  └─────────┬───────┘       └─────────┬───────────┘       └─────────────┬───────────────────┘       └───┬────┘  │
│            │                         │                                   │                          │       │
│  ┌─────────▼───────┐       ┌─────────▼───────────┐       ┌─────────────▼───────────────────┐       ┌───▼────┐  │
│  │ HR/EDA/Accel    │       │ TinyLSTM            │       │ TimescaleDB/InfluxDB          │       │ TinyLSTM │  │
│  │ Sensors         │──────►│ (Engagement +       │──────►│ (Time-Series: Wellness +      │──────►│ (Alerts) │  │
│  │ + Sleep         │       │  Sleep Classifier)  │       │  Sleep + School Events)       │       │          │  │
│  └─────────┬───────┘       └─────────┬───────────┘       │                              │       │ (enhanced)│  │
│            │               │        │                 │  ┌─────────────────────────┐  │       │ ZenMoon-  │  │
│  ┌─────────▼───────┐       │  ┌──────▼───────┐     │       │  │ BGE-Large Embedding     │  │       │ Avitar    │  │
│  │ TinyLSTM        │       │  │ Aggregator   │     │       │  │ (Vector DB: Weaviate) │  │       │          │  │
│  │ (Smoothing +    │──────►│  │ (Context +    │     │       │  └─────────┬─────────────┘  │       │          │  │
│  │  Anomaly Detect)│       │  │  Sleep/School│     │       │            │                │       │          │  │
│  └─────────┬───────┘       │  │  Events)      │     │       │  ┌─────────▼─────────────┐  │       │          │  │
│            │               │  └──────┬───────┘     │       │  │ Darts (Forecasting:   │  │       │          │  │
│  ┌─────────▼───────┐       │         │             │       │  │  Sleep + Stress)      │  │       │          │  │
│  │ BLE Packet      │       │  ┌──────▼───────┐     │       │  └─────────┬───────────┘  │       │          │  │
│  │ (JSON)          │──────►│  │ HTTP/MQTT    │     │       │            │              │       │          │  │
│  └─────────────────┘       │  │ Payload      │     │       │  ┌─────────▼───────────┐  │       │          │  │
│                            │  └─────────────┘     │──────►│  │ Causal Inference     │  │       │          │  │
│                            │                    │       │  │ (DoWhy/CausalML)     │  │       │          │  │
│                            │                    │       │  └─────────┬───────────┘  │       │          │  │
│                            │                    │       │            │              │       │          │  │
│                            │                    │       │  ┌─────────▼───────────┐  │       │          │  │
│                            │                    │       │  │ Personalization      │  │       │          │  │
│                            │                    │       │  │ (Chronotype Engine)  │  │       │          │  │
│                            │                    │       │  └─────────┬───────────┘  │       │          │  │
│                            │                    │       │            │              │       │          │  │
│                            │                    │       │  ┌─────────▼───────────┐  │       │          │  │
│                            │                    │       │  │ Gemma/Phi-3 + RLHF   │  │──────►│          │  │
│                            │                    │       │  │ (Insight Generator) │  │       │          │  │
│                            │                    │       │  └────────────────────┘  │       │          │  │
│                            │                    │       │                         │       │          │  │
│                            │                    │       │  ┌─────────────────────┐  │       │          │  │
│                            │                    │       │  │ Feedback Loop        │◄───────┘          │  │
│                            │                    │       │  │ (Parent Feedback)    │  │                 │  │
│                            │                    │       │  └─────────────────────┘  │                 │  │
│                            │                    │       │                                │                 │  │
│                            └────────────────────┘       └─────────────────────────────────┘                 │  │
│                                                                                                       │  │
│  ┌───────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                       │  │
│  ┌───────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                            Parent Feedback Loop (RLHF)                              │  │
│  └───────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                       │  │
└───────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## 1) Cloud Backend: Self-Improving Intelligence Core

New Components

- Causal Inference Engine — Identify causal relationships (e.g., "mindfulness → stress reduction"). Tools: DoWhy, CausalML
- Personalization Engine — Learn child-specific traits (e.g., chronotype, stress triggers). Tools: scikit-learn, PyTorch
- RLHF Fine-Tuning Loop — Improve Gemma/Phi-3 using parent feedback (👍/👎). Tools: Transformers, PEFT
- Vector DB (Weaviate) — Store contextual embeddings (BGE-Large)
- Time-Series DB — Store raw metrics + school events (TimescaleDB/InfluxDB)

### A. Causal Inference Engine

Purpose: Move beyond correlation to causation using DoWhy/CausalML.

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

### B. Personalization Engine (Chronotype Detection)

Purpose: Detect early bird vs. night owl and tailor timing of interventions.

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

### C. RLHF Fine-Tuning Loop

Purpose: Use parent feedback (👍/👎) to continuously improve Gemma/Phi-3.

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

### D. Enhanced Prompt With Personalization

Combine forecast, chronotype, and causal insights.

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

## 2) Parent’s Mobile Device: Feedback Loop (iOS Example)

New Features

- Feedback buttons (👍/👎) next to each recommendation
- Real-time updates via WebSocket
- Avatar expressions for chronotype cues

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

## 3) Data Flow With Feedback Loop

1. Wearable → Child’s Mobile → Cloud (as before)
2. Cloud → Parent’s Mobile: Recommendation + Forecast
3. Parent’s Mobile → Cloud: Feedback (👍/👎)
   - Feedback stored in `recommendation_feedback` table
   - Triggers RLHF fine-tuning every 10 feedback items
4. Cloud updates causal/personalization insights and generates improved future recommendations

## 4) Database Schema Updates

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

## 5) Deployment Architecture Accents

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                                                                               │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐    ┌─────────────┐   │
│   │  Flask App  │    │ TimescaleDB │    │    Weaviate     │    │  Gemma/Phi-3 │   │
│   │ (Gunicorn)  │    │ (Time-Series)│   │  (Vector DB)    │    │ (RLHF Model) │   │
│   └─────────────┘    └─────────────┘    └─────────────────┘    └─────────────┘   │
│       │                    │                    │                    │           │
│       └────────────────────┘                    └────────────────────┘           │
│               │                                            │                     │
│               ▼                                            ▼                     │
│   ┌─────────────────────┐                      ┌─────────────────────┐           │
│   │   Redis (Caching)   │                      │   Celery (Tasks)    │           │
│   │ - Forecast cache    │                      │ - RLHF fine-tuning  │           │
│   │ - Rate limiting     │                      │ - Causal analysis   │           │
│   └─────────────────────┘                      └─────────────────────┘           │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 6) Example End-to-End Flow (Night Owl)

- Wearable detects high stress during a math test (0.75)
- Child’s Mobile adds context (event: math_test, sleep_duration: 6h)
- Cloud:
  - Darts predicts stress peak at 0.85 tomorrow
  - Causal engine notes "mindfulness reduces stress by 15%"
  - Personalization identifies night_owl
  - Gemma/Phi-3 outputs a personalized recommendation

## 7) Key Enhancements Summary

- Recommendations: Personalized, causal, and RLHF-fine-tuned
- Data Analysis: Moves from descriptive to causal
- Personalization: Chronotype + intervention preferences
- Feedback Loop: Parent feedback drives model improvement
- Avatar: Dynamic (chronotype + stress/sleep cues)

## 8) Tools & Libraries

- Causal Inference: DoWhy, CausalML
- Personalization: scikit-learn, PyTorch
- RLHF: Transformers, PEFT, TRLX
- Vector DB: Weaviate, BGE-Large (FlagEmbedding)
- Time-Series DB: TimescaleDB, InfluxDB
- Real-Time: Flask-SocketIO, WebSocket
- Tasks: Celery, Redis
- Deployment: Docker, Gunicorn, Nginx

## 9) Final Recommendations

- Start with feedback loop (👍/👎) and RLHF fine-tuning
- Add causal inference (effect of interventions)
- Personalize with chronotypes
- Optimize: Redis cache forecasts; run causal/personalization in Celery
- Monitor: Track accuracy; A/B test base vs. RLHF models

## 10) Example: A/B Testing (Sketch)

```python
@app.route('/api/recommendation/<child_id>')
def get_recommendation(child_id):
    # 50% chance to use the new RLHF-finetuned model
    use_new_model = random.random() < 0.5

    model_path = f"./gemma_rlhf_{child_id}" if use_new_model else "google/gemma-7b-it"

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
