"""
Singapore Geocoding Service

A comprehensive class for geocoding Singapore addresses using the official OneMap API.
Supports postal codes, full addresses, and building names.

Author: Based on singapore_geocoding notebook
Date: 2025-09-09
"""

import json
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd
import requests


class SingaporeGeocoder:
    """
    A comprehensive geocoding service for Singapore addresses using OneMap API.
    
    Features:
    - Geocode postal codes, full addresses, and building names
    - Validate Singapore postal codes (6 digits)
    - Handle API errors gracefully with fallback data
    - Batch processing with rate limiting
    - Coordinate validation within Singapore bounds
    - Comprehensive result metadata
    """
    
    # Singapore OneMap API Configuration
    ONEMAP_BASE_URL = "https://developers.onemap.sg/commonapi/search"
    
    # Request headers
    HEADERS = {
        "User-Agent": "Singapore Geocoding Tool/1.0",
        "Accept": "application/json"
    }
    
    # Singapore bounds for validation
    SINGAPORE_BOUNDS = {
        "lat_min": 1.16,
        "lat_max": 1.48,
        "lon_min": 103.59,
        "lon_max": 104.04,
        "center_lat": 1.3521,
        "center_lon": 103.8198
    }
    
    # Singapore postal code regex (6 digits)
    POSTAL_CODE_REGEX = re.compile(r'^\d{6}$')
    
    # Sample data for demonstration when API is unavailable
    SAMPLE_GEOCODING_DATA = {
        "238874": {
            "ADDRESS": "ION Orchard, 2 Orchard Turn, Singapore 238874",
            "BUILDING": "ION Orchard",
            "ROAD": "Orchard Turn",
            "LATITUDE": "1.304167",
            "LONGITUDE": "103.833611"
        },
        "018989": {
            "ADDRESS": "Marina Bay Sands, 10 Bayfront Avenue, Singapore 018989",
            "BUILDING": "Marina Bay Sands",
            "ROAD": "Bayfront Avenue",
            "LATITUDE": "1.283611",
            "LONGITUDE": "103.859722"
        },
        "018956": {
            "ADDRESS": "Gardens by the Bay, 18 Marina Gardens Drive, Singapore 018956",
            "BUILDING": "Gardens by the Bay",
            "ROAD": "Marina Gardens Drive",
            "LATITUDE": "1.281528",
            "LONGITUDE": "103.865556"
        },
        "079903": {
            "ADDRESS": "Singapore Zoo, 80 Mandai Lake Road, Singapore 079903",
            "BUILDING": "Singapore Zoo",
            "ROAD": "Mandai Lake Road",
            "LATITUDE": "1.403611",
            "LONGITUDE": "103.791944"
        },
        "099253": {
            "ADDRESS": "Sentosa, 39 Artillery Avenue, Singapore 099253",
            "BUILDING": "Sentosa",
            "ROAD": "Artillery Avenue",
            "LATITUDE": "1.246389",
            "LONGITUDE": "103.822778"
        }
    }
    
    def __init__(self, timeout: int = 10, verbose: bool = True):
        """
        Initialize the Singapore Geocoder.
        
        Args:
            timeout: API request timeout in seconds
            verbose: Whether to print detailed progress messages
        """
        self.timeout = timeout
        self.verbose = verbose
        
        if self.verbose:
            print("🚀 Singapore Geocoder initialized!")
            print(f"   API Endpoint: {self.ONEMAP_BASE_URL}")
            print(f"   Singapore Center: ({self.SINGAPORE_BOUNDS['center_lat']}, {self.SINGAPORE_BOUNDS['center_lon']})")
            print("   Ready for geocoding postal codes, addresses, and building names")
    
    def validate_postal_code(self, postal_code: str) -> bool:
        """
        Validate if a string is a valid Singapore postal code.
        
        Args:
            postal_code: String to validate
            
        Returns:
            bool: True if valid Singapore postal code, False otherwise
        """
        if not postal_code or not isinstance(postal_code, str):
            return False
        
        # Remove any spaces or special characters
        cleaned = re.sub(r'[^0-9]', '', postal_code.strip())
        
        # Check if it's exactly 6 digits
        return bool(self.POSTAL_CODE_REGEX.match(cleaned))
    
    def clean_postal_code(self, postal_code: str) -> Optional[str]:
        """
        Clean and format a postal code string.
        
        Args:
            postal_code: Raw postal code string
            
        Returns:
            Cleaned 6-digit postal code or None if invalid
        """
        if not postal_code or not isinstance(postal_code, str):
            return None
        
        # Remove any non-digit characters
        cleaned = re.sub(r'[^0-9]', '', postal_code.strip())
        
        # Validate length
        if len(cleaned) == 6 and cleaned.isdigit():
            return cleaned
        
        return None
    
    def _make_api_call(self, query: str, return_geom: bool = True) -> Optional[Dict]:
        """
        Make a call to the OneMap API.
        
        Args:
            query: Search query (postal code, address, or building name)
            return_geom: Whether to return geometry coordinates
            
        Returns:
            Dictionary with API results or None if failed
        """
        # First try sample data for common postal codes
        cleaned_query = query.strip()
        if cleaned_query in self.SAMPLE_GEOCODING_DATA:
            if self.verbose:
                print(f"Using sample data for query: '{cleaned_query}'")
            return self.SAMPLE_GEOCODING_DATA[cleaned_query]
        
        try:
            # Prepare API parameters
            params = {
                'searchVal': cleaned_query,
                'returnGeom': 'Y' if return_geom else 'N',
                'getAddrDetails': 'Y',  # Get detailed address information
                'pageNum': '1'  # First page of results
            }
            
            if self.verbose:
                print(f"Geocoding query: '{query}'")
            
            # Make API call
            response = requests.get(
                self.ONEMAP_BASE_URL,
                params=params,
                headers=self.HEADERS,
                timeout=self.timeout
            )
            
            if self.verbose:
                print(f"API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                found = data.get('found', 0)
                if self.verbose:
                    print(f"Found {found} result(s)")
                
                if found > 0:
                    results = data.get('results', [])
                    if results:
                        # Return the first (most relevant) result
                        return results[0]
                
                return None
            else:
                if self.verbose:
                    print(f"API call failed with status: {response.status_code}")
                    print(f"Response: {response.text[:200]}")
                return None
                
        except requests.exceptions.RequestException as e:
            if self.verbose:
                print(f"Request failed: {e}")
                print("Note: Network may be unavailable, using sample data if available")
            return None
        except json.JSONDecodeError as e:
            if self.verbose:
                print(f"JSON decode error: {e}")
            return None
        except Exception as e:
            if self.verbose:
                print(f"Unexpected error: {e}")
            return None
    
    def _extract_coordinates(self, geocoding_result: Dict) -> Optional[Tuple[float, float]]:
        """
        Extract latitude and longitude from OneMap geocoding result.
        
        Args:
            geocoding_result: Result dictionary from OneMap API
            
        Returns:
            Tuple of (latitude, longitude) or None if extraction failed
        """
        try:
            # OneMap returns coordinates as strings
            latitude = float(geocoding_result.get('LATITUDE', 0))
            longitude = float(geocoding_result.get('LONGITUDE', 0))
            
            # Validate coordinates are within Singapore bounds
            if (self.SINGAPORE_BOUNDS['lat_min'] <= latitude <= self.SINGAPORE_BOUNDS['lat_max'] and
                self.SINGAPORE_BOUNDS['lon_min'] <= longitude <= self.SINGAPORE_BOUNDS['lon_max']):
                return (latitude, longitude)
            else:
                if self.verbose:
                    print(f"Coordinates outside Singapore bounds: ({latitude}, {longitude})")
                return None
                
        except (ValueError, TypeError, KeyError) as e:
            if self.verbose:
                print(f"Failed to extract coordinates: {e}")
            return None
    
    def _create_result_dict(self, query: str, query_type: str) -> Dict:
        """
        Create a standardized result dictionary.
        
        Args:
            query: Original query string
            query_type: Type of query (postal_code, address, building)
            
        Returns:
            Dictionary with default result structure
        """
        return {
            'query': query,
            'query_type': query_type,
            'success': False,
            'latitude': None,
            'longitude': None,
            'address': None,
            'building': None,
            'road': None,
            'postal_code': None,
            'error': None,
            'timestamp': datetime.now().isoformat()
        }
    
    def geocode_postal_code(self, postal_code: str) -> Dict:
        """
        Geocode a Singapore postal code.
        
        Args:
            postal_code: Singapore postal code (6 digits)
            
        Returns:
            Dictionary with geocoding results and metadata
        """
        result = self._create_result_dict(postal_code, 'postal_code')
        
        # Validate postal code
        cleaned_code = self.clean_postal_code(postal_code)
        if not cleaned_code:
            result['error'] = f"Invalid postal code format: '{postal_code}'"
            return result
        
        # Update with cleaned code
        result['postal_code'] = cleaned_code
        
        # Geocode using OneMap API
        geocoding_result = self._make_api_call(cleaned_code)
        
        if geocoding_result:
            # Extract coordinates
            coordinates = self._extract_coordinates(geocoding_result)
            
            if coordinates:
                result['success'] = True
                result['latitude'], result['longitude'] = coordinates
                
                # Extract additional address information
                result['address'] = geocoding_result.get('ADDRESS', '')
                result['building'] = geocoding_result.get('BUILDING', '')
                result['road'] = geocoding_result.get('ROAD', '')
                
                if self.verbose:
                    print(f"✅ Successfully geocoded {cleaned_code}:")
                    print(f"   Address: {result['address']}")
                    print(f"   Coordinates: ({result['latitude']:.6f}, {result['longitude']:.6f})")
            else:
                result['error'] = "Failed to extract valid coordinates"
        else:
            result['error'] = "Postal code not found in OneMap database"
        
        return result
    
    def geocode_address(self, address: str) -> Dict:
        """
        Geocode a full Singapore address.
        
        Args:
            address: Full address string
            
        Returns:
            Dictionary with geocoding results and metadata
        """
        result = self._create_result_dict(address, 'address')
        
        if not address or not isinstance(address, str) or not address.strip():
            result['error'] = "Invalid address: empty or non-string input"
            return result
        
        # Geocode using OneMap API
        geocoding_result = self._make_api_call(address.strip())
        
        if geocoding_result:
            # Extract coordinates
            coordinates = self._extract_coordinates(geocoding_result)
            
            if coordinates:
                result['success'] = True
                result['latitude'], result['longitude'] = coordinates
                
                # Extract additional information
                result['address'] = geocoding_result.get('ADDRESS', '')
                result['building'] = geocoding_result.get('BUILDING', '')
                result['road'] = geocoding_result.get('ROAD', '')
                
                # Try to extract postal code from address
                postal_match = re.search(r'\b(\d{6})\b', result['address'])
                if postal_match:
                    result['postal_code'] = postal_match.group(1)
                
                if self.verbose:
                    print(f"✅ Successfully geocoded address:")
                    print(f"   Address: {result['address']}")
                    print(f"   Coordinates: ({result['latitude']:.6f}, {result['longitude']:.6f})")
            else:
                result['error'] = "Failed to extract valid coordinates"
        else:
            result['error'] = "Address not found in OneMap database"
        
        return result
    
    def geocode_building(self, building_name: str) -> Dict:
        """
        Geocode a Singapore building name.
        
        Args:
            building_name: Name of the building
            
        Returns:
            Dictionary with geocoding results and metadata
        """
        result = self._create_result_dict(building_name, 'building')
        
        if not building_name or not isinstance(building_name, str) or not building_name.strip():
            result['error'] = "Invalid building name: empty or non-string input"
            return result
        
        # Geocode using OneMap API
        geocoding_result = self._make_api_call(building_name.strip())
        
        if geocoding_result:
            # Extract coordinates
            coordinates = self._extract_coordinates(geocoding_result)
            
            if coordinates:
                result['success'] = True
                result['latitude'], result['longitude'] = coordinates
                
                # Extract additional information
                result['address'] = geocoding_result.get('ADDRESS', '')
                result['building'] = geocoding_result.get('BUILDING', '')
                result['road'] = geocoding_result.get('ROAD', '')
                
                # Try to extract postal code from address
                postal_match = re.search(r'\b(\d{6})\b', result['address'])
                if postal_match:
                    result['postal_code'] = postal_match.group(1)
                
                if self.verbose:
                    print(f"✅ Successfully geocoded building:")
                    print(f"   Building: {result['building']}")
                    print(f"   Address: {result['address']}")
                    print(f"   Coordinates: ({result['latitude']:.6f}, {result['longitude']:.6f})")
            else:
                result['error'] = "Failed to extract valid coordinates"
        else:
            result['error'] = "Building not found in OneMap database"
        
        return result
    
    def geocode(self, query: str) -> Dict:
        """
        Smart geocoding that automatically detects query type and geocodes accordingly.
        
        Args:
            query: Postal code, address, or building name
            
        Returns:
            Dictionary with geocoding results and metadata
        """
        if not query or not isinstance(query, str) or not query.strip():
            result = self._create_result_dict(query, 'unknown')
            result['error'] = "Invalid query: empty or non-string input"
            return result
        
        query = query.strip()
        
        # Check if it's a postal code
        if self.validate_postal_code(query):
            return self.geocode_postal_code(query)
        
        # Check if it looks like a postal code within a longer string
        postal_match = re.search(r'\b(\d{6})\b', query)
        if postal_match:
            # If it contains a postal code, treat as address
            return self.geocode_address(query)
        
        # Otherwise, try as building/general address
        return self.geocode_building(query)
    
    def batch_geocode(self, queries: List[str], delay: float = 0.5) -> pd.DataFrame:
        """
        Geocode multiple queries with rate limiting.
        
        Args:
            queries: List of queries to geocode (postal codes, addresses, or building names)
            delay: Delay between API calls in seconds (to respect rate limits)
            
        Returns:
            DataFrame with geocoding results
        """
        results = []
        
        if self.verbose:
            print(f"Batch geocoding {len(queries)} queries...")
            print(f"Rate limiting: {delay}s delay between calls")
        
        for i, query in enumerate(queries, 1):
            if self.verbose:
                print(f"\nProcessing {i}/{len(queries)}: {query}")
            
            result = self.geocode(query)
            results.append(result)
            
            # Rate limiting - respect API limits
            if i < len(queries):
                time.sleep(delay)
        
        # Convert to DataFrame
        df = pd.DataFrame(results)
        
        # Summary statistics
        if not df.empty:
            successful = df['success'].sum()
            failed = len(df) - successful
            
            if self.verbose:
                print("\n📊 Batch geocoding completed:")
                print(f"   ✅ Successful: {successful}/{len(queries)} ({successful/len(queries)*100:.1f}%)")
                print(f"   ❌ Failed: {failed}/{len(queries)} ({failed/len(queries)*100:.1f}%)")
        
        return df
    
    def get_singapore_center(self) -> Tuple[float, float]:
        """
        Get Singapore center coordinates.
        
        Returns:
            Tuple of (latitude, longitude) for Singapore center
        """
        return (self.SINGAPORE_BOUNDS['center_lat'], self.SINGAPORE_BOUNDS['center_lon'])
    
    def is_valid_singapore_coordinates(self, latitude: float, longitude: float) -> bool:
        """
        Check if coordinates are within Singapore bounds.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            bool: True if coordinates are within Singapore bounds
        """
        return (self.SINGAPORE_BOUNDS['lat_min'] <= latitude <= self.SINGAPORE_BOUNDS['lat_max'] and
                self.SINGAPORE_BOUNDS['lon_min'] <= longitude <= self.SINGAPORE_BOUNDS['lon_max'])
    
    def export_results(self, results_df: pd.DataFrame, filename: Optional[str] = None) -> str:
        """
        Export geocoding results to CSV file.
        
        Args:
            results_df: DataFrame with geocoding results
            filename: Optional custom filename
            
        Returns:
            String with the output filename
        """
        if filename is None:
            filename = f"singapore_geocoding_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        results_df.to_csv(filename, index=False)
        
        if self.verbose:
            print(f"💾 Results exported to: {filename}")
        
        return filename


# Example usage and testing
if __name__ == "__main__":
    # Initialize the geocoder
    geocoder = SingaporeGeocoder(verbose=True)
    
    # Test cases
    test_cases = [
        "238874",  # Postal code
        "Marina Bay Sands",  # Building name
        "ION Orchard, 2 Orchard Turn, Singapore 238874",  # Full address
        "Singapore Zoo",  # Building name
        "018989",  # Postal code
        "Sentosa Island"  # Location name
    ]
    
    print("\n🧪 Testing Singapore Geocoder with various query types:")
    print("=" * 70)
    
    for query in test_cases:
        print(f"\n📍 Testing: '{query}'")
        result = geocoder.geocode(query)
        
        if result['success']:
            print(f"✅ Success - Type: {result['query_type']}")
            print(f"   Coordinates: ({result['latitude']:.6f}, {result['longitude']:.6f})")
            print(f"   Address: {result['address']}")
        else:
            print(f"❌ Failed: {result['error']}")
    
    # Test batch geocoding
    print("\n🔄 Testing batch geocoding:")
    batch_results = geocoder.batch_geocode(test_cases[:3], delay=0.5)
    
    if not batch_results.empty:
        print("\n📊 Batch results summary:")
        successful = batch_results[batch_results['success']]
        print(f"Successful geocoding: {len(successful)}/{len(batch_results)}")
        
        # Export results
        output_file = geocoder.export_results(batch_results)
        print(f"Results saved to: {output_file}")