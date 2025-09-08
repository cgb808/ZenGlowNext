# Chronotype Detection Module

A scaffold implementation for detecting sleep patterns and classifying children's chronotypes using K-means clustering.

## Features

- **Sleep Pattern Analysis**: Analyzes sleep/wake times and duration patterns
- **Chronotype Classification**: Classifies as early_bird, night_owl, or intermediate
- **Clean Architecture**: Separates data preparation from clustering logic
- **Mock CLI**: Generates random sleep data for testing
- **Database Integration Ready**: Includes placeholder notes for production integration

## Usage

### Basic Detection

```python
from personalization.chronotype import detect_chronotype
import pandas as pd

# Your sleep data (30 days recommended)
df = pd.DataFrame({
    'hour': [21, 6, 22, 7, 20, 6],  # Hour of sleep/wake events
    'sleep_duration': [8.5, 8.5, 7.8, 7.8, 8.2, 8.2],  # Sleep duration
    'sleep_state': ['sleep', 'wake', 'sleep', 'wake', 'sleep', 'wake']
})

chronotype = detect_chronotype('child_123', df)
print(f"Detected chronotype: {chronotype}")
```

### CLI Testing

```bash
# Test with random data
python chronotype_cli.py --child-id test_child --days 30

# Test specific chronotype patterns
python chronotype_cli.py --bias early_bird
python chronotype_cli.py --bias night_owl
python chronotype_cli.py --bias intermediate

# Test all patterns
python chronotype_cli.py --test-all
```

## Chronotype Types

- **early_bird**: 🌅 Peak energy in morning, prefers early bedtime
- **night_owl**: 🦉 Peak energy in evening, prefers late bedtime  
- **intermediate**: ⚖️ Balanced sleep pattern, flexible timing

## Data Requirements

The input DataFrame should contain:

- `hour`: Hour of sleep/wake event (0-23)
- `sleep_duration`: Duration of sleep in hours (positive number)
- `sleep_state`: Sleep state indicator ('sleep', 'wake', 'active', etc.)

Minimum 5 data points required, 30 days recommended for accuracy.

## Algorithm

1. **Data Preparation**: Validates and cleans sleep data
2. **Feature Extraction**: Uses hour and sleep_duration as clustering features
3. **K-means Clustering**: Groups data into 3 clusters using standardized features
4. **Classification**: Analyzes cluster patterns to determine chronotype

## Database Integration

See database integration notes in `chronotype.py` for production setup with:
- Sleep data fetching from `wellness_metrics` table
- Chronotype storage in `children` table
- Automatic updates and timestamps

## Dependencies

- pandas
- scikit-learn
- numpy

## Testing

The module includes comprehensive testing via the CLI:
- Generates realistic sleep patterns for each chronotype
- Tests detection accuracy
- Provides detailed analysis output

```bash
# Install dependencies
pip install pandas scikit-learn numpy

# Run tests
python chronotype_cli.py --test-all
```

## Future Enhancements

- Add confidence scores for chronotype predictions
- Support for multiple children batch processing
- Integration with real wearable device data
- Advanced feature engineering (sleep quality, activity patterns)
- Longitudinal chronotype tracking and changes over time