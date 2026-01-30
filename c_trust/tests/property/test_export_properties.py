"""
Property-Based Tests for Export Functionality
==============================================
Tests universal properties of export system using Hypothesis.

Phase 4, Task 18: Property-Based Tests for Export
"""

import csv
import time
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck

from src.api.export import (
    generate_csv_export,
    get_export_columns,
    _get_dqi_band
)


# ========================================
# STRATEGIES
# ========================================

@st.composite
def export_data_strategy(draw):
    """Generate valid export data"""
    num_studies = draw(st.integers(min_value=1, max_value=50))
    
    data = []
    for i in range(num_studies):
        study_data = {
            'study_id': f'STUDY_{i:02d}',
            'study_name': f'Study {i}',
            'dqi_score': draw(st.one_of(st.none(), st.floats(min_value=0, max_value=100))),
            'dqi_band': draw(st.sampled_from(['GREEN', 'AMBER', 'ORANGE', 'RED', 'UNKNOWN'])),
            'risk_level': draw(st.sampled_from(['Low', 'Medium', 'High', 'Critical'])),
            'enrollment_actual': draw(st.one_of(st.none(), st.integers(min_value=0, max_value=1000))),
            'enrollment_target': draw(st.one_of(st.none(), st.integers(min_value=0, max_value=1000))),
            'enrollment_rate': draw(st.one_of(st.none(), st.floats(min_value=0, max_value=100))),
        }
        data.append(study_data)
    
    return data


# ========================================
# PROPERTY 1: Export Includes All Required Columns
# ========================================

@given(
    include_agent_signals=st.booleans(),
    include_temporal_metrics=st.booleans()
)
@settings(max_examples=50)
def test_property_export_includes_required_columns(
    include_agent_signals,
    include_temporal_metrics
):
    """
    **Validates: Requirements FR-10**
    
    Property: Export MUST always include core required columns regardless of options
    """
    required_columns = [
        'study_id',
        'study_name',
        'dqi_score',
        'dqi_band',
        'enrollment_actual',
        'enrollment_target',
        'enrollment_rate'
    ]
    
    columns = get_export_columns(
        include_agent_signals=include_agent_signals,
        include_temporal_metrics=include_temporal_metrics
    )
    
    for col in required_columns:
        assert col in columns, f"Required column '{col}' missing from export"


# ========================================
# PROPERTY 2: Export Completes Within Time Limit
# ========================================

