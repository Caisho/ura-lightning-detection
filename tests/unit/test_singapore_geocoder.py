"""
Unit tests for Singapore Geocoder class

Tests cover all major functionality including:
- Postal code validation and cleaning
- Geocoding methods (postal code, address, building)
- Smart geocoding with auto-detection
- Batch processing
- Utility methods
- Error handling
"""

import os
import sys
from unittest.mock import Mock, patch, MagicMock
import pytest
import pandas as pd

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from singapore_geocoder import SingaporeGeocoder


class TestSingaporeGeocoderValidation:
    """Test postal code validation and cleaning methods."""
    
    def test_validate_postal_code_valid_codes(self):
        """Test validation of valid Singapore postal codes."""
        geocoder = SingaporeGeocoder(verbose=False)
        
        valid_codes = [
            "238874",
            "018989", 
            "079903",
            "018956",
            "099253",
            "238-874",  # Should still be valid after cleaning
            " 018989 ",  # Should be valid after stripping
            "238 874"   # Should be valid after cleaning
        ]
        
        for code in valid_codes:
            assert geocoder.validate_postal_code(code), f"'{code}' should be valid"
    
    def test_validate_postal_code_invalid_codes(self):
        """Test validation of invalid postal codes."""
        geocoder = SingaporeGeocoder(verbose=False)
        
        invalid_codes = [
            "12345",      # Too short
            "1234567",    # Too long
            "abc123",     # Contains letters
            "23887a",     # Contains letter
            "",           # Empty string
            None,         # None value
            123456,       # Not a string
        ]
        
        for code in invalid_codes:
            assert not geocoder.validate_postal_code(code), f"'{code}' should be invalid"
    
    def test_clean_postal_code_valid(self):
        """Test cleaning of valid postal codes."""
        geocoder = SingaporeGeocoder(verbose=False)
        
        test_cases = [
            ("238874", "238874"),
            ("238-874", "238874"),
            (" 018989 ", "018989"),
            ("238 874", "238874"),
            ("07-99-03", "079903"),
        ]
        
        for input_code, expected in test_cases:
            result = geocoder.clean_postal_code(input_code)
            assert result == expected, f"'{input_code}' should clean to '{expected}', got '{result}'"
    
    def test_clean_postal_code_invalid(self):
        """Test cleaning of invalid postal codes returns None."""
        geocoder = SingaporeGeocoder(verbose=False)
        
        invalid_codes = [
            "12345",      # Too short
            "1234567",    # Too long
            "abc123",     # Contains letters
            "",           # Empty string
            None,         # None value
            123456,       # Not a string
        ]
        
        for code in invalid_codes:
            result = geocoder.clean_postal_code(code)
            assert result is None, f"'{code}' should return None after cleaning"


class TestSingaporeGeocoderCoordinates:
    """Test coordinate validation and utility methods."""
    
    def test_singapore_center(self):
        """Test getting Singapore center coordinates."""
        geocoder = SingaporeGeocoder(verbose=False)
        center = geocoder.get_singapore_center()
        
        assert isinstance(center, tuple)
        assert len(center) == 2
        assert center == (1.3521, 103.8198)
    
    def test_valid_singapore_coordinates(self):
        """Test validation of coordinates within Singapore bounds."""
        geocoder = SingaporeGeocoder(verbose=False)
        
        valid_coords = [
            (1.3521, 103.8198),  # Singapore center
            (1.304167, 103.833611),  # ION Orchard
            (1.283611, 103.859722),  # Marina Bay Sands
            (1.16, 103.59),  # Min bounds
            (1.48, 104.04),  # Max bounds
        ]
        
        for lat, lon in valid_coords:
            assert geocoder.is_valid_singapore_coordinates(lat, lon), \
                f"({lat}, {lon}) should be valid Singapore coordinates"
    
    def test_invalid_singapore_coordinates(self):
        """Test validation of coordinates outside Singapore bounds."""
        geocoder = SingaporeGeocoder(verbose=False)
        
        invalid_coords = [
            (40.7128, -74.0060),  # New York
            (51.5074, -0.1278),   # London
            (1.15, 103.8),        # Below min latitude
            (1.49, 103.8),        # Above max latitude
            (1.35, 103.58),       # Below min longitude
            (1.35, 104.05),       # Above max longitude
        ]
        
        for lat, lon in invalid_coords:
            assert not geocoder.is_valid_singapore_coordinates(lat, lon), \
                f"({lat}, {lon}) should be invalid Singapore coordinates"


