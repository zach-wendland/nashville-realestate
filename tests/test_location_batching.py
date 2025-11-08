import pytest
import pandas as pd
from main import process_location_batch, build_pipeline_dataframe
from api.zillow_fetcher import split_locations

def test_split_locations_no_limit():
    """Test that split_locations can handle more than 5 locations."""
    locations = "loc1; loc2; loc3; loc4; loc5; loc6; loc7; loc8"
    result = split_locations(locations)
    assert len(result) == 8
    assert result == ["loc1", "loc2", "loc3", "loc4", "loc5", "loc6", "loc7", "loc8"]

def test_process_location_batch(mocker):
    """Test that process_location_batch correctly handles a batch of locations."""
    # Mock build_pipeline_dataframe to return a known DataFrame
    mock_df = pd.DataFrame({
        'PRICE': ['1000', '2000'],
        'ADDRESS': ['123 Test St', '456 Mock Ave']
    })
    mocker.patch('main.build_pipeline_dataframe', return_value=mock_df)
    
    result = process_location_batch(['37206, Nashville, TN', '37209, Nashville, TN'], '20251107')
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    assert list(result.columns) == ['PRICE', 'ADDRESS']

def test_process_location_batch_empty(mocker):
    """Test that process_location_batch handles empty results correctly."""
    # Mock build_pipeline_dataframe to return an empty DataFrame
    mocker.patch('main.build_pipeline_dataframe', return_value=pd.DataFrame())
    
    result = process_location_batch(['37206, Nashville, TN'], '20251107')
    assert result is None