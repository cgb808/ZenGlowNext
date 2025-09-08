#!/usr/bin/env python3
"""
CLI runner for ZenGlow Causal Inference Module

Usage:
    python3 run_causal_analysis.py [child_id]

If no child_id is provided, runs sample analysis for demo children.
"""

import sys
import os

# Add the modules directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))

from causal import analyze_causal_effect


def main():
    if len(sys.argv) > 1:
        child_id = sys.argv[1]
        print(f"=== ZenGlow Causal Analysis for {child_id} ===")
        
        try:
            result = analyze_causal_effect(child_id)
            
            print(f"Child ID: {result['child_id']}")
            print(f"Sample Size: {result['sample_size']} observations")
            print(f"Analysis Method: {result['method_used']}")
            print(f"Causal Effect: {result['causal_effect']}")
            print(f"95% Confidence Interval: {result['confidence_interval']}")
            print(f"Statistically Significant: {result['significant']}")
            print(f"Interpretation: {result['interpretation']}")
            
        except Exception as e:
            print(f"Error analyzing {child_id}: {str(e)}")
    else:
        # Run the full demo
        from causal.causal_inference import main as demo_main
        demo_main()


if __name__ == "__main__":
    main()