@given(data=export_data_strategy())
@settings(max_examples=20, deadline=6000, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_export_completes_within_time_limit(data):
    """
    **Validates: Requirements NFR-4**
    
    Property: Export MUST complete within 5 seconds for up to 50 studies
    """
    filename = "performance_test_export.csv"
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        start_time = time.time()
        
        with patch('src.api.export.EXPORT_DIR', tmp_path):
            result_path = generate_csv_export(data, filename)
        
        elapsed_time = time.time() - start_time
        
        # Allow 5 seconds for export
        assert elapsed_time < 5.0, f"Export took {elapsed_time:.2f}s, should be < 5s"
        assert result_path.exists()


# ========================================
# PROPERTY 3: Export Handles Missing Data Gracefully
# ========================================

@given(data=export_data_strategy())
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_export_handles_missing_data(data):
    """
    **Validates: Requirements FR-10**
    
    Property: Export MUST handle null/missing values without errors
    """
    filename = "missing_data_export.csv"
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Should not raise exception
        with patch('src.api.export.EXPORT_DIR', tmp_path):
            result_path = generate_csv_export(data, filename)
        
        assert result_path.exists()
        
        # Verify CSV is valid
        with open(result_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == len(data)


# ========================================
# PROPERTY 4: DQI Band Classification is Consistent
# ========================================

@given(dqi_score=st.one_of(st.none(), st.floats(min_value=0, max_value=100)))
@settings(max_examples=100)
def test_property_dqi_band_classification_consistent(dqi_score):
    """
    **Validates: Requirements FR-1**
    
    Property: DQI band classification MUST be deterministic and consistent
    """
    band1 = _get_dqi_band(dqi_score)
    band2 = _get_dqi_band(dqi_score)
    
    # Same input should always produce same output
    assert band1 == band2
    
    # Verify band is valid
    valid_bands = ['GREEN', 'AMBER', 'ORANGE', 'RED', 'UNKNOWN']
    assert band1 in valid_bands


# ========================================
# PROPERTY 5: DQI Band Boundaries are Correct
# ========================================

@given(dqi_score=st.floats(min_value=0, max_value=100))
@settings(max_examples=100)
def test_property_dqi_band_boundaries(dqi_score):
    """
    **Validates: Requirements FR-1**
    
    Property: DQI band boundaries MUST be correctly enforced
    """
    band = _get_dqi_band(dqi_score)
    
    if dqi_score >= 85:
        assert band == "GREEN"
    elif dqi_score >= 75:
        assert band == "AMBER"
    elif dqi_score >= 65:
        assert band == "ORANGE"
    else:
        assert band == "RED"


# ========================================
# PROPERTY 6: Export Row Count Matches Input
# ========================================

@given(data=export_data_strategy())
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_export_row_count_matches_input(data):
    """
    **Validates: Requirements FR-10**
    
    Property: Export MUST contain exactly one row per input study
    """
    filename = "row_count_export.csv"
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        with patch('src.api.export.EXPORT_DIR', tmp_path):
            result_path = generate_csv_export(data, filename)
        
        # Count rows in CSV
        with open(result_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == len(data), f"Expected {len(data)} rows, got {len(rows)}"


# ========================================
# PROPERTY 7: Export Preserves Study IDs
# ========================================

@given(data=export_data_strategy())
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_export_preserves_study_ids(data):
    """
    **Validates: Requirements FR-10**
    
    Property: Export MUST preserve all study IDs from input
    """
    filename = "study_id_export.csv"
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        with patch('src.api.export.EXPORT_DIR', tmp_path):
            result_path = generate_csv_export(data, filename)
        
        # Read study IDs from CSV
        with open(result_path, 'r') as f:
            reader = csv.DictReader(f)
            exported_ids = [row['study_id'] for row in reader]
        
        input_ids = [d['study_id'] for d in data]
        
        assert set(exported_ids) == set(input_ids), "Study IDs not preserved in export"


# ========================================
# PROPERTY 8: Column Options Work Correctly
# ========================================

@given(
    include_agent_signals=st.booleans(),
    include_temporal_metrics=st.booleans()
)
@settings(max_examples=20)
def test_property_column_options_work(
    include_agent_signals,
    include_temporal_metrics
):
    """
    **Validates: Requirements FR-10**
    
    Property: Column inclusion options MUST be respected
    """
    columns = get_export_columns(
        include_agent_signals=include_agent_signals,
        include_temporal_metrics=include_temporal_metrics
    )
    
    # Check agent signal columns
    agent_columns = ['safety_risk', 'completeness_risk', 'coding_risk']
    if include_agent_signals:
        for col in agent_columns:
            assert col in columns, f"Agent column '{col}' should be included"
    else:
        for col in agent_columns:
            assert col not in columns, f"Agent column '{col}' should be excluded"
    
    # Check temporal metrics columns
    temporal_columns = ['enrollment_velocity', 'visit_schedule_adherence', 'data_entry_lag_days']
    if include_temporal_metrics:
        for col in temporal_columns:
            assert col in columns, f"Temporal column '{col}' should be included"
    else:
        for col in temporal_columns:
            assert col not in columns, f"Temporal column '{col}' should be excluded"


# ========================================
# PROPERTY 9: Export File is Valid CSV
# ========================================

@given(data=export_data_strategy())
@settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_export_file_is_valid_csv(data):
    """
    **Validates: Requirements FR-10**
    
    Property: Export MUST produce valid CSV that can be parsed
    """
    filename = "valid_csv_export.csv"
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        with patch('src.api.export.EXPORT_DIR', tmp_path):
            result_path = generate_csv_export(data, filename)
        
        # Should be able to parse without errors
        with open(result_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)  # Force parsing
        
        # Verify we got data
        assert len(rows) > 0


# ========================================
# PROPERTY 10: Empty Data Produces Valid Export
# ========================================

def test_property_empty_data_produces_valid_export():
    """
    **Validates: Requirements FR-10**
    
    Property: Export MUST handle empty data gracefully
    """
    filename = "empty_export.csv"
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        with patch('src.api.export.EXPORT_DIR', tmp_path):
            result_path = generate_csv_export([], filename)
        
        assert result_path.exists()
        
        # Should have headers but no data rows
        with open(result_path, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        assert len(rows) == 1  # Only header row


# ========================================
# SUMMARY
# ========================================

"""
Property Test Coverage Summary:
- Property 1: Export includes all required columns (FR-10)
- Property 2: Export completes within 5 seconds (NFR-4)
- Property 3: Export handles missing data gracefully (FR-10)
- Property 4: DQI band classification is consistent (FR-1)
- Property 5: DQI band boundaries are correct (FR-1)
- Property 6: Export row count matches input (FR-10)
- Property 7: Export preserves study IDs (FR-10)
- Property 8: Column options work correctly (FR-10)
- Property 9: Export file is valid CSV (FR-10)
- Property 10: Empty data produces valid export (FR-10)

Total: 10 property-based tests

All properties verify:
✓ Column completeness (FR-10)
✓ Performance requirements (NFR-4)
✓ Data integrity
✓ Error handling
✓ Consistency
✓ Boundary conditions
"""
