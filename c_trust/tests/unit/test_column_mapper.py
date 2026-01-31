"""
Unit Tests for FlexibleColumnMapper
====================================

Tests the flexible column mapping functionality that handles NEST data variations.

Author: C-TRUST Team
Date: 2025
"""

import pytest
import pandas as pd
from src.data.column_mapper import FlexibleColumnMapper


class TestFlexibleColumnMapper:
    """Test suite for FlexibleColumnMapper class."""
    
    @pytest.fixture
    def mapper(self):
        """Create a FlexibleColumnMapper instance for testing."""
        return FlexibleColumnMapper()
    
    @pytest.fixture
    def sample_df(self):
        """Create a sample DataFrame with various column name formats."""
        return pd.DataFrame({
            'Visit Name': [1, 2, 3],
            'Form Type': ['A', 'B', 'C'],
            'Site ID': [101, 102, 103],
            'CPID': ['P001', 'P002', 'P003'],
            'Query Status': ['Open', 'Closed', 'Open'],
            'Visit Date': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'Severity': ['High', 'Low', 'Medium']
        })
    
    # Test 1: Exact Match (Case-Insensitive)
    def test_exact_match_case_insensitive(self, mapper, sample_df):
        """Test that exact match works with case-insensitive comparison."""
        # Test with exact match parameter
        result = mapper.find_column(sample_df, 'visit', exact_match='Visit Name')
        assert result == 'Visit Name'
        
        # Test with different case
        result = mapper.find_column(sample_df, 'visit', exact_match='visit name')
        assert result == 'Visit Name'
        
        result = mapper.find_column(sample_df, 'visit', exact_match='VISIT NAME')
        assert result == 'Visit Name'
    
    # Test 2: Semantic Match from Mappings
    def test_semantic_match_from_mappings(self, mapper, sample_df):
        """Test that semantic matching works using predefined mappings."""
        # Visit column
        result = mapper.find_column(sample_df, 'visit')
        assert result == 'Visit Name'
        
        # Form column
        result = mapper.find_column(sample_df, 'form')
        assert result == 'Form Type'
        
        # Site column
        result = mapper.find_column(sample_df, 'site')
        assert result == 'Site ID'
        
        # Patient column
        result = mapper.find_column(sample_df, 'patient')
        assert result == 'CPID'
        
        # Status column
        result = mapper.find_column(sample_df, 'status')
        assert result == 'Query Status'
        
        # Date column
        result = mapper.find_column(sample_df, 'date')
        assert result == 'Visit Date'
        
        # Severity column
        result = mapper.find_column(sample_df, 'severity')
        assert result == 'Severity'
    
    # Test 3: Fuzzy Match with 80% Threshold
    def test_fuzzy_match_similar_names(self, mapper):
        """Test that fuzzy matching works for similar column names."""
        # Test with slight variations
        df = pd.DataFrame({
            'Visit_Name': [1, 2, 3],  # Underscore instead of space
            'FormType': ['A', 'B', 'C'],  # No space
            'Site_ID': [101, 102, 103],  # Underscore
            'PatientID': ['P001', 'P002', 'P003'],  # Different name but similar
        })
        
        # These should match with fuzzy matching
        assert mapper.find_column(df, 'visit') == 'Visit_Name'
        assert mapper.find_column(df, 'form') == 'FormType'
        assert mapper.find_column(df, 'site') == 'Site_ID'
        assert mapper.find_column(df, 'patient') == 'PatientID'
    
    # Test 4: No Match Found
    def test_no_match_found(self, mapper, sample_df):
        """Test that None is returned when no match is found."""
        result = mapper.find_column(sample_df, 'nonexistent_column')
        assert result is None
        
        # Test with a semantic name that doesn't exist
        result = mapper.find_column(sample_df, 'unknown_semantic_name')
        assert result is None
    
    # Test 5: Empty DataFrame
    def test_empty_dataframe(self, mapper):
        """Test that None is returned for empty DataFrame."""
        empty_df = pd.DataFrame()
        result = mapper.find_column(empty_df, 'visit')
        assert result is None
    
    # Test 6: None DataFrame
    def test_none_dataframe(self, mapper):
        """Test that None is returned for None DataFrame."""
        result = mapper.find_column(None, 'visit')
        assert result is None
    
    # Test 7: Find Multiple Columns
    def test_find_multiple_columns(self, mapper, sample_df):
        """Test finding multiple columns at once."""
        results = mapper.find_columns(sample_df, ['visit', 'form', 'patient'])
        
        assert results['visit'] == 'Visit Name'
        assert results['form'] == 'Form Type'
        assert results['patient'] == 'CPID'
    
    # Test 8: Find Multiple Columns with Some Missing
    def test_find_multiple_columns_partial(self, mapper, sample_df):
        """Test finding multiple columns when some don't exist."""
        results = mapper.find_columns(
            sample_df,
            ['visit', 'form', 'nonexistent']
        )
        
        assert results['visit'] == 'Visit Name'
        assert results['form'] == 'Form Type'
        assert results['nonexistent'] is None
    
    # Test 9: Add New Mapping
    def test_add_new_mapping(self, mapper):
        """Test adding a new semantic mapping."""
        # Add a new mapping
        mapper.add_mapping('custom_field', ['Custom Field', 'CUSTOM', 'custom'])
        
        # Test that it works
        df = pd.DataFrame({'Custom Field': [1, 2, 3]})
        result = mapper.find_column(df, 'custom_field')
        assert result == 'Custom Field'
    
    # Test 10: Extend Existing Mapping
    def test_extend_existing_mapping(self, mapper):
        """Test extending an existing semantic mapping."""
        # Get original mapping count
        original_info = mapper.get_mapping_info('visit')
        original_count = original_info['count']
        
        # Add new variations
        mapper.add_mapping('visit', ['Visit_New', 'VISIT_NEW'])
        
        # Check that mapping was extended
        new_info = mapper.get_mapping_info('visit')
        assert new_info['count'] == original_count + 2
        
        # Test that new variations work
        df = pd.DataFrame({'Visit_New': [1, 2, 3]})
        result = mapper.find_column(df, 'visit')
        assert result == 'Visit_New'
    
    # Test 11: Get Mapping Info
    def test_get_mapping_info(self, mapper):
        """Test getting information about a semantic mapping."""
        info = mapper.get_mapping_info('visit')
        
        assert info['semantic_name'] == 'visit'
        assert info['exists'] is True
        assert info['count'] > 0
        assert isinstance(info['possible_names'], list)
        assert 'Visit' in info['possible_names']
    
    # Test 12: Get Mapping Info for Nonexistent Mapping
    def test_get_mapping_info_nonexistent(self, mapper):
        """Test getting info for a nonexistent mapping."""
        info = mapper.get_mapping_info('nonexistent')
        
        assert info['semantic_name'] == 'nonexistent'
        assert info['exists'] is False
        assert info['count'] == 0
        assert info['possible_names'] == []
    
    # Test 13: Get All Mappings
    def test_get_all_mappings(self, mapper):
        """Test getting all semantic mappings."""
        all_mappings = mapper.get_all_mappings()
        
        assert isinstance(all_mappings, dict)
        assert 'visit' in all_mappings
        assert 'form' in all_mappings
        assert 'patient' in all_mappings
        assert len(all_mappings) > 0
    
    # Test 14: Case Variations
    def test_case_variations(self, mapper):
        """Test that column matching works with various case formats."""
        df = pd.DataFrame({
            'VISIT': [1, 2, 3],
            'visit': [4, 5, 6],
            'Visit': [7, 8, 9]
        })
        
        # Should find one of them (first match)
        result = mapper.find_column(df, 'visit')
        assert result in ['VISIT', 'visit', 'Visit']
    
    # Test 15: Whitespace Handling
    def test_whitespace_handling(self, mapper):
        """Test that whitespace is handled correctly."""
        df = pd.DataFrame({
            '  Visit Name  ': [1, 2, 3],  # Extra whitespace
            'Form Type': ['A', 'B', 'C']
        })
        
        # Should still find the column despite whitespace
        result = mapper.find_column(df, 'visit')
        assert result == '  Visit Name  '
    
    # Test 16: Special Characters in Column Names
    def test_special_characters(self, mapper):
        """Test handling of special characters in column names."""
        df = pd.DataFrame({
            'Visit Name (Source: EDC)': [1, 2, 3],
            '# Days Since Open': [10, 20, 30]
        })
        
        # Should find columns with special characters
        result = mapper.find_column(df, 'visit')
        assert result == 'Visit Name (Source: EDC)'
        
        result = mapper.find_column(df, 'days_open')
        assert result == '# Days Since Open'
    
    # Test 17: Query Column Variations
    def test_query_column_variations(self, mapper):
        """Test finding query-related columns with various names."""
        df = pd.DataFrame({
            'Total Open issue Count per subject': [5, 10, 15],
            'Open Queries': [2, 3, 4]
        })
        
        # Should find query columns
        result = mapper.find_column(df, 'query')
        assert result in ['Total Open issue Count per subject', 'Open Queries']
    
    # Test 18: Action Owner Column
    def test_action_owner_column(self, mapper):
        """Test finding action owner column."""
        df = pd.DataFrame({
            'Action Owner': ['Site', 'CRA', 'DM'],
            'Other Column': [1, 2, 3]
        })
        
        result = mapper.find_column(df, 'action_owner')
        assert result == 'Action Owner'
    
    # Test 19: Days Open Column
    def test_days_open_column(self, mapper):
        """Test finding days open/outstanding columns."""
        df = pd.DataFrame({
            '# Days Since Open': [10, 20, 30],
            'Other Column': [1, 2, 3]
        })
        
        result = mapper.find_column(df, 'days_open')
        assert result == '# Days Since Open'
        
        # Test with alternative name
        df2 = pd.DataFrame({
            '# Days Outstanding': [5, 10, 15]
        })
        
        result2 = mapper.find_column(df2, 'days_open')
        assert result2 == '# Days Outstanding'
    
    # Test 20: Fuzzy Match Threshold
    def test_fuzzy_match_threshold(self, mapper):
        """Test that fuzzy matching respects the 80% threshold."""
        df = pd.DataFrame({
            'Vis': [1, 2, 3],  # Too different from 'Visit' (< 80% similar)
            'Visitor': [4, 5, 6],  # Similar but not exact
            'Visit Name': [7, 8, 9]  # Should match
        })
        
        # Should find 'Visit Name' as it's in the mappings
        result = mapper.find_column(df, 'visit')
        assert result == 'Visit Name'
    
    # Test 21: Multiple Possible Matches
    def test_multiple_possible_matches(self, mapper):
        """Test behavior when multiple columns could match."""
        df = pd.DataFrame({
            'Visit': [1, 2, 3],
            'Visit Name': [4, 5, 6],
            'Visit Date': [7, 8, 9]
        })
        
        # Should find one of them (first exact match from mappings)
        result = mapper.find_column(df, 'visit')
        assert result in ['Visit', 'Visit Name', 'Visit Date']
    
    # Test 22: Real NEST Column Names
    def test_real_nest_column_names(self, mapper):
        """Test with actual column names from NEST 2.0 files."""
        # Simulate real NEST EDC Metrics columns
        df = pd.DataFrame({
            'Subject ID': ['S001', 'S002'],
            'Total Open issue Count per subject': [5, 10],
            'Forms Entered': [20, 25],
            'Expected Visits': [10, 12],
            'Site ID': [101, 102]
        })
        
        assert mapper.find_column(df, 'patient') == 'Subject ID'
        assert mapper.find_column(df, 'query') == 'Total Open issue Count per subject'
        assert mapper.find_column(df, 'form') == 'Forms Entered'
        assert mapper.find_column(df, 'visit') == 'Expected Visits'
        assert mapper.find_column(df, 'site') == 'Site ID'
    
    # Test 23: Completion Column
    def test_completion_column(self, mapper):
        """Test finding completion-related columns."""
        df = pd.DataFrame({
            'Completion Status': ['Complete', 'Incomplete'],
            'Other': [1, 2]
        })
        
        result = mapper.find_column(df, 'completion')
        assert result == 'Completion Status'


# Run tests with pytest
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
