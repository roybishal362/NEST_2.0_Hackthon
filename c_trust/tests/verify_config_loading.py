
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parents[1]))

from src.core.config import config_manager
from src.data.ingestion import FileTypeDetector

def verify_integration():
    print("Verifying Config Loading and File Detection Integration...")
    
    # 1. Check Config Loading
    config = config_manager.get_config()
    patterns = config.data_sources.file_patterns
    
    print(f"\nLoaded Patterns (Type: {type(patterns)}):")
    edc_metrics = patterns.get("edc_metrics")
    print(f"EDC Metrics Pattern: {edc_metrics} (Type: {type(edc_metrics)})")
    
    if not isinstance(edc_metrics, list):
        print("❌ FAILED: EDC Metrics pattern should be a list!")
        return False
        
    # 2. Check Detector Compilation
    detector = FileTypeDetector()
    print(f"\nCompiled {len(detector.patterns)} pattern types.")
    
    # 3. Test Detection on specific problematic file
    test_file = "SAE Dashboard_updated.xlsx"
    file_type = detector.detect_file_type(test_file)
    print(f"\nTesting file: '{test_file}'")
    print(f"Detected Type: {file_type}")
    
    if file_type and file_type.value == "sae_dm":
        print("✅ SUCCESS: File detected correctly!")
        return True
    else:
        print(f"❌ FAILED: Expected sae_dm, got {file_type}")
        return False

if __name__ == "__main__":
    success = verify_integration()
    sys.exit(0 if success else 1)
