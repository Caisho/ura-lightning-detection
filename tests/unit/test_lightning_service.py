"""
Comprehensive unit tests for LightningService API requests.

Tests cover:
- API request functionality with mocking
- Response parsing and data extraction
- Error handling for various failure scenarios
- Coordinate validation and processing
- Edge cases and malformed data handling
"""

import json
import pytest
from datetime import datetime
from unittest.mock import Mock, patch
import requests

from src.lightning_service import LightningService, lightning_service


class TestLightningServiceInitialization:
    """Test LightningService initialization and configuration."""
    
    def test_init_default_params(self):
        """Test LightningService initialization with default parameters."""
        service = LightningService()
        
        assert service.api_base_url == "https://api-open.data.gov.sg/v2/real-time/api/weather"
        assert "User-Agent" in service.headers
        assert "Accept" in service.headers
        assert service.headers["Accept"] == "application/json"
        
        # Test Singapore bounds configuration
        bounds = service.singapore_bounds
        assert bounds["lat_min"] == 0.95
        assert bounds["lat_max"] == 1.75
        assert bounds["lon_min"] == 103.27
        assert bounds["lon_max"] == 104.52
        assert bounds["center_lat"] == 1.3521
        assert bounds["center_lon"] == 103.8198
    
    def test_global_instance_exists(self):
        """Test that global lightning_service instance is available."""
        assert lightning_service is not None
        assert isinstance(lightning_service, LightningService)


class TestLightningServiceFetchData:
    """Test lightning data fetching functionality."""
    
    @patch('src.lightning_service.requests.get')
    def test_fetch_lightning_data_success(self, mock_get):
        """Test successful lightning data fetch."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "records": [
                    {
                        "datetime": "2024-01-15T10:00:00+08:00",
                        "item": {
                            "type": "lightning",
                            "readings": []
                        }
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        service = LightningService()
        result = service.fetch_lightning_data()
        
        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[0][0] == service.api_base_url
        assert call_args[1]['params'] == {"api": "lightning"}
        assert call_args[1]['headers'] == service.headers
        assert call_args[1]['timeout'] == 10
        
        # Verify result
        assert result is not None
        assert result["code"] == 0
        assert "data" in result
    
    @patch('src.lightning_service.requests.get')
    def test_fetch_lightning_data_with_date_filter(self, mock_get):
        """Test lightning data fetch with date filter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "data": {"records": []}}
        mock_get.return_value = mock_response
        
        service = LightningService()
        date_filter = "2024-01-15"
        result = service.fetch_lightning_data(date_filter)
        
        # Verify date filter was included in params
        call_args = mock_get.call_args
        assert call_args[1]['params'] == {"api": "lightning", "date": date_filter}
        assert result is not None
    
    @patch('src.lightning_service.requests.get')
    def test_fetch_lightning_data_400_error(self, mock_get):
        """Test handling of 400 Bad Request error."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid parameters"
        mock_get.return_value = mock_response
        
        service = LightningService()
        result = service.fetch_lightning_data()
        
        assert result is None
    
    @patch('src.lightning_service.requests.get')
    def test_fetch_lightning_data_404_error(self, mock_get):
        """Test handling of 404 Not Found error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Weather data not found"
        mock_get.return_value = mock_response
        
        service = LightningService()
        result = service.fetch_lightning_data()
        
        assert result is None
    
    @patch('src.lightning_service.requests.get')
    def test_fetch_lightning_data_other_error(self, mock_get):
        """Test handling of other HTTP error codes."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_get.return_value = mock_response
        
        service = LightningService()
        result = service.fetch_lightning_data()
        
        assert result is None
    
    @patch('src.lightning_service.requests.get')
    def test_fetch_lightning_data_request_exception(self, mock_get):
        """Test handling of network/request exceptions."""
        mock_get.side_effect = requests.exceptions.RequestException("Network error")
        
        service = LightningService()
        result = service.fetch_lightning_data()
        
        assert result is None
    
    @patch('src.lightning_service.requests.get')
    def test_fetch_lightning_data_json_decode_error(self, mock_get):
        """Test handling of JSON decode errors."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_get.return_value = mock_response
        
        service = LightningService()
        result = service.fetch_lightning_data()
        
        assert result is None


