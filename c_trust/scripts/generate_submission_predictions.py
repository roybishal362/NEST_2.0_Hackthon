"""
Generate Submission Predictions CSV
====================================
Generates CSV file with predictions for all 23 NEST studies for submission.

Output Format:
study_id,dqi_score,risk_level,risk_score,confidence,agent_signals,recommendation

Usage:
    python scripts/generate_submission_predictions.py
"""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core import get_logger

logger = get_logger(__name__)


def generate_agent_signals_summary(dimension_scores) -> str:
    """
    Generate agent signals summary from dimension scores.
    
    Handles both old (list) and new (dict) structures.
    
    Args:
        dimension_scores: Dictionary or list of dimension scores
    
    Returns:
        Comma-separated string of dimension:level pairs
    """
    signals = []
    
    # Handle both old (list) and new (dict) structures
    if isinstance(dimension_scores, list):
        # Old structure: list of {dimension, raw_score, ...}
        for dim_data in dimension_scores:
            if isinstance(dim_data, dict):
                dimension = dim_data.get("dimension", "unknown")
                score = dim_data.get("raw_score", 0)
                
                # Convert score to risk level
                if score >= 85:
                    level = "low"
                elif score >= 65:
                    level = "medium"
                elif score >= 40:
                    level = "high"
                else:
                    level = "critical"
                
                signals.append(f"{dimension}:{level}")
    
    elif isinstance(dimension_scores, dict):
        # New structure: dict with dimension names as keys
        for dimension, data in dimension_scores.items():
            if isinstance(data, dict):
                score = data.get("score", 0)
                
                # Convert score to risk level
                if score >= 85:
                    level = "low"
                elif score >= 65:
                    level = "medium"
                elif score >= 40:
                    level = "high"
                else:
                    level = "critical"
                
                signals.append(f"{dimension}:{level}")
    
    return ",".join(signals) if signals else "no_signals"


def generate_recommendation(dqi_score: float, risk_level: str, confidence: float) -> str:
    """
    Generate recommendation based on DQI score, risk level, and confidence.
    
    Args:
        dqi_score: DQI score (0-100)
        risk_level: Risk level (GREEN, AMBER, ORANGE, RED)
        confidence: Confidence score (0-1)
    
    Returns:
        Recommendation string
    """
    if risk_level == "RED" or dqi_score < 40:
        return "Immediate attention required - Critical data quality issues"
    elif risk_level == "ORANGE" or dqi_score < 65:
        return "Significant data quality issues - Review and remediation needed"
    elif risk_level == "AMBER" or dqi_score < 85:
        return "Minor data quality issues - Monitor and address"
    else:
        return "Data quality acceptable - Continue monitoring"


def calculate_risk_score(dqi_score: float) -> float:
    """
    Calculate risk score from DQI score.
    Risk score is inverse of DQI score (0-100 scale).
    
    Args:
        dqi_score: DQI score (0-100)
    
    Returns:
        Risk score (0-100)
    """
    return 100.0 - dqi_score


def main():
    """Generate submission predictions CSV"""
    logger.info("Starting prediction CSV generation")
    
    # Load data cache
    cache_file = Path("data_cache.json")
    if not cache_file.exists():
        logger.error("data_cache.json not found. Run analysis pipeline first.")
        print("ERROR: data_cache.json not found")
        print("Please run the analysis pipeline first:")
        print("  python scripts/run_phase5_simple_validation.py")
        return 1
    
    try:
        with open(cache_file, "r") as f:
            data = json.load(f)
        
        logger.info(f"Loaded data for {len(data)} studies")
        
        # Create submission directory if it doesn't exist
        submission_dir = Path("submission")
        submission_dir.mkdir(exist_ok=True)
        
        # Generate CSV
        output_file = submission_dir / "predictions.csv"
        
        with open(output_file, "w", newline="") as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                "study_id",
                "dqi_score",
                "risk_level",
                "risk_score",
                "confidence",
                "agent_signals",
                "recommendation"
            ])
            
            # Data rows
            for study_id in sorted(data.keys()):
                study_data = data[study_id]
                
                # Extract data
                dqi_score = study_data.get("overall_score", 50.0)
                risk_level = study_data.get("risk_level", "UNKNOWN")
                dimension_scores = study_data.get("dimension_scores", {})
                
                # Calculate derived values
                risk_score = calculate_risk_score(dqi_score)
                
                # Confidence: Use average of dimension confidences if available
                confidences = []
                
                if isinstance(dimension_scores, list):
                    # Old structure: no confidence data, use default
                    confidence = 0.75
                elif isinstance(dimension_scores, dict):
                    # New structure: extract confidence from each dimension
                    for dim_data in dimension_scores.values():
                        if isinstance(dim_data, dict):
                            conf = dim_data.get("confidence", 0.0)
                            if conf > 0:
                                confidences.append(conf)
                    
                    confidence = sum(confidences) / len(confidences) if confidences else 0.5
                else:
                    confidence = 0.5
                
                # Generate agent signals summary
                agent_signals = generate_agent_signals_summary(dimension_scores)
                
                # Generate recommendation
                recommendation = generate_recommendation(dqi_score, risk_level, confidence)
                
                # Write row
                writer.writerow([
                    study_id,
                    f"{dqi_score:.1f}",
                    risk_level,
                    f"{risk_score:.1f}",
                    f"{confidence:.2f}",
                    agent_signals,
                    recommendation
                ])
                
                logger.debug(
                    f"{study_id}: DQI={dqi_score:.1f}, Risk={risk_level}, "
                    f"Confidence={confidence:.2f}"
                )
        
        logger.info(f"Prediction CSV generated: {output_file}")
        logger.info(f"Total studies: {len(data)}")
        
        print(f"\n✓ Prediction CSV generated successfully!")
        print(f"  File: {output_file}")
        print(f"  Studies: {len(data)}")
        print(f"\nSummary:")
        
        # Print summary statistics
        risk_counts = {}
        for study_data in data.values():
            risk_level = study_data.get("risk_level", "UNKNOWN")
            risk_counts[risk_level] = risk_counts.get(risk_level, 0) + 1
        
        for risk_level in ["GREEN", "AMBER", "ORANGE", "RED", "UNKNOWN"]:
            count = risk_counts.get(risk_level, 0)
            if count > 0:
                print(f"  {risk_level}: {count} studies")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error generating prediction CSV: {e}", exc_info=True)
        print(f"\nERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
