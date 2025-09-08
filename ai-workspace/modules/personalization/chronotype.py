"""
Chronotype Detection Module

Analyzes sleep patterns to classify children as:
- Early bird (wakes up early, peak energy in morning)
- Night owl (peak energy in evening)
- Intermediate (balanced)

This module provides clean separation between data preparation and clustering logic.
"""

from enum import Enum
from typing import Optional
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import warnings

warnings.filterwarnings('ignore', category=FutureWarning)


class ChronoType(Enum):
    """Chronotype classification constants"""
    EARLY_BIRD = "early_bird"
    NIGHT_OWL = "night_owl"
    INTERMEDIATE = "intermediate"


def prepare_sleep_data(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Prepare and validate sleep data for chronotype analysis.
    
    Args:
        df: DataFrame with columns: ['hour', 'sleep_duration', 'sleep_state']
            - hour: Hour of sleep/wake event (0-23)
            - sleep_duration: Duration of sleep in hours
            - sleep_state: Sleep state ('sleep', 'wake', etc.)
    
    Returns:
        Cleaned DataFrame ready for clustering or None if insufficient data
    """
    if df is None or df.empty:
        print("⚠️  No sleep data provided")
        return None
    
    # Validate required columns
    required_cols = ['hour', 'sleep_duration', 'sleep_state']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"⚠️  Missing required columns: {missing_cols}")
        return None
    
    # Filter for valid sleep/wake events
    df_clean = df.copy()
    df_clean = df_clean.dropna(subset=['hour', 'sleep_duration'])
    df_clean = df_clean[df_clean['hour'].between(0, 23)]
    df_clean = df_clean[df_clean['sleep_duration'] > 0]
    
    if len(df_clean) < 5:
        print(f"⚠️  Insufficient data points ({len(df_clean)}). Need at least 5 valid records.")
        return None
    
    print(f"✅ Prepared {len(df_clean)} data points for chronotype analysis")
    return df_clean


def perform_clustering(df: pd.DataFrame) -> tuple:
    """
    Perform K-means clustering on sleep patterns.
    
    Args:
        df: Prepared sleep data DataFrame
        
    Returns:
        Tuple of (cluster_labels, cluster_centers, avg_hours_by_cluster)
    """
    # Extract features for clustering
    features = df[['hour', 'sleep_duration']].values
    
    # Standardize features for better clustering
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)
    
    # Perform K-means clustering with 3 clusters
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(features_scaled)
    
    # Add cluster labels to dataframe for analysis
    df_clustered = df.copy()
    df_clustered['cluster'] = cluster_labels
    
    # Calculate average hour for each cluster
    avg_hours_by_cluster = df_clustered.groupby('cluster')['hour'].mean()
    
    return cluster_labels, kmeans.cluster_centers_, avg_hours_by_cluster


def classify_chronotype(avg_hours_by_cluster: pd.Series) -> str:
    """
    Classify chronotype based on cluster analysis.
    
    Args:
        avg_hours_by_cluster: Series with average hours for each cluster
        
    Returns:
        Chronotype classification string
    """
    # Find clusters with earliest and latest average hours
    earliest_cluster = avg_hours_by_cluster.idxmin()
    latest_cluster = avg_hours_by_cluster.idxmax()
    
    earliest_hour = avg_hours_by_cluster.min()
    latest_hour = avg_hours_by_cluster.max()
    
    print(f"📊 Cluster analysis:")
    print(f"   Earliest cluster {earliest_cluster}: avg {earliest_hour:.1f}h")
    print(f"   Latest cluster {latest_cluster}: avg {latest_hour:.1f}h")
    
    # Classification logic based on sleep/wake patterns
    hour_difference = latest_hour - earliest_hour
    
    # More sensitive classification
    if earliest_hour <= 7.0 and latest_hour <= 22.0:
        # Early bird: early wake times (before 7 AM) and earlier bedtimes
        return ChronoType.EARLY_BIRD.value
    elif earliest_hour >= 8.5 or latest_hour >= 22.5:
        # Night owl: later wake times (after 8:30 AM) OR later bedtimes (after 10:30 PM)
        return ChronoType.NIGHT_OWL.value
    elif earliest_hour <= 6.5 and hour_difference >= 6:
        # Strong early bird pattern: very early wake times
        return ChronoType.EARLY_BIRD.value
    elif latest_hour >= 23.0 and hour_difference >= 6:
        # Strong night owl pattern: very late bedtimes
        return ChronoType.NIGHT_OWL.value
    else:
        # Intermediate pattern
        return ChronoType.INTERMEDIATE.value


def detect_chronotype(child_id: str, df: pd.DataFrame) -> str:
    """
    Detect chronotype for a given child based on sleep data.
    
    Args:
        child_id: Unique identifier for the child
        df: DataFrame with sleep data containing columns:
            - hour: Hour of sleep/wake event (0-23)
            - sleep_duration: Duration of sleep in hours
            - sleep_state: Sleep state indicator
    
    Returns:
        Chronotype classification: 'early_bird', 'night_owl', or 'intermediate'
    """
    print(f"\n🔍 Analyzing chronotype for child: {child_id}")
    
    # Step 1: Prepare and validate data
    df_clean = prepare_sleep_data(df)
    if df_clean is None:
        print(f"❌ Cannot determine chronotype for {child_id} - insufficient data")
        return ChronoType.INTERMEDIATE.value  # Default fallback
    
    # Step 2: Perform clustering analysis
    try:
        cluster_labels, cluster_centers, avg_hours_by_cluster = perform_clustering(df_clean)
    except Exception as e:
        print(f"❌ Clustering failed for {child_id}: {e}")
        return ChronoType.INTERMEDIATE.value  # Default fallback
    
    # Step 3: Classify chronotype
    chronotype = classify_chronotype(avg_hours_by_cluster)
    
    print(f"🎯 Detected chronotype for {child_id}: {chronotype}")
    
    return chronotype


# Database Integration Placeholder
"""
DATABASE INTEGRATION NOTES:

To integrate with the production database, replace the mock data generation with:

1. Database Fetch:
   ```python
   import sqlalchemy as sa
   from your_db_module import engine
   
   def fetch_sleep_data(child_id: str) -> pd.DataFrame:
       query = '''
       SELECT
           EXTRACT(HOUR FROM timestamp) AS hour,
           sleep_duration,
           sleep_state
       FROM wellness_metrics
       WHERE child_id = %s 
           AND timestamp >= NOW() - INTERVAL '30 days'
       ORDER BY timestamp
       '''
       return pd.read_sql(query, engine, params=[child_id])
   ```

2. Database Update:
   ```python
   def update_chronotype_in_db(child_id: str, chronotype: str):
       query = '''
       UPDATE children 
       SET chronotype = %s, 
           chronotype_updated_at = NOW()
       WHERE id = %s
       '''
       with engine.connect() as conn:
           conn.execute(sa.text(query), [chronotype, child_id])
           conn.commit()
   ```

3. Integration in main function:
   ```python
   def detect_and_store_chronotype(child_id: str):
       df = fetch_sleep_data(child_id)
       chronotype = detect_chronotype(child_id, df)
       update_chronotype_in_db(child_id, chronotype)
       return chronotype
   ```

Required database schema:
- Add 'chronotype' VARCHAR(20) column to children table
- Add 'chronotype_updated_at' TIMESTAMP column for tracking updates
"""