class TestLightningServiceParseResponse:
    """Test lightning response parsing functionality."""
    
    def test_parse_lightning_response_success(self):
        """Test successful parsing of lightning response."""
        api_response = {
            "code": 0,
            "data": {
                "paginationToken": "test-token",
                "records": [
                    {
                        "datetime": "2024-01-15T10:00:00+08:00",
                        "updatedTimestamp": "2024-01-15T10:05:00+08:00",
                        "item": {
                            "isStationData": False,
                            "type": "lightning",
                            "readings": [
                                {
                                    "location": {
                                        "latitude": "1.3521",
                                        "longitude": "103.8198"
                                    },
                                    "type": "CG",
                                    "text": "Cloud-to-ground lightning",
                                    "datetime": "2024-01-15T10:00:00+08:00"
                                }
                            ]
                        }
                    },
                    {
                        "datetime": "2024-01-15T10:05:00+08:00",
                        "item": {
                            "type": "lightning",
                            "readings": []
                        }
                    }
                ]
            }
        }
        
        service = LightningService()
        result = service.parse_lightning_response(api_response)
        
        assert result is not None
        assert result["api_status"] == 0
        assert result["pagination_token"] == "test-token"
        assert len(result["records"]) == 2
        assert result["total_strikes"] == 1
        assert result["records_with_lightning"] == 1
        
        # Check time range
        assert result["time_range"]["earliest"] == "2024-01-15T10:00:00+08:00"
        assert result["time_range"]["latest"] == "2024-01-15T10:05:00+08:00"
        
        # Check first record with lightning
        first_record = result["records"][0]
        assert first_record["datetime"] == "2024-01-15T10:00:00+08:00"
        assert first_record["is_station_data"] is False
        assert first_record["observation_type"] == "lightning"
        assert first_record["readings_count"] == 1
        assert len(first_record["readings"]) == 1
        
        # Check reading details
        reading = first_record["readings"][0]
        assert reading["latitude"] == 1.3521
        assert reading["longitude"] == 103.8198
        assert reading["type"] == "CG"
        assert reading["description"] == "Cloud-to-ground lightning"
    
    def test_parse_lightning_response_empty_data(self):
        """Test parsing response with no lightning data."""
        api_response = {
            "code": 0,
            "data": {
                "records": []
            }
        }
        
        service = LightningService()
        result = service.parse_lightning_response(api_response)
        
        assert result is not None
        assert result["total_strikes"] == 0
        assert result["records_with_lightning"] == 0
        assert len(result["records"]) == 0
        assert result["time_range"]["earliest"] is None
        assert result["time_range"]["latest"] is None
    
    def test_parse_lightning_response_invalid_response(self):
        """Test parsing invalid API response."""
        invalid_responses = [
            None,
            {"code": 1, "errorMsg": "API Error"},
            {"code": -1, "errorMsg": "Invalid request"},
            {}
        ]
        
        service = LightningService()
        
        for invalid_response in invalid_responses:
            result = service.parse_lightning_response(invalid_response)
            assert result is None
    
    def test_parse_lightning_response_invalid_coordinates(self):
        """Test parsing response with invalid coordinate data."""
        api_response = {
            "code": 0,
            "data": {
                "records": [
                    {
                        "datetime": "2024-01-15T10:00:00+08:00",
                        "item": {
                            "type": "lightning",
                            "readings": [
                                {
                                    "location": {
                                        "latitude": "invalid",
                                        "longitude": "103.8198"
                                    },
                                    "type": "CG",
                                    "text": "Invalid coordinate",
                                    "datetime": "2024-01-15T10:00:00+08:00"
                                },
                                {
                                    "location": {
                                        "latitude": "1.3521",
                                        "longitude": "valid_coord"
                                    },
                                    "type": "CG",
                                    "text": "Valid lightning",
                                    "datetime": "2024-01-15T10:00:00+08:00"
                                }
                            ]
                        }
                    }
                ]
            }
        }
        
        service = LightningService()
        result = service.parse_lightning_response(api_response)
        
        # Should still process, but skip invalid coordinates
        assert result is not None
        assert result["total_strikes"] == 0  # Both readings had invalid coordinates
        assert len(result["records"][0]["readings"]) == 0  # Invalid readings filtered out
    
    def test_parse_lightning_response_missing_fields(self):
        """Test parsing response with missing fields."""
        api_response = {
            "code": 0,
            "data": {
                "records": [
                    {
                        # Missing datetime
                        "item": {
                            "readings": [
                                {
                                    "location": {
                                        "latitude": "1.3521",
                                        "longitude": "103.8198"
                                    }
                                    # Missing type, text, datetime
                                }
                            ]
                        }
                    }
                ]
            }
        }
        
        service = LightningService()
        result = service.parse_lightning_response(api_response)
        
        assert result is not None
        assert result["total_strikes"] == 1
        
        # Check default values are used
        reading = result["records"][0]["readings"][0]
        assert reading["type"] == "Unknown"
        assert reading["description"] == "Unknown"
        assert reading["datetime"] is None


