
import pytest
from unittest.mock import MagicMock
from autodbaudit.application.annotation_sync import AnnotationSyncService

def test_merged_cells_sync_fill_down():
    """
    Verify that _read_sheet_annotations correctly fills down values for merged cells.
    """
    ws = MagicMock()
    ws.title = "Services"
    
    # Mock Headers (Raw strings)
    header_row = ("Server", "Instance", "Service Name")
    
    # Mock Data Rows (Raw values)
    row2 = ("S1", "I1", "SvcA")
    row3 = (None, None, "SvcB") # Merged
    row4 = ("S2", "I2", "SvcC")
    
    # iter_rows side_effect: first call for header, second call for data
    # Note: Header call uses max_row=1. Data call uses min_row=2.
    ws.iter_rows.side_effect = [
        [header_row], # Header
        [row2, row3, row4] # Data
    ]
    
    service = AnnotationSyncService("dummy.db")
    
    # Mock Config
    config = {
        "entity_type": "service",
        "key_cols": ["Server", "Instance", "Service Name"],
        "editable_cols": {"Status": "status"}
    }
    
    annotations = service._read_sheet_annotations(ws, config)
    
    # Keys are lowercased by normalization logic!
    assert "s1|i1|svca" in annotations, f"First row key missing. Keys: {list(annotations.keys())}"
    assert "s1|i1|svcb" in annotations, "Merged row key missing (Fill down failed)"
    assert "s2|i2|svcc" in annotations, "Third row key missing"
    
    print("Merged cell test passed!")

def test_default_instance_key_preservation():
    """
    Verify that '(Default)' instance name is preserved (and lowercased).
    """
    ws = MagicMock()
    ws.title = "Services"
    
    header_row = ("Server", "Instance", "Service Name")
    row2 = ("S1", "(Default)", "SvcA")
    
    ws.iter_rows.side_effect = [
        [header_row],
        [row2]
    ]
    
    service = AnnotationSyncService("dummy.db")
    
    config = {
        "entity_type": "service",
        "key_cols": ["Server", "Instance", "Service Name"],
        "editable_cols": {}
    }
    
    annotations = service._read_sheet_annotations(ws, config)
    
    # Expected: s1|(default)|svca
    assert "s1|(default)|svca" in annotations, f"Key should preserve (Default). Keys: {list(annotations.keys())}"
    
    print("(Default) preservation test passed!")
