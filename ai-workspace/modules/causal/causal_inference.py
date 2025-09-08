"""
Causal Inference Engine for ZenGlow

This module implements causal analysis to move beyond correlation and determine
true causal effects of interventions on child wellness outcomes.

Purpose:
Move beyond correlation (e.g., "stress rises before tests") to causation 
(e.g., "mindfulness reduces stress by 15%").

Planned Integration:
- Will connect to ZenGlow's Supabase/PostgreSQL database via SQL queries
- Analyze wellness_metrics and school_events tables for causal relationships
- Support real-time causal analysis through API endpoints

Dependencies:
- DoWhy: Microsoft's causal inference library for rigorous analysis
- CausalML: Advanced causal ML methods for personalized treatment effects
- pandas: Data manipulation and analysis
- numpy: Numerical computing support

Author: ZenGlow AI Team
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Union
from datetime import datetime, timedelta

# Guard imports for heavy dependencies - prevents import errors during development
try:
    from dowhy import CausalModel
    DOWHY_AVAILABLE = True
except ImportError:
    DOWHY_AVAILABLE = False
    logging.warning("DoWhy not installed. Using mock analysis mode.")

try:
    import causalml
    CAUSALML_AVAILABLE = True
except ImportError:
    CAUSALML_AVAILABLE = False
    logging.warning("CausalML not installed. Using basic analysis mode.")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _generate_mock_wellness_data(child_id: str, days: int = 30) -> pd.DataFrame:
    """
    Generate mock wellness data for testing causal analysis.
    
    This simulates the data that would come from the database query:
    ```sql
    SELECT
        w.time,
        w.stress_level,
        w.sleep_duration,
        s.event_type AS intervention,
        s.event_time
    FROM wellness_metrics w
    LEFT JOIN school_events s ON
        w.child_id = s.child_id AND
        date_trunc('day', w.time) = date_trunc('day', s.event_time)
    WHERE w.child_id = '{child_id}'
    ORDER BY w.time
    ```
    
    Args:
        child_id: Unique identifier for the child
        days: Number of days of historical data to generate
        
    Returns:
        DataFrame with columns: time, stress_level, sleep_duration, intervention, event_time
    """
    np.random.seed(hash(child_id) % 2**32)  # Consistent data per child
    
    base_date = datetime.now() - timedelta(days=days)
    dates = [base_date + timedelta(days=i) for i in range(days)]
    
    data = []
    for i, date in enumerate(dates):
        # Simulate baseline stress and sleep patterns
        base_stress = 50 + np.random.normal(0, 10)
        base_sleep = 8.0 + np.random.normal(0, 1.0)
        
        # Simulate interventions (mindfulness, stories, etc.) on some days
        has_intervention = np.random.random() < INTERVENTION_PROBABILITY  # 40% chance of intervention
        intervention_type = None
        event_time = None
        
        if has_intervention:
            intervention_type = np.random.choice(['mindfulness', 'breathing', 'story', 'music'])
            event_time = date.replace(hour=19, minute=np.random.randint(0, 60))
            
            # Interventions reduce stress by 10-30%
            stress_reduction = np.random.uniform(MIN_STRESS_REDUCTION, MAX_STRESS_REDUCTION)
            base_stress *= (1 - stress_reduction)
            
            # Interventions slightly improve sleep
            base_sleep += np.random.uniform(0.2, 0.8)
        
        # Add some noise and ensure realistic bounds
        stress_level = max(0, min(100, base_stress + np.random.normal(0, 5)))
        sleep_duration = max(4, min(12, base_sleep))
        
        data.append({
            'time': date,
            'stress_level': round(stress_level, 1),
            'sleep_duration': round(sleep_duration, 1),
            'intervention': intervention_type,
            'event_time': event_time
        })
    
    return pd.DataFrame(data)


def analyze_causal_effect(child_id: str, use_mock_data: bool = True) -> Dict[str, Any]:
    """
    Analyze the causal effect of interventions on child wellness outcomes.
    
    This function implements causal inference to determine whether interventions
    (mindfulness, breathing exercises, stories, etc.) causally reduce stress levels
    and improve wellness outcomes for a specific child.
    
    Database Integration (Planned):
    When use_mock_data=False, this function will execute the following SQL query
    against the ZenGlow Supabase database:
    
    ```sql
    SELECT
        w.time,
        w.stress_level,
        w.sleep_duration,
        s.event_type AS intervention,
        s.event_time
    FROM wellness_metrics w
    LEFT JOIN school_events s ON
        w.child_id = s.child_id AND
        date_trunc('day', w.time) = date_trunc('day', s.event_time)
    WHERE w.child_id = '{child_id}'
    ORDER BY w.time
    ```
    
    Causal Analysis Method:
    1. Load historical intervention and outcome data
    2. Define causal model with treatment (intervention) and outcome (stress_level)
    3. Identify confounding variables (sleep_duration, time trends)
    4. Use DoWhy's backdoor criterion and propensity score methods
    5. Estimate average treatment effect (ATE)
    
    Args:
        child_id: Unique identifier for the child to analyze
        use_mock_data: If True, uses generated mock data; if False, queries database
        
    Returns:
        Dictionary containing:
        - child_id: The analyzed child's ID
        - causal_effect: Estimated causal effect (negative = stress reduction)
        - confidence_interval: 95% confidence interval for the effect
        - interpretation: Human-readable interpretation
        - sample_size: Number of observations analyzed
        - method_used: Analysis method (mock, dowhy, or fallback)
        - significant: Whether effect is statistically significant
        
    Raises:
        ValueError: If child_id is invalid or no data available
        ConnectionError: If database connection fails (when use_mock_data=False)
    """
    logger.info(f"Starting causal analysis for child {child_id}")
    
    if not child_id or not isinstance(child_id, str):
        raise ValueError("child_id must be a non-empty string")
    
    try:
        # Step 1: Load data (mock for now, will be database query later)
        if use_mock_data:
            logger.info("Using mock data for analysis")
            df = _generate_mock_wellness_data(child_id)
        else:
            # TODO: Implement database query when DB integration is ready
            # df = pd.read_sql(query, db.engine)
            raise NotImplementedError(
                "Database integration not yet implemented. Use use_mock_data=True"
            )
        
        if df.empty:
            raise ValueError(f"No data available for child {child_id}")
        
        # Step 2: Prepare data for causal analysis
        # Create binary treatment variable (0 = no intervention, 1 = intervention)
        df['treatment'] = (df['intervention'].notna()).astype(int)
        
        # Remove rows with missing stress levels
        df = df.dropna(subset=['stress_level'])
        
        if len(df) < 10:
            logger.warning(f"Limited data for child {child_id}: only {len(df)} observations")
        
        # Step 3: Perform causal analysis
        if DOWHY_AVAILABLE and len(df) >= 10:
            logger.info("Using DoWhy for rigorous causal analysis")
            result = _analyze_with_dowhy(df, child_id)
        else:
            logger.info("Using fallback statistical analysis")
            result = _analyze_with_fallback(df, child_id)
        
        logger.info(f"Causal analysis completed for child {child_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error in causal analysis for child {child_id}: {str(e)}")
        raise


def _analyze_with_dowhy(df: pd.DataFrame, child_id: str) -> Dict[str, Any]:
    """
    Perform causal analysis using DoWhy library.
    
    This implements the full causal inference pipeline with proper
    identification and estimation of causal effects.
    """
    try:
        # Define causal model
        model = CausalModel(
            data=df,
            treatment='treatment',
            outcome='stress_level',
            common_causes=['sleep_duration']  # Confounding variables
        )
        
        # Identify causal effect using backdoor criterion
        identified_estimand = model.identify_effect()
        
        # Estimate causal effect using propensity score stratification
        estimate = model.estimate_effect(
            identified_estimand,
            method_name="backdoor.propensity_score_stratification"
        )
        
        # Calculate confidence interval (approximate)
        effect_value = estimate.value
        std_error = abs(effect_value) * STD_ERROR_APPROX_FACTOR  # See STD_ERROR_APPROX_FACTOR documentation above
        ci_lower = effect_value - 1.96 * std_error
        ci_upper = effect_value + 1.96 * std_error
        
        # Determine statistical significance
        ci_lower = effect_value - CRITICAL_VALUE_95 * std_error
        ci_upper = effect_value + CRITICAL_VALUE_95 * std_error
        
        # Determine statistical significance
        significant = abs(effect_value) > CRITICAL_VALUE_95 * std_error
        
        # Generate interpretation
        if effect_value < -1:
            interpretation = f"Interventions significantly reduce stress by {abs(effect_value):.1f} points"
        elif effect_value < 0:
            interpretation = f"Interventions show minor stress reduction of {abs(effect_value):.1f} points"
        elif effect_value > 1:
            interpretation = f"Interventions may increase stress by {effect_value:.1f} points"
        else:
            interpretation = "No significant causal effect detected"
        
        return {
            'child_id': child_id,
            'causal_effect': round(effect_value, 3),
            'confidence_interval': [round(ci_lower, 3), round(ci_upper, 3)],
            'interpretation': interpretation,
            'sample_size': len(df),
            'method_used': 'dowhy',
            'significant': significant
        }
        
    except Exception as e:
        logger.warning(f"DoWhy analysis failed: {str(e)}. Falling back to simple analysis.")
        return _analyze_with_fallback(df, child_id)


def _analyze_with_fallback(df: pd.DataFrame, child_id: str) -> Dict[str, Any]:
    """
    Fallback causal analysis using simple statistical comparison.
    
    When DoWhy is not available, this provides a basic difference-in-means
    estimate of the causal effect.
    """
    # Simple difference in means between intervention and non-intervention days
    intervention_stress = df[df['treatment'] == 1]['stress_level'].mean()
    control_stress = df[df['treatment'] == 0]['stress_level'].mean()
    
    if pd.isna(intervention_stress) or pd.isna(control_stress):
        effect_value = 0.0
        significant = False
        interpretation = "Insufficient data for analysis"
    else:
        effect_value = intervention_stress - control_stress
        
        # Simple significance test (assuming equal variances)
        intervention_std = df[df['treatment'] == 1]['stress_level'].std()
        control_std = df[df['treatment'] == 0]['stress_level'].std()
        n_intervention = len(df[df['treatment'] == 1])
        n_control = len(df[df['treatment'] == 0])
        
        if n_intervention > 1 and n_control > 1:
            pooled_std = np.sqrt(((n_intervention - 1) * intervention_std**2 + 
                                (n_control - 1) * control_std**2) / 
                               (n_intervention + n_control - 2))
            se = pooled_std * np.sqrt(1/n_intervention + 1/n_control)
            t_stat = abs(effect_value) / se if se > 0 else 0
            significant = t_stat > 1.96
        else:
            significant = False
        
        # Generate interpretation
        if effect_value < -2:
            interpretation = f"Interventions reduce stress by {abs(effect_value):.1f} points (simple analysis)"
        elif effect_value < 0:
            interpretation = f"Interventions show minor stress reduction of {abs(effect_value):.1f} points"
        elif effect_value > 2:
            interpretation = f"Interventions may increase stress by {effect_value:.1f} points"
        else:
            interpretation = "No clear causal effect detected (simple analysis)"
    
    # Approximate confidence interval
    std_error = abs(effect_value) * STD_ERROR_SCALING_FACTOR if effect_value != 0 else STD_ERROR_FALLBACK_VALUE
    ci_lower = float(effect_value - 1.96 * std_error)
    ci_upper = float(effect_value + 1.96 * std_error)
    
    return {
        'child_id': child_id,
        'causal_effect': float(round(effect_value, 3)),
        'confidence_interval': [round(ci_lower, 3), round(ci_upper, 3)],
        'interpretation': interpretation,
        'sample_size': int(len(df)),
        'method_used': 'fallback',
        'significant': bool(significant)
    }


def main():
    """
    CLI entrypoint for running sample causal analysis.
    
    This demonstrates the causal inference capabilities with mock data
    for multiple sample children.
    """
    print("=== ZenGlow Causal Inference Engine ===")
    print("Analyzing intervention effectiveness on child wellness outcomes\n")
    
    # Sample children for demonstration
    sample_children = ['child_001', 'child_002', 'child_003']
    
    for child_id in sample_children:
        print(f"Analyzing child: {child_id}")
        print("-" * 40)
        
        try:
            result = analyze_causal_effect(child_id)
            
            print(f"Sample Size: {result['sample_size']} observations")
            print(f"Analysis Method: {result['method_used']}")
            print(f"Causal Effect: {result['causal_effect']}")
            print(f"95% CI: {result['confidence_interval']}")
            print(f"Significant: {result['significant']}")
            print(f"Interpretation: {result['interpretation']}")
            
        except Exception as e:
            print(f"Error analyzing {child_id}: {str(e)}")
        
        print("\n")
    
    print("=== Analysis Complete ===")
    print("\nNext Steps:")
    print("1. Install DoWhy for rigorous causal analysis: pip install dowhy")
    print("2. Install CausalML for advanced methods: pip install causalml")
    print("3. Integrate with ZenGlow database for real data")
    print("4. Add to Flask API endpoints for real-time analysis")


if __name__ == "__main__":
    main()