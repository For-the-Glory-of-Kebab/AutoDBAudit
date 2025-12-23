
import pytest
from unittest.mock import MagicMock
from autodbaudit.application.collectors.infrastructure import InfrastructureCollector
from autodbaudit.application.collectors.base import CollectorContext

def test_collect_client_protocols_generates_all_four():
    """
    Verify that _collect_client_protocols generates findings/rows for all 4 standard protocols.
    """
    # Setup Context
    conn = MagicMock()
    writer = MagicMock()
    prov = MagicMock()
    
    ctx = CollectorContext(
        connector=conn,
        query_provider=prov,
        writer=writer,
        server_name="TestServer",
        instance_name="TestInstance"
    )
    
    # Instantiate with context
    collector = InfrastructureCollector(ctx)
    
    # Mock query result: Only TCP/IP is returned
    mock_protocols = [
        {"ProtocolName": "TCP/IP", "IsEnabled": 1, "DefaultPort": 1433, "Notes": "Found"}
    ]
    conn.execute_query.return_value = mock_protocols
    
    # Mock save_finding
    collector.save_finding = MagicMock()
    
    # Run
    count = collector._collect_client_protocols()
    
    # Verify count is 4 (Standard set)
    assert count == 4, f"Expected 4 protocols, got {count}"
    
    # Verify Writer calls
    assert writer.add_client_protocol.call_count == 4
    
    # Check Findings
    assert collector.save_finding.call_count == 4
    
    # Check Named Pipes finding (Manual)
    found_named_pipes = False
    for call_args in collector.save_finding.call_args_list:
        args, kwargs = call_args
        if kwargs.get('entity_name') == 'Named Pipes':
            found_named_pipes = True
            assert kwargs['status'] == 'PASS'
            assert "disabled" in kwargs['description']
            assert "Manual" in kwargs['description']
            break
            
    assert found_named_pipes, "Named Pipes finding not generated"
    
    # Verify TCP/IP finding (Detected)
    found_tcp = False
    for call_args in collector.save_finding.call_args_list:
        args, kwargs = call_args
        if kwargs.get('entity_name') == 'TCP/IP':
            found_tcp = True
            assert "Detected" in kwargs['description']
            assert "enabled" in kwargs['description']
            break
            
    assert found_tcp, "TCP/IP finding not generated"

    print("Client Protocols collector test passed!")
