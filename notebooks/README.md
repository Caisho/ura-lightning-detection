# Singapore Address Geocoding Notebook

## Overview

The `singapore_geocoding.ipynb` notebook provides a comprehensive solution for converting Singapore postal codes to longitude and latitude coordinates using the official Singapore OneMap API.

## Features

- **Postal Code Validation**: Validates Singapore 6-digit postal code format
- **OneMap API Integration**: Uses official Singapore government geocoding service
- **Batch Processing**: Process multiple postal codes efficiently with rate limiting
- **Interactive Maps**: Display results on interactive Folium maps
- **Error Handling**: Comprehensive error handling and validation
- **Offline Support**: Sample data fallback when network is unavailable
- **Export Functionality**: Save results to CSV files

## Quick Start

1. **Open the notebook**:
   ```bash
   uv run jupyter lab notebooks/singapore_geocoding.ipynb
   ```

2. **Single address geocoding**:
   ```python
   result = geocode_postal_code("238874")  # ION Orchard
   if result['success']:
       print(f"Coordinates: {result['latitude']}, {result['longitude']}")
   ```

3. **Batch geocoding**:
   ```python
   postal_codes = ["238874", "018989", "079903"]
   results_df = batch_geocode_postal_codes(postal_codes)
   ```

## Supported Postal Codes

The notebook includes sample data for popular Singapore locations:
- `238874` - ION Orchard (Orchard Road)
- `018989` - Marina Bay Sands
- `018956` - Gardens by the Bay
- `079903` - Singapore Zoo
- `099253` - Sentosa Island

## API Integration

Uses the official Singapore OneMap API:
- **Endpoint**: `https://developers.onemap.sg/commonapi/search`
- **No API key required** for basic usage
- **Rate limiting**: Built-in delay between requests
- **Fallback data**: Sample coordinates when API is unavailable

## Output Format

Each geocoding result includes:
```python
{
    'postal_code': '238874',
    'success': True,
    'latitude': 1.304167,
    'longitude': 103.833611,
    'address': 'ION Orchard, 2 Orchard Turn, Singapore 238874',
    'building': 'ION Orchard',
    'road': 'Orchard Turn',
    'error': None,
    'timestamp': '2025-01-16T...'
}
```

## Usage Examples

### Validate Postal Code
```python
if validate_singapore_postal_code("238874"):
    result = geocode_postal_code("238874")
```

### Clean User Input
```python
cleaned = clean_postal_code(" 238-874 ")  # Returns "238874"
```

### Export Results
```python
results_df.to_csv("geocoding_results.csv", index=False)
```

### Create Interactive Map
```python
map_obj = create_singapore_geocoding_map(results_df)
map_obj  # Display in Jupyter
```

## Dependencies

All required dependencies are included in the project's `pyproject.toml`:
- `requests` - API calls
- `pandas` - Data manipulation
- `folium` - Interactive mapping
- Standard library modules: `json`, `re`, `time`, `datetime`, `typing`

## Error Handling

The notebook handles various error scenarios:
- Invalid postal code format
- Network connectivity issues
- API response errors
- Coordinate validation
- Rate limiting

## Integration with Lightning Detection System

This geocoding functionality can be integrated with the main lightning detection system to:
- Convert customer addresses to coordinates for alert radius calculations
- Validate hardware installation addresses
- Generate location-based analytics
- Support customer address management

## Contributing

When adding new postal codes or features:
1. Follow the existing code style
2. Update sample data if needed
3. Test with various postal code formats
4. Update documentation