class TestLightningServiceExtractCoordinates:
    """Test coordinate extraction functionality."""
    
    def test_extract_coordinates_success(self):
        """Test successful coordinate extraction."""
        parsed_data = {
            "records": [
                {
                    "datetime": "2024-01-15T10:00:00+08:00",
                    "readings": [
                        {
                            "latitude": 1.3521,
                            "longitude": 103.8198,
                            "type": "CG",
                            "description": "Cloud-to-ground",
                            "datetime": "2024-01-15T10:00:00+08:00"
                        },
                        {
                            "latitude": 1.4000,
                            "longitude": 103.9000,
                            "type": "IC",
                            "description": "Intra-cloud",
                            "datetime": "2024-01-15T10:01:00+08:00"
                        }
                    ]
                },
                {
                    "datetime": "2024-01-15T10:05:00+08:00",
                    "readings": [
                        {
                            "latitude": 1.3000,
                            "longitude": 103.8000,
                            "type": "CG",
                            "description": "Cloud-to-ground",
                            "datetime": "2024-01-15T10:05:00+08:00"
                        }
                    ]
                }
            ]
        }
        
        service = LightningService()
        coordinates = service.extract_coordinates(parsed_data)
        
        assert len(coordinates) == 3
        
        # Check first coordinate
        coord1 = coordinates[0]
        assert coord1["latitude"] == 1.3521
        assert coord1["longitude"] == 103.8198
        assert coord1["type"] == "CG"
        assert coord1["description"] == "Cloud-to-ground"
        assert coord1["datetime"] == "2024-01-15T10:00:00+08:00"
        assert coord1["record_datetime"] == "2024-01-15T10:00:00+08:00"
        
        # Check second coordinate
        coord2 = coordinates[1]
        assert coord2["type"] == "IC"
        assert coord2["description"] == "Intra-cloud"
        
        # Check third coordinate
        coord3 = coordinates[2]
        assert coord3["record_datetime"] == "2024-01-15T10:05:00+08:00"
    
    def test_extract_coordinates_empty_data(self):
        """Test coordinate extraction with empty data."""
        empty_data_cases = [
            None,
            {},
            {"records": []},
            {"records": [{"datetime": "2024-01-15T10:00:00+08:00", "readings": []}]}
        ]
        
        service = LightningService()
        
        for empty_data in empty_data_cases:
            coordinates = service.extract_coordinates(empty_data)
            assert len(coordinates) == 0
    
    def test_extract_coordinates_bounds_validation(self):
        """Test coordinate extraction with bounds validation."""
        # Mix of valid and invalid Singapore coordinates
        parsed_data = {
            "records": [
                {
                    "datetime": "2024-01-15T10:00:00+08:00",
                    "readings": [
                        {
                            "latitude": 1.3521,  # Valid Singapore
                            "longitude": 103.8198,
                            "type": "CG",
                            "description": "Valid Singapore",
                            "datetime": "2024-01-15T10:00:00+08:00"
                        },
                        {
                            "latitude": 40.7128,  # New York (outside Singapore)
                            "longitude": -74.0060,
                            "type": "CG",
                            "description": "Outside Singapore",
                            "datetime": "2024-01-15T10:01:00+08:00"
                        },
                        {
                            "latitude": 1.4500,  # Valid Singapore
                            "longitude": 103.9000,
                            "type": "IC",
                            "description": "Valid Singapore 2",
                            "datetime": "2024-01-15T10:02:00+08:00"
                        }
                    ]
                }
            ]
        }
        
        service = LightningService()
        coordinates = service.extract_coordinates(parsed_data)
        
        # Should extract all coordinates, bounds checking is just for logging
        assert len(coordinates) == 3
        
        # Verify all coordinates are extracted regardless of bounds
        singapore_coords = [c for c in coordinates if 1.0 <= c["latitude"] <= 1.5]
        assert len(singapore_coords) == 2  # Two valid Singapore coordinates


