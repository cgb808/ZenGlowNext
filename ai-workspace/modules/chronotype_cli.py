#!/usr/bin/env python3
"""
Mock CLI for Chronotype Detection

Generates 30 days of random sleep data and demonstrates chronotype detection.
This serves as a testing interface for the chronotype detection module.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
import sys
import os

# Add the modules directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from personalization.chronotype import detect_chronotype, ChronoType


def generate_mock_sleep_data(child_id: str, days: int = 30, chronotype_bias: str = None) -> pd.DataFrame:
    """
    Generate mock sleep data for testing chronotype detection.
    
    Args:
        child_id: Child identifier
        days: Number of days to simulate
        chronotype_bias: Optional bias toward specific chronotype for testing
        
    Returns:
        DataFrame with sleep data
    """
    print(f"🔧 Generating {days} days of mock sleep data for {child_id}")
    if chronotype_bias:
        print(f"   Bias: {chronotype_bias}")
    
    np.random.seed(hash(child_id) % 2**32)  # Consistent seed per child
    
    records = []
    base_date = datetime.now() - timedelta(days=days)
    
    for day in range(days):
        current_date = base_date + timedelta(days=day)
        
        # Generate sleep and wake events based on bias
        if chronotype_bias == ChronoType.EARLY_BIRD.value:
            # Early bird: sleep around 21-22h, wake around 5-7h
            sleep_hour = np.random.normal(21.5, 1.0)
            wake_hour = np.random.normal(6.0, 0.8)
            sleep_duration = np.random.normal(8.5, 1.0)
        elif chronotype_bias == ChronoType.NIGHT_OWL.value:
            # Night owl: sleep around 23-1h, wake around 8-10h
            sleep_hour = np.random.normal(23.5, 1.2)
            wake_hour = np.random.normal(9.0, 1.0)
            sleep_duration = np.random.normal(8.0, 1.2)
        else:
            # Intermediate or random: mixed patterns
            if np.random.random() < 0.3:  # 30% early pattern
                sleep_hour = np.random.normal(21.5, 1.0)
                wake_hour = np.random.normal(6.5, 1.0)
            elif np.random.random() < 0.6:  # 30% late pattern  
                sleep_hour = np.random.normal(23.0, 1.5)
                wake_hour = np.random.normal(8.5, 1.2)
            else:  # 40% intermediate
                sleep_hour = np.random.normal(22.2, 1.8)
                wake_hour = np.random.normal(7.5, 1.5)
            sleep_duration = np.random.normal(8.2, 1.3)
        
        # Normalize hours and duration
        sleep_hour = max(0, min(23, sleep_hour))
        wake_hour = max(0, min(23, wake_hour))
        sleep_duration = max(4, min(12, sleep_duration))
        
        # Add sleep event
        records.append({
            'hour': round(sleep_hour),
            'sleep_duration': round(sleep_duration, 1),
            'sleep_state': 'sleep',
            'timestamp': current_date.replace(hour=int(sleep_hour), minute=0)
        })
        
        # Add wake event
        records.append({
            'hour': round(wake_hour),
            'sleep_duration': round(sleep_duration, 1),
            'sleep_state': 'wake',
            'timestamp': (current_date + timedelta(days=1)).replace(hour=int(wake_hour), minute=0)
        })
        
        # Add some random activity hours (for noise)
        if np.random.random() < 0.3:
            activity_hour = np.random.randint(12, 20)
            records.append({
                'hour': activity_hour,
                'sleep_duration': sleep_duration,
                'sleep_state': 'active',
                'timestamp': current_date.replace(hour=activity_hour, minute=0)
            })
    
    df = pd.DataFrame(records)
    print(f"✅ Generated {len(df)} sleep/wake events")
    return df


def analyze_results(child_id: str, detected_chronotype: str, expected_chronotype: str = None):
    """Analyze and display detection results"""
    
    print(f"\n📋 CHRONOTYPE ANALYSIS RESULTS")
    print(f"   Child ID: {child_id}")
    print(f"   Detected: {detected_chronotype}")
    
    if expected_chronotype:
        print(f"   Expected: {expected_chronotype}")
        correct = detected_chronotype == expected_chronotype
        print(f"   Accuracy: {'✅ CORRECT' if correct else '❌ INCORRECT'}")
    
    # Provide interpretation
    interpretations = {
        ChronoType.EARLY_BIRD.value: "🌅 Early bird - peak energy in morning, prefers early bedtime",
        ChronoType.NIGHT_OWL.value: "🦉 Night owl - peak energy in evening, prefers late bedtime", 
        ChronoType.INTERMEDIATE.value: "⚖️ Intermediate - balanced sleep pattern, flexible timing"
    }
    
    print(f"   Meaning: {interpretations.get(detected_chronotype, 'Unknown chronotype')}")


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description='Chronotype Detection Mock CLI')
    parser.add_argument('--child-id', default='test_child_001', 
                       help='Child ID for analysis (default: test_child_001)')
    parser.add_argument('--days', type=int, default=30,
                       help='Number of days of sleep data to generate (default: 30)')
    parser.add_argument('--bias', choices=[e.value for e in ChronoType],
                       help='Bias mock data toward specific chronotype for testing')
    parser.add_argument('--test-all', action='store_true',
                       help='Test all chronotype biases')
    
    args = parser.parse_args()
    
    print("🌙 ZenGlow Chronotype Detection - Mock CLI")
    print("=" * 50)
    
    if args.test_all:
        # Test all chronotype biases
        for chronotype in ChronoType:
            test_child_id = f"{args.child_id}_{chronotype.value}"
            print(f"\n🧪 Testing {chronotype.value} bias...")
            
            df = generate_mock_sleep_data(test_child_id, args.days, chronotype.value)
            detected = detect_chronotype(test_child_id, df)
            analyze_results(test_child_id, detected, chronotype.value)
            print("-" * 50)
    else:
        # Single test
        df = generate_mock_sleep_data(args.child_id, args.days, args.bias)
        detected = detect_chronotype(args.child_id, df)
        analyze_results(args.child_id, detected, args.bias)
    
    print(f"\n🎯 Chronotype detection complete!")
    print(f"\nTo test specific patterns:")
    print(f"  python chronotype_cli.py --bias early_bird")
    print(f"  python chronotype_cli.py --bias night_owl")
    print(f"  python chronotype_cli.py --bias intermediate")
    print(f"  python chronotype_cli.py --test-all")


if __name__ == '__main__':
    main()