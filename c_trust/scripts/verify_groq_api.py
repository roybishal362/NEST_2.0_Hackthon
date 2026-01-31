"""
Groq API Verification Script
=============================
Utility script to verify Groq API integration and configuration.

Usage:
    python scripts/verify_groq_api.py
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Load environment variables
load_dotenv(parent_dir / ".env")

from src.intelligence.llm_client import GroqLLMClient


def verify_groq_api():
    """Verify Groq API connection and configuration"""
    print("=" * 60)
    print("C-TRUST Groq API Integration Verification")
    print("=" * 60)
    
    # Initialize client
    client = GroqLLMClient()
    
    # Get status
    status = client.get_status()
    
    print("\n📊 Status Report:")
    print(f"  ✓ API Key Configured: {status['api_key_configured']}")
    print(f"  ✓ Groq Package Available: {status['groq_package_available']}")
    print(f"  ✓ Model: {status['model']}")
    print(f"  ✓ Available: {status['available']}")
    print(f"  ✓ Mock Mode: {status['mock_mode']}")
    
    if status['error']:
        print(f"\n⚠️  Error: {status['error']}")
    
    # Test explanation generation
    print("\n🧪 Testing Explanation Generation...")
    test_signal = {
        "agent_type": "enrollment_agent",
        "risk_level": "medium",
        "confidence": 0.85,
        "evidence": [
            {"description": "Enrollment rate below target by 15%"}
        ],
        "recommended_actions": ["Review recruitment strategy"]
    }
    
    explanation = client.generate_explanation(test_signal)
    print(f"\n📝 Generated Explanation:\n{explanation}\n")
    
    # Test recommendations
    print("🧪 Testing Recommendations Generation...")
    recommendations = client.generate_recommendations([test_signal])
    print(f"\n💡 Generated Recommendations:")
    print(f"  Source: {recommendations['source']}")
    if 'warning' in recommendations:
        print(f"  Warning: {recommendations['warning']}")
    for rec in recommendations['recommendations']:
        print(f"  - {rec}")
    
    print("\n" + "=" * 60)
    if status['available']:
        print("✅ SUCCESS: Groq API is fully operational!")
    else:
        print("⚠️  WARNING: Running in mock mode (template-based responses)")
        print("   To enable AI features:")
        print("   1. Get free API key: https://console.groq.com/keys")
        print("   2. Add to .env: GROQ_API_KEY=your_key_here")
        print("   3. Install package: pip install groq")
        print("   4. Restart application")
    print("=" * 60)


if __name__ == "__main__":
    verify_groq_api()
