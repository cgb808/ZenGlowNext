# ZenGlow Clustering & Feature Engineering Pipeline

## Overview

This pipeline implements comprehensive feature engineering and clustering analysis for wellness sensor and mood data in the ZenGlow application. It transforms raw sensor data into meaningful features and identifies behavioral patterns through unsupervised learning.

## Components

### 1. Feature Engineering Module (`feature_engineering.py`)

Transforms raw wellness data into features suitable for clustering analysis.

#### Feature Categories

**Temporal Features (10 features)**
- `hour_of_day`: Hour extraction (0-23) 
- `day_of_week`: Day of week (0-6, Monday=0)
- `is_weekend`: Binary weekend indicator
- `circadian_bucket`: Categorical time bucket (morning/afternoon/evening/night)
- `is_morning/afternoon/evening/night`: One-hot encoded circadian buckets
- `hour_sin/hour_cos`: Cyclical hour encoding
- `day_sin/day_cos`: Cyclical day encoding

**Rolling Statistical Features (75 features)**
- Calculates rolling statistics over windows of 3, 6, and 12 time periods
- Statistics: mean, std, min, max, median
- Applied to core physiological metrics: heart_rate, hrv, stress_indicator, mood_score, confidence
- Example: `heart_rate_rolling_6_mean`, `mood_score_rolling_12_std`

**Mood-Specific Features (7 features)**
- `mood_score_normalized`: Normalized mood score (0-1)
- `mood_category`: Categorized mood (low/medium/high)
- `mood_volatility_6h`: Rolling standard deviation of mood
- `wellness_report_normalized`: Normalized self-report score
- `confidence_normalized`: Normalized confidence score
- `mood_low/medium/high`: One-hot encoded mood categories

**Physiological Features (9 features)**  
- `hr_resting/moderate/vigorous_zone`: Heart rate zone indicators
- `activity_level_encoded`: Encoded activity levels (0-3)
- `steps_goal_met`: Daily step goal achievement (binary)
- `steps_per_1000`: Scaled step count
- `stress_level`: Normalized stress indicator
- `high_stress`: High stress threshold indicator
- `hrv_normalized`: Normalized heart rate variability

**Behavioral Features (6 features)**
- `screen_time_low/moderate/high`: Screen time categories
- `app_interactions_per_hour`: Normalized app interaction rate
- `response_time_fast/slow`: Response time categories

#### Rationale

1. **Temporal Features**: Capture circadian rhythms and daily patterns crucial for wellness analysis
2. **Rolling Statistics**: Smooth noisy sensor data and capture trends over different time horizons
3. **Categorical Encoding**: Transform categorical variables for clustering algorithms
4. **Normalization**: Ensure features are on comparable scales
5. **Domain Knowledge**: Features specifically designed for wellness applications

### 2. Clustering Pipeline Module (`clustering_pipeline.py`)

Implements clustering analysis using multiple algorithms from scikit-learn.

#### Supported Algorithms

**K-Means Clustering**
- Partitional clustering for spherical clusters
- Automatic optimal k selection using silhouette score
- Range tested: k=2 to k=10

**DBSCAN Clustering**  
- Density-based clustering for arbitrary cluster shapes
- Identifies noise points and outliers
- Default parameters: eps=0.5, min_samples=5

**Agglomerative Clustering**
- Hierarchical clustering approach
- Automatic optimal k selection
- Uses Ward linkage by default

**HDBSCAN (optional)**
- Enhanced density-based clustering
- Automatic cluster number detection
- Requires separate installation

#### Clustering Metrics

- **Silhouette Score**: Measures cluster cohesion and separation (-1 to 1, higher is better)
- **Calinski-Harabasz Index**: Ratio of between-cluster to within-cluster variance (higher is better)  
- **Davies-Bouldin Index**: Average similarity between clusters (lower is better)

### 3. Experiment Script (`run_clustering_experiment.py`)

Main script that orchestrates the complete pipeline.

#### Usage

```bash
# Run with synthetic data (default)
python3 run_clustering_experiment.py

# Run with custom data file
python3 run_clustering_experiment.py --data /path/to/data.csv

# Specify output directory
python3 run_clustering_experiment.py --output /custom/output/dir
```

#### Data Format

Expected CSV columns:
- `timestamp`: ISO format datetime
- `device_id`: Unique device identifier
- `heart_rate`: Heart rate (BPM)
- `hrv`: Heart rate variability
- `steps`: Step count
- `activity_level`: Activity category (sedentary/light/moderate/vigorous)
- `stress_indicator`: Stress level (0-1)
- `mood_score`: Mood score (0-1)
- `confidence`: Confidence in mood rating (0-1)
- `wellness_self_report`: Self-reported wellness (1-10)
- `screen_time`: Screen time (minutes)
- `app_interactions`: App interaction count
- `response_time`: Average response time (seconds)

## Output Files

### Labeled Data
- `clustered_data.csv`: Original data with cluster labels
- `clustered_data.parquet`: Parquet format (if pyarrow available)

### Models
- `clustering_model.pkl`: Trained clustering models and scalers

### Analysis
- `cluster_analysis.txt`: Detailed cluster characteristics
- `experiment_summary.txt`: Complete experiment summary

## Example Results

```
📋 CLUSTER SUMMARY METRICS
==================================================

✅ KMEANS:
   • Clusters: 2
   • Total samples: 2000
   • Silhouette Score: 0.087
   • Calinski-Harabasz: 206.5
   • Davies-Bouldin: 3.028
   • Cluster sizes: [918, 1082]
```

## Cluster Interpretation

Clusters typically represent distinct wellness behavior patterns:

- **Cluster 0**: Lower activity, higher stress, evening-oriented patterns
- **Cluster 1**: Higher activity, lower stress, morning-oriented patterns

## Future Enhancements (Placeholder for Incremental/Online Updates)

### Incremental Clustering
- Implement streaming clustering for real-time updates
- Use `MiniBatchKMeans` for large datasets
- Add data drift detection using statistical tests

### Online Learning
- Support for `partial_fit` methods where available
- Implement concept drift detection
- Add model retraining triggers based on performance degradation

### Advanced Features
- Integration with time-series clustering (DTW-based)
- Ensemble clustering methods
- Automated feature selection
- Personalized clustering per individual

## Dependencies

- pandas>=1.3.0
- numpy>=1.20.0
- scikit-learn>=1.0.0
- pyarrow (optional, for Parquet support)
- hdbscan (optional, for HDBSCAN clustering)

## Installation

```bash
# Install required packages
pip install pandas numpy scikit-learn

# Optional packages
pip install pyarrow hdbscan
```

## Performance Notes

- Processing time scales with O(n*f) for feature engineering where n=samples, f=features
- K-means: O(n*k*i) where k=clusters, i=iterations
- DBSCAN: O(n log n) with spatial indexing
- Memory usage peaks during rolling feature calculation

## Validation

The pipeline includes extensive validation:
- Missing value handling
- Infinite value replacement  
- Feature scaling normalization
- Cluster quality metrics
- Comprehensive error handling

## Integration Points

This pipeline integrates with:
- ZenGlow's existing data processing infrastructure
- Mobile app data collection
- Real-time inference systems
- Dashboard visualization components

For questions or issues, refer to the ZenGlow technical documentation or the AI agents development team.