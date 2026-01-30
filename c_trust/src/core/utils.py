"""
Core utility functions for C-TRUST system
"""
import uuid
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import pandas as pd


def generate_id(prefix: str = "") -> str:
    """Generate unique identifier with optional prefix"""
    unique_id = str(uuid.uuid4())
    return f"{prefix}_{unique_id}" if prefix else unique_id


def generate_snapshot_id(study_id: str, timestamp: Optional[datetime] = None) -> str:
    """Generate snapshot ID based on study and timestamp"""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    
    timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
    return f"snapshot_{study_id}_{timestamp_str}"


def calculate_hash(data: Union[str, Dict, List]) -> str:
    """Calculate SHA-256 hash of data"""
    if isinstance(data, (dict, list)):
        data_str = json.dumps(data, sort_keys=True)
    else:
        data_str = str(data)
    
    return hashlib.sha256(data_str.encode()).hexdigest()


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning default if denominator is zero"""
    if denominator == 0:
        return default
    return numerator / denominator


def calculate_percentage(part: float, total: float) -> float:
    """Calculate percentage with safe division"""
    return safe_divide(part, total, 0.0) * 100


def clamp(value: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
    """Clamp a value between min and max bounds"""
    return max(min_val, min(max_val, value))


def normalize_score(value: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
    """Normalize score to 0-100 range"""
    if value < min_val:
        return 0.0
    if value > max_val:
        return 100.0
    return ((value - min_val) / (max_val - min_val)) * 100


def weighted_average(values: List[float], weights: List[float]) -> float:
    """Calculate weighted average of values"""
    if len(values) != len(weights):
        raise ValueError("Values and weights must have same length")
    
    if not values:
        return 0.0
    
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0
    
    weighted_sum = sum(v * w for v, w in zip(values, weights))
    return weighted_sum / total_weight


def classify_dqi_band(score: float) -> str:
    """Classify DQI score into bands"""
    if score >= 85:
        return "GREEN"
    elif score >= 65:
        return "AMBER"
    elif score >= 40:
        return "ORANGE"
    else:
        return "RED"


def format_confidence(confidence: float) -> str:
    """Format confidence score as percentage string"""
    return f"{confidence * 100:.1f}%"


def format_timestamp(timestamp: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format timestamp as string"""
    return timestamp.strftime(format_str)


def parse_study_id(filename: str) -> Optional[str]:
    """Extract study ID from filename"""
    # Pattern: Study X_... or STUDY X_...
    import re
    pattern = r'(?:Study|STUDY)\s*(\d+)_'
    match = re.search(pattern, filename)
    return match.group(1) if match else None


def validate_file_path(file_path: Union[str, Path]) -> bool:
    """Validate that file path exists and is readable"""
    path = Path(file_path)
    return path.exists() and path.is_file()


def ensure_directory(dir_path: Union[str, Path]) -> Path:
    """Ensure directory exists, create if necessary"""
    path = Path(dir_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_excel_safely(file_path: Union[str, Path], sheet_name: Optional[str] = None) -> Optional[pd.DataFrame]:
    """Safely load Excel file, return None if fails"""
    try:
        return pd.read_excel(file_path, sheet_name=sheet_name)
    except Exception as e:
        print(f"Failed to load Excel file {file_path}: {e}")
        return None


def load_csv_safely(file_path: Union[str, Path]) -> Optional[pd.DataFrame]:
    """Safely load CSV file, return None if fails"""
    try:
        return pd.read_csv(file_path)
    except Exception as e:
        print(f"Failed to load CSV file {file_path}: {e}")
        return None


def calculate_data_delta(prev_data: Dict, curr_data: Dict) -> Dict[str, Any]:
    """Calculate delta between two data snapshots"""
    delta = {
        "added_keys": [],
        "removed_keys": [],
        "changed_values": {},
        "summary": {}
    }
    
    prev_keys = set(prev_data.keys())
    curr_keys = set(curr_data.keys())
    
    delta["added_keys"] = list(curr_keys - prev_keys)
    delta["removed_keys"] = list(prev_keys - curr_keys)
    
    # Check for changed values in common keys
    common_keys = prev_keys & curr_keys
    for key in common_keys:
        if prev_data[key] != curr_data[key]:
            delta["changed_values"][key] = {
                "previous": prev_data[key],
                "current": curr_data[key]
            }
    
    # Summary statistics
    delta["summary"] = {
        "total_changes": len(delta["added_keys"]) + len(delta["removed_keys"]) + len(delta["changed_values"]),
        "added_count": len(delta["added_keys"]),
        "removed_count": len(delta["removed_keys"]),
        "changed_count": len(delta["changed_values"])
    }
    
    return delta


def merge_dictionaries(*dicts: Dict) -> Dict:
    """Merge multiple dictionaries, later ones override earlier ones"""
    result = {}
    for d in dicts:
        if d:
            result.update(d)
    return result


def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """Split list into chunks of specified size"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def flatten_dict(d: Dict, parent_key: str = '', sep: str = '.') -> Dict:
    """Flatten nested dictionary"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


class Timer:
    """Context manager for timing operations"""
    
    def __init__(self, description: str = "Operation"):
        self.description = description
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        print(f"{self.description} completed in {duration:.2f} seconds")
    
    @property
    def duration(self) -> Optional[float]:
        """Get duration in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None