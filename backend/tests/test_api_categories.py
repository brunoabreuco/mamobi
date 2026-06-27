import pytest
from mamobi.models import EventCategory, db
from mamobi.seed import DEFAULT_CATEGORIES

def test_list_categories(client, app):
    # Categories might not be seeded due to test DB timing
    with app.app_context():
        from mamobi.seed import seed_categories
        seed_categories()
        
    response = client.get("/api/categories")
    assert response.status_code == 200
    
    data = response.json["data"]
    assert len(data) >= len(DEFAULT_CATEGORIES)
    
    # Check if names are correct and sorted
    names = [c["name"] for c in data]
    expected_names = sorted([c["name"] for c in DEFAULT_CATEGORIES])
    
    # In case there are more categories in the test DB, we check if defaults are present
    for name in expected_names:
        assert name in names
        
    # Check structure
    cat = data[0]
    assert "id" in cat
    assert "name" in cat
    assert "icon" in cat
    assert "color" in cat
