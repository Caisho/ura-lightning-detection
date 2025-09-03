"""
Lightning Detection Service

Extracted from lightning_api_test.ipynb to provide reusable API functionality.
Handles fetching lightning data from NEA API and processing coordinates.
"""

import requests
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LightningService:
    """Service for fetching and processing Singapore lightning data from NEA API."""
    
    def __init__(self):
        self.api_base_url = "https://api-open.data.gov.sg/v2/real-time/api/weather"
        self.headers = {
            "User-Agent": "Lightning Detection System/1.0",
            "Accept": "application/json",
        }
        
        # Singapore bounding box for map centering
        self.singapore_bounds = {
            "lat_min": 0.95,
            "lat_max": 1.75, 
            "lon_min": 103.27,
            "lon_max": 104.52,
            "center_lat": 1.3521,
            "center_lon": 103.8198
        }
    
    def fetch_lightning_data(self, date_filter: Optional[str] = None) -> Optional[Dict]:
        """
        Fetch lightning data from NEA API using the v2 endpoint.
        
        Args:
            date_filter: Optional date filter in YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS format
            
        Returns:
            JSON response or None if failed
        """
        try:
            # Prepare parameters for the API
            params = {"api": "lightning"}
            
            # Add optional date filter if provided
            if date_filter:
                params["date"] = date_filter
                logger.info(f"Fetching lightning data for date: {date_filter}")
            else:
                logger.info("Fetching latest lightning observations")
            
            # Make API call
            logger.info(f"Calling NEA Lightning API: {self.api_base_url}")
            
            response = requests.get(
                self.api_base_url, 
                params=params,
                headers=self.headers,
                timeout=10
            )
            
            logger.info(f"Response Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ API call successful!")
                return data
            elif response.status_code == 400:
                logger.error(f"❌ Bad Request (400): Invalid parameters")
                logger.error(f"Response: {response.text}")
                return None
            elif response.status_code == 404:
                logger.error(f"❌ Not Found (404): Weather data not found")
                logger.error(f"Response: {response.text}")
                return None
            else:
                logger.error(f"❌ API call failed with status: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {e}")
            return None
    
    def parse_lightning_response(self, api_response: Dict) -> Optional[Dict]:
        """
        Parse the NEA Lightning API response and extract relevant information.
        
        Args:
            api_response: JSON response from NEA API
            
        Returns:
            dict: Parsed lightning data with metadata and readings
        """
        if not api_response or api_response.get('code') != 0:
            logger.error("❌ Invalid or error response from API")
            if api_response:
                logger.error(f"Response code: {api_response.get('code', 'Unknown')}")
                logger.error(f"Error message: {api_response.get('errorMsg', 'No error message')}")
            return None
        
        # Initialize parsed data structure
        parsed_data = {
            'timestamp': datetime.now().isoformat(),
            'api_status': api_response.get('code'),
            'error_message': api_response.get('errorMsg', ''),
            'pagination_token': api_response.get('data', {}).get('paginationToken', None),
            'records': [],
            'total_strikes': 0,
            'records_with_lightning': 0,
            'time_range': {
                'earliest': None,
                'latest': None
            }
        }
        
        # Extract records from data section
        data_section = api_response.get('data', {})
        records = data_section.get('records', [])
        
        logger.info(f"📊 Processing {len(records)} time period records from API...")
        
        # Track time range
        all_datetimes = []
        
        for record in records:
            record_datetime = record.get('datetime')
            updated_timestamp = record.get('updatedTimestamp')
            
            if record_datetime:
                all_datetimes.append(record_datetime)
            
            # Extract item data
            item = record.get('item', {})
            is_station_data = item.get('isStationData', False)
            observation_type = item.get('type', 'unknown')
            readings = item.get('readings', [])
            
            # Create record data structure
            record_data = {
                'datetime': record_datetime,
                'updated_timestamp': updated_timestamp,
                'is_station_data': is_station_data,
                'observation_type': observation_type,
                'readings_count': len(readings),
                'readings': []
            }
            
            # Process lightning readings for this time period
            if readings:
                parsed_data['records_with_lightning'] += 1
                logger.info(f"⚡ Found {len(readings)} lightning strikes at {record_datetime}")
                
                for reading in readings:
                    location = reading.get('location', {})
                    
                    # Parse coordinates (they come as strings from API)
                    try:
                        latitude = float(location.get('latitude', 0))
                        longitude = float(location.get('longitude', 0))
                    except (ValueError, TypeError):
                        logger.warning(f"⚠️ Invalid coordinates in reading: {location}")
                        continue
                    
                    reading_data = {
                        'latitude': latitude,
                        'longitude': longitude,
                        'type': reading.get('type', 'Unknown'),
                        'description': reading.get('text', 'Unknown'),
                        'datetime': reading.get('datetime'),
                        'record_datetime': record_datetime
                    }
                    
                    record_data['readings'].append(reading_data)
                    parsed_data['total_strikes'] += 1
            else:
                logger.info(f"📝 No lightning activity at {record_datetime}")
            
            parsed_data['records'].append(record_data)
        
        # Determine time range
        if all_datetimes:
            parsed_data['time_range']['earliest'] = min(all_datetimes)
            parsed_data['time_range']['latest'] = max(all_datetimes)
        
        logger.info(f"✅ Parsing complete:")
        logger.info(f"   - Time periods processed: {len(records)}")
        logger.info(f"   - Periods with lightning: {parsed_data['records_with_lightning']}")
        logger.info(f"   - Total lightning strikes: {parsed_data['total_strikes']}")
        
        return parsed_data
    
    def extract_coordinates(self, parsed_data: Dict) -> List[Dict]:
        """
        Extract coordinates from parsed lightning data into a list of dictionaries.
        
        Args:
            parsed_data: Parsed lightning data from parse_lightning_response()
            
        Returns:
            List[Dict]: List of lightning coordinates with metadata
        """
        coordinates_list = []
        
        if not parsed_data or not parsed_data.get('records'):
            logger.warning("⚠️ No lightning data available for coordinate extraction")
            return coordinates_list
        
        for record in parsed_data['records']:
            record_time = record.get('datetime', 'Unknown')
            
            for reading in record.get('readings', []):
                coord_data = {
                    'latitude': reading['latitude'],
                    'longitude': reading['longitude'],
                    'type': reading['type'],
                    'description': reading['description'],
                    'datetime': reading['datetime'],
                    'record_datetime': record_time
                }
                coordinates_list.append(coord_data)
        
        # Validate coordinates are within Singapore bounds
        if coordinates_list:
            valid_count = 0
            for coord in coordinates_list:
                if (self.singapore_bounds['lat_min'] <= coord['latitude'] <= self.singapore_bounds['lat_max'] and
                    self.singapore_bounds['lon_min'] <= coord['longitude'] <= self.singapore_bounds['lon_max']):
                    valid_count += 1
            
            logger.info(f"📍 Coordinate Summary:")
            logger.info(f"- Total coordinates extracted: {len(coordinates_list)}")
            logger.info(f"- Coordinates within Singapore bounds: {valid_count}")
            
            if valid_count < len(coordinates_list):
                logger.warning(f"⚠️ {len(coordinates_list) - valid_count} coordinates outside Singapore bounds")
        
        return coordinates_list
    
    def get_lightning_summary(self) -> Dict:
        """
        Get a complete lightning data summary by fetching and processing current data.
        
        Returns:
            Dict containing all processed lightning information
        """
        # Fetch latest lightning data
        raw_data = self.fetch_lightning_data()
        
        if not raw_data:
            return {
                'success': False,
                'error': 'Failed to fetch lightning data from API',
                'coordinates': [],
                'total_strikes': 0,
                'timestamp': datetime.now().isoformat()
            }
        
        # Parse the response
        parsed_data = self.parse_lightning_response(raw_data)
        
        if not parsed_data:
            return {
                'success': False,
                'error': 'Failed to parse lightning data',
                'coordinates': [],
                'total_strikes': 0,
                'timestamp': datetime.now().isoformat()
            }
        
        # Extract coordinates
        coordinates = self.extract_coordinates(parsed_data)
        
        return {
            'success': True,
            'coordinates': coordinates,
            'total_strikes': parsed_data['total_strikes'],
            'records_with_lightning': parsed_data['records_with_lightning'],
            'time_range': parsed_data['time_range'],
            'timestamp': parsed_data['timestamp'],
            'singapore_bounds': self.singapore_bounds,
            'raw_records_count': len(parsed_data['records'])
        }


# Create a global instance for easy import
lightning_service = LightningService()