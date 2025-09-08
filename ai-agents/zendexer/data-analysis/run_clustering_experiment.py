#!/usr/bin/env python3
"""
ZenGlow Clustering Experiment Script
Main script to run clustering experiments and generate insights
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import warnings
warnings.filterwarnings('ignore')

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from feature_engineering import WellnessFeatureEngineer
from clustering_pipeline import WellnessClusteringPipeline


def generate_synthetic_wellness_data(n_samples: int = 1000, n_devices: int = 10) -> pd.DataFrame:
    """Generate synthetic wellness data for demonstration"""
    print("🎲 Generating synthetic wellness data...")
    
    np.random.seed(42)
    
    # Generate time series data
    start_date = pd.Timestamp('2024-01-01')
    
    data = []
    for device_id in range(1, n_devices + 1):
        device_samples = n_samples // n_devices
        
        # Create temporal pattern
        dates = pd.date_range(start_date, periods=device_samples, freq='1H')
        
        for i, timestamp in enumerate(dates):
            hour = timestamp.hour
            day_of_week = timestamp.dayofweek
            
            # Create realistic patterns based on time
            # Morning: higher activity, moderate mood
            # Evening: lower activity, variable mood
            # Weekend: different patterns
            
            is_weekend = day_of_week >= 5
            is_morning = 6 <= hour <= 11
            is_evening = 18 <= hour <= 22
            
            # Base patterns
            base_activity = 0.5
            base_mood = 0.6
            base_stress = 0.3
            
            # Time-based adjustments
            if is_morning:
                base_activity += 0.2
                base_mood += 0.1
                base_stress -= 0.1
            elif is_evening:
                base_activity -= 0.1
                base_stress += 0.1
            
            if is_weekend:
                base_activity -= 0.1
                base_mood += 0.15
                base_stress -= 0.15
            
            # Individual variations
            individual_factor = (device_id % 3) / 10  # 0, 0.1, 0.2
            
            # Generate correlated values
            heart_rate = max(60, min(180, np.random.normal(75 + base_activity * 30, 15)))
            steps = max(0, np.random.normal(base_activity * 2000 + 1000, 500))
            mood_score = max(0, min(1, np.random.normal(base_mood + individual_factor, 0.2)))
            stress_indicator = max(0, min(1, np.random.normal(base_stress, 0.15)))
            
            # Screen time (higher in evening, weekends)
            screen_time_factor = 1.5 if is_evening else (2.0 if is_weekend else 1.0)
            screen_time = max(0, np.random.normal(30 * screen_time_factor, 20))
            
            # HRV (inversely related to stress)
            hrv = max(20, min(100, np.random.normal(50 - stress_indicator * 20, 10)))
            
            # Activity level based on steps and heart rate
            if steps > 1500 and heart_rate > 100:
                activity_level = 'vigorous'
            elif steps > 800 or heart_rate > 85:
                activity_level = 'moderate'
            elif steps > 300:
                activity_level = 'light'
            else:
                activity_level = 'sedentary'
            
            # App interactions
            app_interactions = max(0, np.random.poisson(5 + (screen_time / 30)))
            
            # Response time (slower when stressed or tired)
            response_time = max(0.5, np.random.normal(2.5 + stress_indicator * 2, 1))
            
            # Wellness self-report (1-10 scale)
            wellness_self_report = max(1, min(10, np.random.normal(mood_score * 8 + 2, 1.5)))
            
            # Confidence in mood report
            confidence = max(0, min(1, np.random.normal(0.8, 0.1)))
            
            record = {
                'timestamp': timestamp,
                'device_id': f'device_{device_id:03d}',
                'heart_rate': round(heart_rate, 1),
                'hrv': round(hrv, 1),
                'steps': int(steps),
                'activity_level': activity_level,
                'stress_indicator': round(stress_indicator, 3),
                'mood_score': round(mood_score, 3),
                'confidence': round(confidence, 3),
                'wellness_self_report': round(wellness_self_report, 1),
                'screen_time': round(screen_time, 1),
                'app_interactions': int(app_interactions),
                'response_time': round(response_time, 2),
                'notification_count': np.random.poisson(3)
            }
            
            data.append(record)
    
    df = pd.DataFrame(data)
    print(f"   • Generated {len(df)} samples for {n_devices} devices")
    print(f"   • Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"   • Sample data preview:")
    print(df[['device_id', 'heart_rate', 'mood_score', 'activity_level', 'screen_time']].head(3))
    
    return df


def run_clustering_experiment(data_source: str = "synthetic", 
                            output_dir: str = "/tmp/zenglow_clustering") -> dict:
    """Run the complete clustering experiment"""
    print("\n🧪 Starting ZenGlow Clustering Experiment")
    print("=" * 70)
    
    # Step 1: Load or generate data
    if data_source == "synthetic":
        df = generate_synthetic_wellness_data(n_samples=2000, n_devices=20)
    else:
        # Try to load real data if available
        data_path = Path(data_source)
        if data_path.exists():
            if data_path.suffix == '.csv':
                df = pd.read_csv(data_path)
            elif data_path.suffix == '.parquet':
                df = pd.read_parquet(data_path)
            else:
                raise ValueError(f"Unsupported file format: {data_path.suffix}")
            print(f"📂 Loaded data from {data_path}")
        else:
            print(f"⚠️  Data file not found: {data_path}, using synthetic data")
            df = generate_synthetic_wellness_data()
    
    # Step 2: Feature Engineering
    print(f"\n📊 Original data shape: {df.shape}")
    
    feature_engineer = WellnessFeatureEngineer()
    df_features = feature_engineer.engineer_all_features(df)
    
    # Get feature summary
    feature_summary = feature_engineer.get_feature_importance_summary(df_features)
    
    print(f"\n📈 Feature engineering summary:")
    for category, features in feature_summary.items():
        if features:
            print(f"   • {category}: {len(features)} features")
    
    # Step 3: Clustering Pipeline
    clustering_pipeline = WellnessClusteringPipeline(random_state=42)
    
    # Select features for clustering (exclude metadata)
    feature_columns = []
    exclude_cols = ['timestamp', 'device_id', 'text_input', 'circadian_bucket', 'mood_category', 'activity_level']
    
    for col in df_features.columns:
        if (df_features[col].dtype in [np.number] and 
            not any(exc in col.lower() for exc in exclude_cols)):
            feature_columns.append(col)
    
    print(f"\n🔧 Selected {len(feature_columns)} features for clustering")
    
    # Run clustering with multiple algorithms
    algorithms = ['kmeans', 'dbscan', 'agglomerative']
    
    results = clustering_pipeline.run_comprehensive_clustering(
        df_features, 
        feature_columns=feature_columns,
        algorithms=algorithms,
        output_dir=output_dir
    )
    
    # Step 4: Generate Summary Metrics
    experiment_summary = {
        'data_info': {
            'n_samples': len(df),
            'n_devices': df['device_id'].nunique(),
            'time_span': str(df['timestamp'].max() - df['timestamp'].min()),
            'original_features': df.shape[1],
            'engineered_features': df_features.shape[1],
            'clustering_features': len(feature_columns)
        },
        'feature_summary': feature_summary,
        'algorithms_run': list(results.keys()),
        'output_directory': output_dir,
        'results': results
    }
    
    # Save experiment summary
    summary_path = Path(output_dir) / "experiment_summary.txt"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(summary_path, 'w') as f:
        f.write("=== ZENGLOW CLUSTERING EXPERIMENT SUMMARY ===\n\n")
        f.write(f"Experiment completed: {pd.Timestamp.now()}\n\n")
        
        f.write("=== DATA INFORMATION ===\n")
        for key, value in experiment_summary['data_info'].items():
            f.write(f"{key}: {value}\n")
        
        f.write(f"\n=== FEATURE ENGINEERING ===\n")
        for category, features in feature_summary.items():
            if features:
                f.write(f"{category.title()}: {len(features)} features\n")
                if len(features) <= 5:
                    f.write(f"  - {', '.join(features)}\n")
                else:
                    f.write(f"  - {', '.join(features[:3])} ... ({len(features)-3} more)\n")
        
        f.write(f"\n=== CLUSTERING RESULTS ===\n")
        for algo in algorithms:
            if algo in results and 'error' not in results[algo]:
                analysis = results[algo]['analysis']
                f.write(f"\n{algo.upper()}:\n")
                f.write(f"  Clusters found: {analysis['n_clusters']}\n")
                if 'metrics' in analysis and analysis['metrics']:
                    for metric, value in analysis['metrics'].items():
                        f.write(f"  {metric}: {value:.4f}\n")
            else:
                f.write(f"\n{algo.upper()}: Failed to run\n")
    
    print(f"\n✅ Experiment completed! Summary saved to {summary_path}")
    
    return experiment_summary


def print_cluster_summary_metrics(results: dict):
    """Print cluster summary metrics to console"""
    print("\n📋 CLUSTER SUMMARY METRICS")
    print("=" * 50)
    
    for algorithm, result in results.items():
        if 'error' in result:
            print(f"\n❌ {algorithm.upper()}: {result['error']}")
            continue
            
        analysis = result['analysis']
        print(f"\n✅ {algorithm.upper()}:")
        print(f"   • Clusters: {analysis['n_clusters']}")
        print(f"   • Total samples: {analysis['total_samples']}")
        
        if 'metrics' in analysis and analysis['metrics']:
            metrics = analysis['metrics']
            print(f"   • Silhouette Score: {metrics.get('silhouette_score', 'N/A'):.3f}")
            print(f"   • Calinski-Harabasz: {metrics.get('calinski_harabasz_score', 'N/A'):.1f}")
            print(f"   • Davies-Bouldin: {metrics.get('davies_bouldin_score', 'N/A'):.3f}")
            
            if 'n_noise_points' in metrics and metrics['n_noise_points'] > 0:
                print(f"   • Noise points: {metrics['n_noise_points']}")
        
        # Print cluster sizes
        cluster_summary = analysis['cluster_summary']
        cluster_sizes = [info['size'] for info in cluster_summary.values()]
        print(f"   • Cluster sizes: {cluster_sizes}")


def main():
    """Main experiment runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ZenGlow Clustering Experiment")
    parser.add_argument('--data', default='synthetic', 
                       help='Data source: "synthetic" or path to data file')
    parser.add_argument('--output', default='/tmp/zenglow_clustering',
                       help='Output directory for results')
    
    args = parser.parse_args()
    
    try:
        # Run the experiment
        results = run_clustering_experiment(args.data, args.output)
        
        # Print summary metrics
        print_cluster_summary_metrics(results['results'])
        
        print(f"\n🎯 All results saved to: {args.output}")
        print("📁 Generated files:")
        print("   • clustered_data.parquet - Labeled data in Parquet format")
        print("   • clustered_data.csv - Labeled data in CSV format")
        print("   • clustering_model.pkl - Trained clustering models")
        print("   • cluster_analysis.txt - Detailed cluster analysis")
        print("   • experiment_summary.txt - Complete experiment summary")
        
        # Placeholder for incremental/online updates
        print(f"\n🔄 Future Enhancement: Incremental/Online Clustering")
        print("   • Implement streaming clustering for real-time updates")
        print("   • Add model retraining triggers based on data drift detection")
        print("   • Support for partial_fit methods in online scenarios")
        
        return True
        
    except Exception as e:
        print(f"❌ Experiment failed: {str(e)}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)