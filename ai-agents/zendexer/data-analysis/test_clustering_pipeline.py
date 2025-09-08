#!/usr/bin/env python3
"""
Simple test for ZenGlow clustering pipeline
Tests basic functionality of feature engineering and clustering modules
"""

import sys
import os
import tempfile
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

try:
    from feature_engineering import WellnessFeatureEngineer
    from clustering_pipeline import WellnessClusteringPipeline
    import pandas as pd
    import numpy as np
    
    def test_basic_functionality():
        """Test basic functionality of the pipeline"""
        try:
            print("🧪 Testing ZenGlow Clustering Pipeline...")
            
            # Create simple test data
            np.random.seed(42)
            n_samples = 100
            test_data = {
                'timestamp': pd.date_range('2024-01-01', periods=n_samples, freq='1H'),
                'device_id': ['test_device'] * n_samples,
                'heart_rate': np.random.normal(75, 15, n_samples),
                'hrv': np.random.normal(50, 10, n_samples),
                'steps': np.random.randint(0, 2000, n_samples),
                'activity_level': np.random.choice(['sedentary', 'light', 'moderate'], n_samples),
                'stress_indicator': np.random.uniform(0, 1, n_samples),
                'mood_score': np.random.uniform(0, 1, n_samples),
                'confidence': np.random.uniform(0.5, 1, n_samples),
                'wellness_self_report': np.random.uniform(1, 10, n_samples),
                'screen_time': np.random.uniform(0, 120, n_samples),
                'app_interactions': np.random.randint(0, 20, n_samples),
                'response_time': np.random.uniform(1, 5, n_samples),
                'notification_count': np.random.randint(0, 10, n_samples)
            }
            
            df = pd.DataFrame(test_data)
            print(f"✅ Created test data: {df.shape}")
            
            # Test feature engineering
            print("\n🔧 Testing feature engineering...")
            feature_engineer = WellnessFeatureEngineer()
            df_features = feature_engineer.engineer_all_features(df)
            
            assert df_features.shape[1] > df.shape[1], "Features should be added"
            print(f"✅ Feature engineering works: {df.shape[1]} -> {df_features.shape[1]} features")
            
            # Test clustering
            print("\n🎯 Testing clustering...")
            clustering_pipeline = WellnessClusteringPipeline(random_state=42)
            
            # Select numeric features
            numeric_cols = df_features.select_dtypes(include=[np.number]).columns.tolist()
            feature_cols = [col for col in numeric_cols 
                           if not any(x in col.lower() for x in ['timestamp', 'device_id'])][:10]  # Limit for test
            
            X = clustering_pipeline.prepare_data(df_features, feature_cols)
            assert X.shape[0] == n_samples, "Data preparation should preserve sample count"
            print(f"✅ Data preparation works: {X.shape}")
            
            X_scaled = clustering_pipeline.scale_features(X)
            assert abs(X_scaled.mean()) < 0.01, "Scaled data should have zero mean"
            print(f"✅ Feature scaling works: mean={X_scaled.mean():.3f}")
            
            # Test clustering
            labels = clustering_pipeline.perform_clustering(X_scaled, 'kmeans', n_clusters=2)
            assert len(labels) == n_samples, "Should have label for each sample"
            assert len(np.unique(labels)) <= 2, "Should have at most 2 clusters"
            print(f"✅ Clustering works: {len(np.unique(labels))} clusters found")
            
            # Test analysis
            df_with_labels = df_features.copy()
            df_with_labels['cluster'] = labels
            analysis = clustering_pipeline.analyze_clusters(df_with_labels, X_scaled)
            assert 'cluster_summary' in analysis, "Analysis should include cluster summary"
            print(f"✅ Cluster analysis works: {analysis['n_clusters']} clusters analyzed")
            
            # Test saving (to temp directory)
            with tempfile.TemporaryDirectory() as tmp_dir:
                saved_files = clustering_pipeline.save_clustering_results(analysis, df_with_labels, tmp_dir)
                assert 'clustered_data_csv' in saved_files, "Should save CSV file"
                assert Path(saved_files['clustered_data_csv']).exists(), "CSV file should exist"
                print(f"✅ Results saving works: {len(saved_files)} files saved")
            
            print("\n🎉 All tests passed! Pipeline is working correctly.")
            return True
            
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
            return False

if __name__ == "__main__":
    success = test_basic_functionality()
    sys.exit(0 if success else 1)