class TestSingaporeGeocoderAPI:
    """Test API-related functionality with mocking."""
    
    @patch('singapore_geocoder.requests.get')
    def test_geocode_postal_code_with_sample_data(self, mock_get):
        """Test geocoding using sample data (no API call)."""
        geocoder = SingaporeGeocoder(verbose=False)
        
        # Test with sample data postal code
        result = geocoder.geocode_postal_code("238874")
        
        # Should not make API call for sample data
        mock_get.assert_not_called()
        
        # Verify result structure and content
        assert result['success'] is True
        assert result['postal_code'] == "238874"
        assert result['latitude'] == 1.304167
        assert result['longitude'] == 103.833611
        assert result['address'] == "ION Orchard, 2 Orchard Turn, Singapore 238874"
        assert result['building'] == "ION Orchard"
        assert result['road'] == "Orchard Turn"
        assert result['error'] is None
        assert 'timestamp' in result
    
    def test_geocode_postal_code_invalid_format(self):
        """Test geocoding with invalid postal code format."""
        geocoder = SingaporeGeocoder(verbose=False)
        
        result = geocoder.geocode_postal_code("invalid")
        
        assert result['success'] is False
        assert result['error'] == "Invalid postal code format: 'invalid'"
        assert result['latitude'] is None
        assert result['longitude'] is None
    
    @patch('singapore_geocoder.requests.get')
    def test_geocode_with_api_success(self, mock_get):
        """Test successful API call for geocoding."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'found': 1,
            'results': [{
                'ADDRESS': 'Test Address, Singapore 123456',
                'BUILDING': 'Test Building',
                'ROAD': 'Test Road',
                'LATITUDE': '1.35',
                'LONGITUDE': '103.85'
            }]
        }
        mock_get.return_value = mock_response
        
        geocoder = SingaporeGeocoder(verbose=False)
        result = geocoder.geocode_postal_code("123456")
        
        assert result['success'] is True
        assert result['latitude'] == 1.35
        assert result['longitude'] == 103.85
        assert result['address'] == 'Test Address, Singapore 123456'
    
    @patch('singapore_geocoder.requests.get')
    def test_geocode_with_api_failure(self, mock_get):
        """Test API call failure handling."""
        # Mock failed API response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response
        
        geocoder = SingaporeGeocoder(verbose=False)
        result = geocoder.geocode_postal_code("123456")
        
        assert result['success'] is False
        assert "Postal code not found in OneMap database" in result['error']
    
    @patch('singapore_geocoder.requests.get')
    def test_geocode_with_network_error(self, mock_get):
        """Test network error handling."""
        # Mock network exception
        mock_get.side_effect = Exception("Network error")
        
        geocoder = SingaporeGeocoder(verbose=False)
        result = geocoder.geocode_postal_code("123456")
        
        assert result['success'] is False
        assert "Postal code not found in OneMap database" in result['error']


class TestSingaporeGeocoderMethods:
    """Test different geocoding method variations."""
    
    def test_geocode_address(self):
        """Test address geocoding method."""
        geocoder = SingaporeGeocoder(verbose=False)
        
        # Test with empty address
        result = geocoder.geocode_address("")
        assert result['success'] is False
        assert "Invalid address: empty or non-string input" in result['error']
        
        # Test with None address
        result = geocoder.geocode_address(None)
        assert result['success'] is False
        assert "Invalid address: empty or non-string input" in result['error']
    
    def test_geocode_building(self):
        """Test building name geocoding method."""
        geocoder = SingaporeGeocoder(verbose=False)
        
        # Test with empty building name
        result = geocoder.geocode_building("")
        assert result['success'] is False
        assert "Invalid building name: empty or non-string input" in result['error']
        
        # Test with None building name
        result = geocoder.geocode_building(None)
        assert result['success'] is False
        assert "Invalid building name: empty or non-string input" in result['error']
    
    def test_smart_geocode_postal_code_detection(self):
        """Test smart geocode method auto-detecting postal codes."""
        geocoder = SingaporeGeocoder(verbose=False)
        
        # Should detect as postal code and use sample data
        result = geocoder.geocode("238874")
        assert result['success'] is True
        assert result['query_type'] == 'postal_code'
    
    def test_smart_geocode_invalid_input(self):
        """Test smart geocode with invalid input."""
        geocoder = SingaporeGeocoder(verbose=False)
        
        # Test with empty string
        result = geocoder.geocode("")
        assert result['success'] is False
        assert "Invalid query: empty or non-string input" in result['error']
        
        # Test with None
        result = geocoder.geocode(None)
        assert result['success'] is False
        assert "Invalid query: empty or non-string input" in result['error']


class TestSingaporeGeocoderBatch:
    """Test batch geocoding functionality."""
    
    def test_batch_geocode_sample_data(self):
        """Test batch geocoding with sample data."""
        geocoder = SingaporeGeocoder(verbose=False)
        
        queries = ["238874", "018989", "079903"]
        results_df = geocoder.batch_geocode(queries, delay=0.1)
        
        assert isinstance(results_df, pd.DataFrame)
        assert len(results_df) == 3
        assert 'success' in results_df.columns
        assert 'query' in results_df.columns
        assert 'query_type' in results_df.columns
        
        # All should be successful with sample data
        successful = results_df['success'].sum()
        assert successful == 3
    
    def test_batch_geocode_mixed_queries(self):
        """Test batch geocoding with mixed query types."""
        geocoder = SingaporeGeocoder(verbose=False)
        
        queries = ["238874", "invalid", "018989"]
        results_df = geocoder.batch_geocode(queries, delay=0.1)
        
        assert len(results_df) == 3
        
        # Check that invalid query failed
        invalid_row = results_df[results_df['query'] == 'invalid'].iloc[0]
        assert invalid_row['success'] == False
        
        # Check that valid postal codes succeeded
        valid_rows = results_df[results_df['query'].isin(['238874', '018989'])]
        assert all(valid_rows['success'])
    
    def test_export_results(self):
        """Test exporting results to CSV."""
        geocoder = SingaporeGeocoder(verbose=False)
        
        # Create a simple DataFrame
        data = {
            'query': ['238874'],
            'success': [True],
            'latitude': [1.304167],
            'longitude': [103.833611]
        }
        df = pd.DataFrame(data)
        
        # Export to a test file
        filename = geocoder.export_results(df, "test_export.csv")
        
        assert filename == "test_export.csv"
        assert os.path.exists("test_export.csv")
        
        # Read back and verify
        imported_df = pd.read_csv("test_export.csv")
        assert len(imported_df) == 1
        assert str(imported_df.iloc[0]['query']) == '238874'
        
        # Clean up
        os.remove("test_export.csv")


class TestSingaporeGeocoderInitialization:
    """Test geocoder initialization and configuration."""
    
    def test_init_default_params(self):
        """Test initialization with default parameters."""
        geocoder = SingaporeGeocoder()
        
        assert geocoder.timeout == 10
        assert geocoder.verbose is True
    
    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        geocoder = SingaporeGeocoder(timeout=5, verbose=False)
        
        assert geocoder.timeout == 5
        assert geocoder.verbose is False
    
    def test_constants(self):
        """Test that class constants are properly set."""
        assert SingaporeGeocoder.ONEMAP_BASE_URL == "https://developers.onemap.sg/commonapi/search"
        assert "User-Agent" in SingaporeGeocoder.HEADERS
        assert "Accept" in SingaporeGeocoder.HEADERS
        
        # Test Singapore bounds
        bounds = SingaporeGeocoder.SINGAPORE_BOUNDS
        assert bounds['lat_min'] == 1.16
        assert bounds['lat_max'] == 1.48
        assert bounds['lon_min'] == 103.59
        assert bounds['lon_max'] == 104.04
        assert bounds['center_lat'] == 1.3521
        assert bounds['center_lon'] == 103.8198
        
        # Test sample data exists
        assert "238874" in SingaporeGeocoder.SAMPLE_GEOCODING_DATA
        assert "018989" in SingaporeGeocoder.SAMPLE_GEOCODING_DATA


class TestSingaporeGeocoderEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_coordinate_extraction_edge_cases(self):
        """Test coordinate extraction with various edge cases."""
        geocoder = SingaporeGeocoder(verbose=False)
        
        # Test with missing coordinates
        empty_result = {}
        coords = geocoder._extract_coordinates(empty_result)
        assert coords is None
        
        # Test with invalid coordinate format
        invalid_result = {"LATITUDE": "invalid", "LONGITUDE": "invalid"}
        coords = geocoder._extract_coordinates(invalid_result)
        assert coords is None
        
        # Test with coordinates outside Singapore bounds
        outside_result = {"LATITUDE": "40.7128", "LONGITUDE": "-74.0060"}
        coords = geocoder._extract_coordinates(outside_result)
        assert coords is None
    
    def test_result_dict_structure(self):
        """Test that result dictionaries have expected structure."""
        geocoder = SingaporeGeocoder(verbose=False)
        
        result = geocoder.geocode_postal_code("238874")
        
        expected_keys = [
            'query', 'query_type', 'success', 'latitude', 'longitude',
            'address', 'building', 'road', 'postal_code', 'error', 'timestamp'
        ]
        
        for key in expected_keys:
            assert key in result, f"Missing key '{key}' in result"
        
        # Test timestamp format (should be ISO format)
        assert 'T' in result['timestamp']  # ISO format includes 'T'


if __name__ == "__main__":
    # Run tests with pytest when executed directly
    pytest.main([__file__, "-v"])