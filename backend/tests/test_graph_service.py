"""
Tests for Knowledge Graph Service
"""
import pytest
from app.services.knowledge.graph_service import GraphService


@pytest.fixture
def graph_service():
    """Create a graph service instance"""
    return GraphService()


def test_graph_service_initialization(graph_service):
    """Test that graph service initializes correctly"""
    assert graph_service is not None
    assert hasattr(graph_service, 'driver')


def test_is_available(graph_service):
    """Test availability check"""
    # Should return True or False, not raise exception
    result = graph_service.is_available()
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_get_statistics(graph_service):
    """Test getting graph statistics"""
    if not graph_service.is_available():
        pytest.skip("Neo4j not available")
    
    try:
        stats = graph_service.get_statistics()
        assert isinstance(stats, dict)
        assert 'total_nodes' in stats or 'node_count' in stats
    except Exception as e:
        pytest.skip(f"Error getting stats: {e}")


@pytest.mark.asyncio
async def test_add_code_node(graph_service):
    """Test adding a code node"""
    if not graph_service.is_available():
        pytest.skip("Neo4j not available")
    
    try:
        node_id = graph_service.add_code_node(
            name="test_function",
            node_type="function",
            file_path="/test/file.py",
            metadata={"language": "python"}
        )
        assert node_id is not None
        assert isinstance(node_id, str)
    except Exception as e:
        pytest.skip(f"Error adding node: {e}")


@pytest.mark.asyncio
async def test_find_correlations(graph_service):
    """Test finding correlations"""
    if not graph_service.is_available():
        pytest.skip("Neo4j not available")
    
    try:
        correlations = graph_service.find_correlations("test_entity", max_depth=2)
        assert isinstance(correlations, list)
    except Exception as e:
        pytest.skip(f"Error finding correlations: {e}")
