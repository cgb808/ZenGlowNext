# Recommendations System Overview

## Purpose
The ZenGlow Recommendations System provides structured wellness suggestions for the parent dashboard, helping parents support their children's wellbeing through data-driven insights and personalized recommendations.

## Current Implementation (Phase 1)

### Architecture
- **Rule-Based Engine**: Simple conditional logic to generate recommendations
- **Feature Flag Support**: `RECOMMENDATIONS_ENABLED` environment variable controls availability
- **Type-Safe**: Full TypeScript implementation with comprehensive interfaces
- **Extensible**: Designed for easy addition of new recommendation rules

### Core Components

#### 1. RecommendationService (`src/services/recommendations/recommendationService.ts`)
Main service that generates recommendations based on:
- **Recent Metrics**: Wellness score, mood averages, routine completion
- **Chronotype Information**: Early bird vs night owl preferences 
- **Engagement Signals**: Streaks, missed routines, activity patterns
- **Environmental Factors**: Screen time, contextual data

#### 2. Type Definitions (`types/recommendations.ts`)
Comprehensive interfaces for:
- `Recommendation`: Core recommendation structure
- `RecommendationContext`: Input context for generation
- `RecommendationGenerationOptions`: Filtering and customization options

#### 3. API Endpoint (`api-stubs/recommendations.ts`)
RESTful endpoint providing:
- GET `/api/recommendations?childId=<id>&userId=<userId>`
- Query parameter filtering (priority, type, max count)
- Consistent authentication patterns
- Feature flag integration

### Current Rules

1. **Wellness Score Rule**
   - Low score (<50) + downward trend → High priority mindfulness recommendation
   - Moderate score (<60) → Medium priority wellness support

2. **Chronotype Rule**
   - Night owl + low routine completion → Evening preparation suggestions
   - Early bird + low routine completion → Morning optimization recommendations

3. **Mood & Engagement Rule**
   - Neutral mood (4-6) + low engagement → Playful activity suggestions

4. **Screen Time Rule**
   - >2 hours daily → Medium priority device-free time recommendations
   - >3 hours daily → High priority screen time management

5. **Engagement Rule**
   - No streaks + multiple missed routines → High priority fresh start approach
   - Small streaks (1-3) → Low priority momentum building encouragement

### Feature Flag Integration

```typescript
import { isRecommendationsEnabled } from '../utils/SecurityConfig';

// Service automatically checks feature flag
if (!isRecommendationsEnabled()) {
  return []; // Empty recommendations when disabled
}
```

Environment variable: `RECOMMENDATIONS_ENABLED=true`

## Future Roadmap (Phases 2-4)

### Phase 2: Feedback Loop Integration (Issue #104)
- **Thumbs Up/Down Feedback**: Parent rating system for recommendation quality
- **Feedback Storage**: Database schema for recommendation effectiveness tracking
- **Adaptive Weighting**: Rule weights adjust based on feedback patterns
- **A/B Testing Infrastructure**: Compare recommendation strategies

### Phase 3: Hybrid ML Integration
- **Causal Inference**: DoWhy integration for intervention effectiveness analysis
- **Personalization Profiles**: Machine learning models for individual preferences
- **Context Enrichment**: Environmental and temporal pattern recognition
- **Ranking & Scoring**: ML-driven recommendation prioritization

### Phase 4: Advanced AI Features
- **RLHF (Reinforcement Learning from Human Feedback)**: Fine-tuned language models
- **Exploration/Exploitation**: Balance between proven and novel recommendations
- **Multi-Agent Systems**: Coordinated recommendation strategies
- **Real-Time Adaptation**: Dynamic context-aware generation

## Database Schema (Future)

```sql
-- Recommendation tracking
CREATE TABLE recommendations (
    id SERIAL PRIMARY KEY,
    child_id VARCHAR(50) REFERENCES children(id),
    type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    priority VARCHAR(20) NOT NULL,
    tags JSONB,
    source_signals JSONB,
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    delivered_at TIMESTAMPTZ,
    metadata JSONB
);

-- Feedback collection (Issue #104)
CREATE TABLE recommendation_feedback (
    id SERIAL PRIMARY KEY,
    recommendation_id INT REFERENCES recommendations(id),
    child_id VARCHAR(50) REFERENCES children(id),
    was_helpful BOOLEAN NOT NULL,
    feedback_notes TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Personalization enhancement
ALTER TABLE children ADD COLUMN chronotype VARCHAR(20);
ALTER TABLE children ADD COLUMN preferred_interventions JSONB;
```

## Testing Strategy

- **Unit Tests**: ≥80% coverage requirement met
- **Rule Validation**: Each recommendation rule has dedicated test cases
- **Edge Case Handling**: Error conditions and missing data scenarios
- **Integration Tests**: API endpoint and feature flag behavior
- **Performance Tests**: Large context processing (future)

## Usage Examples

### Basic Generation
```typescript
import { generateRecommendations } from '@services/recommendations/recommendationService';

const context: RecommendationContext = {
  childId: 'child-123',
  recentMetrics: {
    wellnessScore: 45,
    avgMood: 5.2,
    routinesCompleted: 2,
    trend: 'downward'
  },
  engagementSignals: {
    streaks: 1,
    missedRoutines: 3
  },
  screenTimeMinutes: 150
};

const recommendations = await generateRecommendations('child-123', context);
```

### API Usage
```bash
# Get recommendations for a child
GET /api/recommendations?childId=child-123&userId=parent-456

# Filter by priority
GET /api/recommendations?childId=child-123&userId=parent-456&priority=high,medium

# Limit results
GET /api/recommendations?childId=child-123&userId=parent-456&maxRecommendations=3
```

## Development Notes

### Adding New Rules
1. Add rule method to `RecommendationEngine` class
2. Call rule method in `generateRecommendations()`
3. Add corresponding unit tests
4. Update documentation

### Feature Flag Testing
```bash
# Enable recommendations
export RECOMMENDATIONS_ENABLED=true

# Disable recommendations  
export RECOMMENDATIONS_ENABLED=false
```

### Model Artifacts
Future ML models will be stored in `models/recommendation/` (already gitignored).

## Performance Considerations

- **Caching**: Future Redis integration for repeated context queries
- **Batch Processing**: Background recommendation generation
- **Rate Limiting**: API endpoint protection
- **Async Processing**: Non-blocking recommendation delivery

## Security & Privacy

- **Feature Flag Protection**: Recommendations can be disabled instantly
- **Data Minimization**: Only necessary context data processed
- **Authentication**: Consistent with existing parent dashboard patterns
- **Audit Logging**: Recommendation generation tracking (future)

---

**Status**: ✅ Phase 1 Complete - Rule-based foundation ready
**Next**: Feedback loop integration (Issue #104)
**Contact**: See parent dashboard API documentation for integration patterns