class TestLightningServiceSummary:
    """Test complete lightning summary functionality."""
    
    @patch.object(LightningService, 'fetch_lightning_data')
    @patch.object(LightningService, 'parse_lightning_response')
    @patch.object(LightningService, 'extract_coordinates')
    def test_get_lightning_summary_success(self, mock_extract, mock_parse, mock_fetch):
        """Test successful lightning summary generation."""
        # Mock the chain of calls
        mock_fetch.return_value = {"code": 0, "data": {"records": []}}
        mock_parse.return_value = {
            "total_strikes": 5,
            "records_with_lightning": 3,
            "time_range": {
                "earliest": "2024-01-15T10:00:00+08:00",
                "latest": "2024-01-15T10:30:00+08:00"
            },
            "timestamp": "2024-01-15T10:35:00",
            "records": []
        }
        mock_extract.return_value = [
            {"latitude": 1.3521, "longitude": 103.8198, "type": "CG"},
            {"latitude": 1.4000, "longitude": 103.9000, "type": "IC"}
        ]
        
        service = LightningService()
        summary = service.get_lightning_summary()
        
        # Verify method calls
        mock_fetch.assert_called_once()
        mock_parse.assert_called_once()
        mock_extract.assert_called_once()
        
        # Verify summary structure
        assert summary["success"] is True
        assert len(summary["coordinates"]) == 2
        assert summary["total_strikes"] == 5
        assert summary["records_with_lightning"] == 3
        assert summary["time_range"]["earliest"] == "2024-01-15T10:00:00+08:00"
        assert summary["time_range"]["latest"] == "2024-01-15T10:30:00+08:00"
        assert "singapore_bounds" in summary
        assert "raw_records_count" in summary
    
    @patch.object(LightningService, 'fetch_lightning_data')
    def test_get_lightning_summary_fetch_failure(self, mock_fetch):
        """Test lightning summary when fetch fails."""
        mock_fetch.return_value = None
        
        service = LightningService()
        summary = service.get_lightning_summary()
        
        assert summary["success"] is False
        assert summary["error"] == "Failed to fetch lightning data from API"
        assert len(summary["coordinates"]) == 0
        assert summary["total_strikes"] == 0
        assert "timestamp" in summary
    
    @patch.object(LightningService, 'fetch_lightning_data')
    @patch.object(LightningService, 'parse_lightning_response')
    def test_get_lightning_summary_parse_failure(self, mock_parse, mock_fetch):
        """Test lightning summary when parsing fails."""
        mock_fetch.return_value = {"code": 0, "data": {"records": []}}
        mock_parse.return_value = None
        
        service = LightningService()
        summary = service.get_lightning_summary()
        
        assert summary["success"] is False
        assert summary["error"] == "Failed to parse lightning data"
        assert len(summary["coordinates"]) == 0
        assert summary["total_strikes"] == 0


class TestLightningServiceEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_singapore_bounds_constants(self):
        """Test Singapore bounds are correctly defined."""
        service = LightningService()
        bounds = service.singapore_bounds
        
        # Validate bounds make sense
        assert bounds["lat_min"] < bounds["lat_max"]
        assert bounds["lon_min"] < bounds["lon_max"]
        assert bounds["lat_min"] <= bounds["center_lat"] <= bounds["lat_max"]
        assert bounds["lon_min"] <= bounds["center_lon"] <= bounds["lon_max"]
        
        # Validate Singapore-specific bounds
        assert 0.5 <= bounds["lat_min"] <= 1.5  # Reasonable latitude range
        assert 103.0 <= bounds["lon_min"] <= 104.0  # Reasonable longitude range
    
    def test_headers_configuration(self):
        """Test API headers are properly configured."""
        service = LightningService()
        headers = service.headers
        
        assert "User-Agent" in headers
        assert "Accept" in headers
        assert headers["Accept"] == "application/json"
        assert "Lightning Detection System" in headers["User-Agent"]
    
    @patch('src.lightning_service.requests.get')
    def test_api_timeout_configuration(self, mock_get):
        """Test API timeout is properly configured."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "data": {"records": []}}
        mock_get.return_value = mock_response
        
        service = LightningService()
        service.fetch_lightning_data()
        
        # Verify timeout is set
        call_args = mock_get.call_args
        assert call_args[1]['timeout'] == 10
    
    def test_datetime_handling(self):
        """Test proper datetime handling in responses."""
        api_response = {
            "code": 0,
            "data": {
                "records": [
                    {
                        "datetime": "2024-01-15T10:00:00+08:00",
                        "item": {
                            "type": "lightning",
                            "readings": []
                        }
                    },
                    {
                        "datetime": "2024-01-15T09:30:00+08:00",  # Earlier time
                        "item": {
                            "type": "lightning", 
                            "readings": []
                        }
                    },
                    {
                        "datetime": "2024-01-15T10:30:00+08:00",  # Later time
                        "item": {
                            "type": "lightning",
                            "readings": []
                        }
                    }
                ]
            }
        }
        
        service = LightningService()
        result = service.parse_lightning_response(api_response)
        
        # Verify time range calculation
        assert result["time_range"]["earliest"] == "2024-01-15T09:30:00+08:00"
        assert result["time_range"]["latest"] == "2024-01-15T10:30:00+08:00"


class TestLightningServiceIntegration:
    """Integration tests that test multiple components together."""
    
    @patch('src.lightning_service.requests.get')
    def test_full_workflow_with_real_response_structure(self, mock_get):
        """Test full workflow with realistic API response structure."""
        # Mock realistic NEA Lightning API response
        realistic_response = {
            "code": 0,
            "errorMsg": "",
            "data": {
                "paginationToken": "eyJkYXRldGltZSI6IjIwMjQtMDEtMTVUMTA6MDA6MDAuMDAwWiJ9",
                "records": [
                    {
                        "datetime": "2024-01-15T10:00:00+08:00",
                        "updatedTimestamp": "2024-01-15T10:02:00.123Z",
                        "item": {
                            "isStationData": False,
                            "type": "lightning",
                            "readings": [
                                {
                                    "location": {
                                        "latitude": "1.352083",
                                        "longitude": "103.819836"
                                    },
                                    "type": "CG",
                                    "text": "Cloud-to-Ground Lightning",
                                    "datetime": "2024-01-15T10:00:15+08:00"
                                },
                                {
                                    "location": {
                                        "latitude": "1.340000",
                                        "longitude": "103.830000"
                                    },
                                    "type": "IC", 
                                    "text": "Intra-Cloud Lightning",
                                    "datetime": "2024-01-15T10:00:45+08:00"
                                }
                            ]
                        }
                    },
                    {
                        "datetime": "2024-01-15T10:05:00+08:00", 
                        "updatedTimestamp": "2024-01-15T10:07:00.456Z",
                        "item": {
                            "isStationData": False,
                            "type": "lightning",
                            "readings": []
                        }
                    }
                ]
            }
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = realistic_response
        mock_get.return_value = mock_response
        
        # Test the full workflow
        service = LightningService()
        summary = service.get_lightning_summary()
        
        # Verify complete workflow
        assert summary["success"] is True
        assert summary["total_strikes"] == 2
        assert summary["records_with_lightning"] == 1
        assert len(summary["coordinates"]) == 2
        
        # Verify coordinate details
        coords = summary["coordinates"]
        assert coords[0]["latitude"] == 1.352083
        assert coords[0]["longitude"] == 103.819836
        assert coords[0]["type"] == "CG"
        assert coords[0]["description"] == "Cloud-to-Ground Lightning"
        
        assert coords[1]["latitude"] == 1.340000
        assert coords[1]["longitude"] == 103.830000
        assert coords[1]["type"] == "IC"
        assert coords[1]["description"] == "Intra-Cloud Lightning"
        
        # Verify metadata
        assert summary["raw_records_count"] == 2
        assert "singapore_bounds" in summary
        assert "timestamp" in summary