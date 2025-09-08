#!/usr/bin/env python3
"""
ZenGlow Fitbit Data Analysis
Analyze Fitbit wellness data for meditation insights
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

def load_fitbit_data():
    """Load Fitbit data - modify path as needed"""
    
    # Check for local Fitbit data
    possible_paths = [
        "./data/fitbit/dailyActivity_merged.csv",
        "../data/fitbit/dailyActivity_merged.csv", 
        "./fitbit_data/dailyActivity_merged.csv",
        "/kaggle/input/fitbit/Fitabase Data 4.12.16-5.12.16/dailyActivity_merged.csv"
    ]
    
    for path in possible_paths:
        if Path(path).exists():
            print(f"✅ Found Fitbit data at: {path}")
            return pd.read_csv(path)
    
    print("⚠️  No Fitbit data found. Generating synthetic wellness data...")
    return generate_synthetic_fitbit_data()

def generate_synthetic_fitbit_data():
    """Generate synthetic Fitbit-like data for demonstration"""
    
    dates = pd.date_range('2024-04-12', '2024-05-12', freq='D')
    n_users = 30
    
    data = []
    for user_id in range(1, n_users + 1):
        for date in dates:
            # Simulate daily activity with realistic patterns
            base_steps = np.random.normal(8000, 2500)
            base_calories = base_steps * 0.045 + np.random.normal(1800, 300)
            
            # Weekend vs weekday patterns
            if date.weekday() >= 5:  # Weekend
                steps = max(0, base_steps * np.random.uniform(0.7, 1.3))
                active_minutes = max(0, np.random.normal(25, 10))
            else:  # Weekday
                steps = max(0, base_steps * np.random.uniform(0.9, 1.1))
                active_minutes = max(0, np.random.normal(35, 15))
            
            data.append({
                'Id': f'user_{user_id:03d}',
                'ActivityDate': date.strftime('%m/%d/%Y'),
                'TotalSteps': int(steps),
                'TotalDistance': round(steps * 0.0008, 2),  # km
                'Calories': int(base_calories),
                'VeryActiveMinutes': max(0, int(np.random.normal(15, 8))),
                'FairlyActiveMinutes': max(0, int(active_minutes - 15)),
                'LightlyActiveMinutes': max(0, int(np.random.normal(180, 50))),
                'SedentaryMinutes': int(1440 - active_minutes - 180)
            })
    
    return pd.DataFrame(data)

def analyze_wellness_patterns(data):
    """Analyze wellness patterns for meditation insights"""
    
    print("\n🧘 ZenGlow Wellness Analysis")
    print("=" * 40)
    
    # Basic statistics
    print(f"📊 Dataset Overview:")
    print(f"   • Users: {data['Id'].nunique()}")
    print(f"   • Days: {len(data)}")
    print(f"   • Date range: {data['ActivityDate'].min()} to {data['ActivityDate'].max()}")
    
    # Wellness metrics
    print(f"\n💪 Activity Averages:")
    print(f"   • Steps: {data['TotalSteps'].mean():,.0f}")
    print(f"   • Calories: {data['Calories'].mean():,.0f}")
    print(f"   • Active Minutes: {(data['VeryActiveMinutes'] + data['FairlyActiveMinutes']).mean():.1f}")
    
    # Meditation correlation insights
    data['TotalActiveMinutes'] = data['VeryActiveMinutes'] + data['FairlyActiveMinutes']
    data['ActivityLevel'] = pd.cut(data['TotalActiveMinutes'], 
                                 bins=[0, 20, 45, 100], 
                                 labels=['Low', 'Moderate', 'High'])
    
    activity_groups = data.groupby('ActivityLevel').agg({
        'TotalSteps': 'mean',
        'Calories': 'mean',
        'SedentaryMinutes': 'mean'
    }).round(0)
    
    print(f"\n🎯 Activity Level Groups:")
    print(activity_groups)
    
    return data

def create_wellness_visualizations(data):
    """Create visualizations for wellness insights"""
    
    # Convert date for plotting
    data['Date'] = pd.to_datetime(data['ActivityDate'])
    
    # Daily activity trends
    daily_avg = data.groupby('Date').agg({
        'TotalSteps': 'mean',
        'Calories': 'mean',
        'TotalActiveMinutes': 'mean'
    }).reset_index()
    
    # Create subplot figure
    fig = plt.figure(figsize=(15, 10))
    
    # Steps trend
    plt.subplot(2, 2, 1)
    plt.plot(daily_avg['Date'], daily_avg['TotalSteps'], 'b-', linewidth=2)
    plt.title('📈 Average Daily Steps')
    plt.ylabel('Steps')
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    
    # Activity distribution
    plt.subplot(2, 2, 2)
    activity_counts = data['ActivityLevel'].value_counts()
    plt.pie(activity_counts.values, labels=activity_counts.index, autopct='%1.1f%%')
    plt.title('🎯 Activity Level Distribution')
    
    # Steps vs Calories correlation
    plt.subplot(2, 2, 3)
    plt.scatter(data['TotalSteps'], data['Calories'], alpha=0.5, c='green')
    plt.xlabel('Total Steps')
    plt.ylabel('Calories')
    plt.title('💪 Steps vs Calories')
    plt.grid(True, alpha=0.3)
    
    # Weekly patterns
    plt.subplot(2, 2, 4)
    data['Weekday'] = data['Date'].dt.day_name()
    weekday_steps = data.groupby('Weekday')['TotalSteps'].mean().reindex([
        'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'
    ])
    weekday_steps.plot(kind='bar', color='orange')
    plt.title('📅 Weekly Activity Patterns')
    plt.ylabel('Average Steps')
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()
    
    return fig

def meditation_insights(data):
    """Generate insights for meditation app integration"""
    
    print("\n🧘 Meditation App Insights")
    print("=" * 40)
    
    # Stress indicators (high sedentary, low activity)
    data['StressScore'] = (data['SedentaryMinutes'] / 60) / (data['TotalActiveMinutes'] + 1) * 10
    high_stress = data[data['StressScore'] > data['StressScore'].quantile(0.75)]
    
    print(f"📊 High Stress Days: {len(high_stress)} ({len(high_stress)/len(data)*100:.1f}%)")
    print(f"   • Avg Sedentary Hours: {high_stress['SedentaryMinutes'].mean()/60:.1f}")
    print(f"   • Avg Active Minutes: {high_stress['TotalActiveMinutes'].mean():.1f}")
    
    # Recovery recommendations
    print(f"\n💡 ZenGlow Recommendations:")
    print(f"   • Users with >12h sedentary time need meditation breaks")
    print(f"   • Low activity days (<20 min) benefit from gentle movement meditations")
    print(f"   • Weekend patterns suggest stress relief sessions needed")
    
    # Generate meditation timing suggestions
    weekend_data = data[data['Date'].dt.weekday >= 5]
    weekday_data = data[data['Date'].dt.weekday < 5]
    
    print(f"\n⏰ Optimal Meditation Times:")
    print(f"   • Weekdays: After work hours (high sedentary)")
    print(f"   • Weekends: Morning energizing sessions")
    print(f"   • Low activity days: Gentle movement meditations")

def main():
    """Main analysis pipeline"""
    
    print("🌟 ZenGlow Fitbit Wellness Analysis")
    print("==================================")
    
    # Load data
    data = load_fitbit_data()
    print("\n📋 Data Sample:")
    print(data.head())
    
    # Analyze patterns
    data = analyze_wellness_patterns(data)
    
    # Create visualizations
    try:
        create_wellness_visualizations(data)
    except Exception as e:
        print(f"⚠️  Visualization error: {e}")
    
    # Generate meditation insights
    meditation_insights(data)
    
    print("\n✅ Analysis complete! Ready for ZenGlow integration.")

if __name__ == "__main__":
    main()
