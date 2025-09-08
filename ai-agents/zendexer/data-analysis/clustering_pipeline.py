#!/usr/bin/env python3
"""
Clustering Pipeline for ZenGlow Wellness Data
Implements clustering analysis using scikit-learn algorithms
"""

import pandas as pd
import numpy as np
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
from sklearn.model_selection import ParameterGrid
import pickle
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import warnings
warnings.filterwarnings('ignore')

try:
    # Try to import HDBSCAN if available (requires manual install)
    import hdbscan
    HDBSCAN_AVAILABLE = True
except ImportError:
    HDBSCAN_AVAILABLE = False
    print("ℹ️  HDBSCAN not available, using scikit-learn algorithms only")


class WellnessClusteringPipeline:
    """Clustering pipeline for wellness data analysis"""
    
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.scaler = None
        self.clusterer = None
        self.cluster_labels = None
        self.cluster_metrics = {}
        self.feature_names = None
        
    def prepare_data(self, df: pd.DataFrame, 
                    feature_columns: Optional[List[str]] = None,
                    exclude_patterns: List[str] = ['timestamp', 'device_id', 'text_input']) -> np.ndarray:
        """Prepare data for clustering by selecting and scaling features"""
        print("🔧 Preparing data for clustering...")
        
        # Auto-select numeric features if not specified
        if feature_columns is None:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            # Exclude non-feature columns
            feature_columns = [col for col in numeric_cols 
                             if not any(pattern in col.lower() for pattern in exclude_patterns)]
        
        # Store feature names for later use
        self.feature_names = feature_columns
        
        # Extract features
        X = df[feature_columns].copy()
        
        # Handle missing values
        X = X.fillna(X.mean())
        
        # Remove infinite values
        X = X.replace([np.inf, -np.inf], np.nan).fillna(X.mean())
        
        print(f"   • Selected {len(feature_columns)} features")
        print(f"   • Data shape: {X.shape}")
        print(f"   • Features: {feature_columns[:5]}{'...' if len(feature_columns) > 5 else ''}")
        
        return X.values
    
    def scale_features(self, X: np.ndarray, method: str = 'standard') -> np.ndarray:
        """Scale features for clustering"""
        print(f"📏 Scaling features using {method} scaling...")
        
        if method == 'standard':
            self.scaler = StandardScaler()
        elif method == 'minmax':
            self.scaler = MinMaxScaler()
        else:
            raise ValueError("Scaling method must be 'standard' or 'minmax'")
        
        X_scaled = self.scaler.fit_transform(X)
        
        print(f"   • Scaled data shape: {X_scaled.shape}")
        print(f"   • Mean: {X_scaled.mean():.3f}, Std: {X_scaled.std():.3f}")
        
        return X_scaled
    
    def find_optimal_clusters(self, X: np.ndarray, 
                            algorithm: str = 'kmeans',
                            k_range: Tuple[int, int] = (2, 10)) -> Dict[str, Any]:
        """Find optimal number of clusters using various metrics"""
        print(f"🔍 Finding optimal clusters using {algorithm}...")
        
        k_min, k_max = k_range
        results = {
            'k_values': [],
            'silhouette_scores': [],
            'calinski_harabasz_scores': [],
            'davies_bouldin_scores': [],
            'inertias': [] if algorithm == 'kmeans' else None
        }
        
        for k in range(k_min, k_max + 1):
            try:
                if algorithm == 'kmeans':
                    clusterer = KMeans(n_clusters=k, random_state=self.random_state, n_init=10)
                elif algorithm == 'agglomerative':
                    clusterer = AgglomerativeClustering(n_clusters=k)
                else:
                    continue
                
                labels = clusterer.fit_predict(X)
                
                # Calculate metrics
                if len(np.unique(labels)) > 1:  # Need at least 2 clusters for metrics
                    sil_score = silhouette_score(X, labels)
                    ch_score = calinski_harabasz_score(X, labels)
                    db_score = davies_bouldin_score(X, labels)
                    
                    results['k_values'].append(k)
                    results['silhouette_scores'].append(sil_score)
                    results['calinski_harabasz_scores'].append(ch_score)
                    results['davies_bouldin_scores'].append(db_score)
                    
                    if algorithm == 'kmeans':
                        results['inertias'].append(clusterer.inertia_)
                    
                    print(f"   • k={k}: Silhouette={sil_score:.3f}, CH={ch_score:.1f}, DB={db_score:.3f}")
                
            except Exception as e:
                print(f"   • Warning: Failed to cluster with k={k}: {str(e)}")
                continue
        
        # Find optimal k based on silhouette score
        if results['silhouette_scores']:
            best_k_idx = np.argmax(results['silhouette_scores'])
            optimal_k = results['k_values'][best_k_idx]
            print(f"   • Optimal k based on silhouette score: {optimal_k}")
            results['optimal_k'] = optimal_k
        
        return results
    
    def perform_clustering(self, X: np.ndarray, 
                          algorithm: str = 'kmeans',
                          n_clusters: Optional[int] = None,
                          **kwargs) -> np.ndarray:
        """Perform clustering with specified algorithm"""
        print(f"🎯 Performing {algorithm} clustering...")
        
        if algorithm == 'kmeans':
            if n_clusters is None:
                n_clusters = 3  # Default
            self.clusterer = KMeans(n_clusters=n_clusters, 
                                  random_state=self.random_state, 
                                  n_init=10,
                                  **kwargs)
            
        elif algorithm == 'dbscan':
            eps = kwargs.get('eps', 0.5)
            min_samples = kwargs.get('min_samples', 5)
            self.clusterer = DBSCAN(eps=eps, min_samples=min_samples)
            
        elif algorithm == 'agglomerative':
            if n_clusters is None:
                n_clusters = 3
            self.clusterer = AgglomerativeClustering(n_clusters=n_clusters, **kwargs)
            
        elif algorithm == 'hdbscan' and HDBSCAN_AVAILABLE:
            min_cluster_size = kwargs.get('min_cluster_size', 5)
            self.clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, **kwargs)
            
        else:
            raise ValueError(f"Unknown or unavailable algorithm: {algorithm}")
        
        # Fit and predict
        self.cluster_labels = self.clusterer.fit_predict(X)
        
        # Calculate metrics
        if len(np.unique(self.cluster_labels)) > 1:
            # Filter out noise points for DBSCAN/HDBSCAN (label -1)
            valid_mask = self.cluster_labels != -1
            if valid_mask.sum() > 0:
                X_valid = X[valid_mask]
                labels_valid = self.cluster_labels[valid_mask]
                
                if len(np.unique(labels_valid)) > 1:
                    self.cluster_metrics = {
                        'silhouette_score': silhouette_score(X_valid, labels_valid),
                        'calinski_harabasz_score': calinski_harabasz_score(X_valid, labels_valid),
                        'davies_bouldin_score': davies_bouldin_score(X_valid, labels_valid),
                        'n_clusters': len(np.unique(labels_valid)),
                        'n_noise_points': (self.cluster_labels == -1).sum() if algorithm in ['dbscan', 'hdbscan'] else 0
                    }
        
        unique_labels = np.unique(self.cluster_labels)
        n_clusters = len(unique_labels)
        n_noise = (self.cluster_labels == -1).sum() if -1 in unique_labels else 0
        
        print(f"   • Found {n_clusters} clusters")
        if n_noise > 0:
            print(f"   • Noise points: {n_noise}")
        print(f"   • Cluster distribution: {np.bincount(self.cluster_labels[self.cluster_labels >= 0])}")
        
        return self.cluster_labels
    
    def analyze_clusters(self, df: pd.DataFrame, X: np.ndarray) -> Dict[str, Any]:
        """Analyze cluster characteristics and create summaries"""
        print("📊 Analyzing cluster characteristics...")
        
        if self.cluster_labels is None:
            raise ValueError("No clustering performed yet. Call perform_clustering() first.")
        
        # Add cluster labels to dataframe
        df_analysis = df.copy()
        df_analysis['cluster'] = self.cluster_labels
        
        cluster_summary = {}
        unique_clusters = np.unique(self.cluster_labels)
        unique_clusters = unique_clusters[unique_clusters >= 0]  # Exclude noise (-1)
        
        for cluster_id in unique_clusters:
            cluster_mask = self.cluster_labels == cluster_id
            cluster_data = df_analysis[cluster_mask]
            
            # Basic statistics
            cluster_size = cluster_mask.sum()
            cluster_summary[f'cluster_{cluster_id}'] = {
                'size': cluster_size,
                'percentage': (cluster_size / len(df_analysis)) * 100,
                'characteristics': {}
            }
            
            # Analyze numeric features
            if self.feature_names:
                numeric_features = [col for col in self.feature_names if col in df_analysis.columns]
                for feature in numeric_features[:10]:  # Limit to top 10 features
                    if feature in cluster_data.columns:
                        mean_val = cluster_data[feature].mean()
                        std_val = cluster_data[feature].std()
                        cluster_summary[f'cluster_{cluster_id}']['characteristics'][feature] = {
                            'mean': mean_val,
                            'std': std_val
                        }
            
            # Analyze categorical features
            categorical_cols = ['mood_category', 'circadian_bucket', 'activity_level']
            for col in categorical_cols:
                if col in cluster_data.columns:
                    mode_val = cluster_data[col].mode()
                    if len(mode_val) > 0:
                        cluster_summary[f'cluster_{cluster_id}']['characteristics'][f'{col}_mode'] = mode_val.iloc[0]
        
        # Overall metrics
        analysis_results = {
            'cluster_summary': cluster_summary,
            'metrics': self.cluster_metrics,
            'total_samples': len(df_analysis),
            'n_clusters': len(unique_clusters),
            'feature_names': self.feature_names
        }
        
        print(f"   • Analyzed {len(unique_clusters)} clusters")
        print(f"   • Cluster sizes: {[cluster_summary[f'cluster_{i}']['size'] for i in unique_clusters]}")
        
        return analysis_results
    
    def save_clustering_results(self, results: Dict[str, Any], 
                              df_with_clusters: pd.DataFrame,
                              output_dir: str = "/tmp/clustering_results") -> Dict[str, str]:
        """Save clustering results and labeled data"""
        print("💾 Saving clustering results...")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        saved_files = {}
        
        # Save labeled dataset as CSV (always available)
        csv_path = output_path / "clustered_data.csv"
        df_with_clusters.to_csv(csv_path, index=False)
        saved_files['clustered_data_csv'] = str(csv_path)
        
        # Try to save as parquet if possible
        try:
            parquet_path = output_path / "clustered_data.parquet"
            df_with_clusters.to_parquet(parquet_path, index=False)
            saved_files['clustered_data_parquet'] = str(parquet_path)
        except Exception as e:
            print(f"   ⚠️  Could not save parquet (missing pyarrow): {str(e)}")
        
        # Save clustering model
        if self.clusterer is not None:
            model_path = output_path / "clustering_model.pkl"
            with open(model_path, 'wb') as f:
                pickle.dump({
                    'clusterer': self.clusterer,
                    'scaler': self.scaler,
                    'feature_names': self.feature_names,
                    'cluster_metrics': self.cluster_metrics
                }, f)
            saved_files['model'] = str(model_path)
        
        # Save analysis results as JSON-like format
        summary_path = output_path / "cluster_analysis.txt"
        with open(summary_path, 'w') as f:
            f.write("=== CLUSTERING ANALYSIS SUMMARY ===\n\n")
            f.write(f"Total samples: {results['total_samples']}\n")
            f.write(f"Number of clusters: {results['n_clusters']}\n")
            f.write(f"Features used: {len(results['feature_names'])}\n\n")
            
            if 'metrics' in results and results['metrics']:
                f.write("=== CLUSTERING METRICS ===\n")
                for metric, value in results['metrics'].items():
                    f.write(f"{metric}: {value:.4f}\n")
                f.write("\n")
            
            f.write("=== CLUSTER CHARACTERISTICS ===\n")
            for cluster_name, cluster_info in results['cluster_summary'].items():
                f.write(f"\n{cluster_name.upper()}:\n")
                f.write(f"  Size: {cluster_info['size']} ({cluster_info['percentage']:.1f}%)\n")
                f.write("  Key characteristics:\n")
                for char_name, char_value in cluster_info['characteristics'].items():
                    if isinstance(char_value, dict):
                        f.write(f"    {char_name}: mean={char_value.get('mean', 0):.3f}, std={char_value.get('std', 0):.3f}\n")
                    else:
                        f.write(f"    {char_name}: {char_value}\n")
        
        saved_files['summary'] = str(summary_path)
        
        print(f"   • Saved {len(saved_files)} files to {output_path}")
        for file_type, file_path in saved_files.items():
            print(f"     - {file_type}: {file_path}")
        
        return saved_files
    
    def run_comprehensive_clustering(self, df: pd.DataFrame, 
                                   feature_columns: Optional[List[str]] = None,
                                   algorithms: List[str] = ['kmeans'],
                                   output_dir: str = "/tmp/clustering_results") -> Dict[str, Any]:
        """Run complete clustering pipeline with multiple algorithms"""
        print("\n🚀 Starting comprehensive clustering pipeline...")
        print("=" * 70)
        
        # Prepare data
        X = self.prepare_data(df, feature_columns)
        X_scaled = self.scale_features(X)
        
        all_results = {}
        
        for algorithm in algorithms:
            print(f"\n--- Running {algorithm.upper()} clustering ---")
            
            try:
                # Find optimal parameters
                if algorithm in ['kmeans', 'agglomerative']:
                    optimization_results = self.find_optimal_clusters(X_scaled, algorithm)
                    optimal_k = optimization_results.get('optimal_k', 3)
                    
                    # Perform clustering with optimal parameters
                    labels = self.perform_clustering(X_scaled, algorithm, n_clusters=optimal_k)
                else:
                    # For density-based algorithms, use default parameters
                    labels = self.perform_clustering(X_scaled, algorithm)
                
                # Analyze results
                df_copy = df.copy()
                df_copy['cluster'] = labels
                analysis = self.analyze_clusters(df_copy, X_scaled)
                
                # Save results
                algo_output_dir = f"{output_dir}/{algorithm}"
                saved_files = self.save_clustering_results(analysis, df_copy, algo_output_dir)
                
                all_results[algorithm] = {
                    'analysis': analysis,
                    'saved_files': saved_files,
                    'cluster_labels': labels
                }
                
                print(f"✅ {algorithm.upper()} clustering completed successfully")
                
            except Exception as e:
                print(f"❌ Error in {algorithm} clustering: {str(e)}")
                all_results[algorithm] = {'error': str(e)}
        
        print(f"\n🎉 Clustering pipeline completed! Results saved to {output_dir}")
        return all_results