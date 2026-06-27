import os
from pathlib import Path
from mamobi.models import EventCategory, db
from mamobi.seed import DEFAULT_CATEGORIES, IMAGES_DIR

def test_seed_categories(app):
    with app.app_context():
        from mamobi.seed import seed_categories
        seed_categories()
        
        # Check if all default categories were created
        for cat_data in DEFAULT_CATEGORIES:
            cat = db.session.execute(
                db.select(EventCategory).where(EventCategory.name == cat_data["name"])
            ).scalar()
            
            assert cat is not None, f"Category {cat_data['name']} not found"
            assert cat.color == cat_data["color"]
            
            expected_url = f"/images/{cat_data['filename']}"
            assert cat.icon == expected_url
            
            # Check if file exists on disk
            svg_file = IMAGES_DIR / cat_data["filename"]
            assert svg_file.exists(), f"SVG file {svg_file} missing"
            
        # Verify count
        total = db.session.execute(db.select(db.func.count(EventCategory.id))).scalar()
        assert total >= len(DEFAULT_CATEGORIES)

def test_seed_idempotency(app):
    with app.app_context():
        from mamobi.seed import seed_categories
        
        # Ensure initial seed
        seed_categories()
        
        # Count before
        count1 = db.session.execute(db.select(db.func.count(EventCategory.id))).scalar()
        
        # Seed again
        seed_categories()
        
        # Count after
        count2 = db.session.execute(db.select(db.func.count(EventCategory.id))).scalar()
        
        assert count1 == count2, "Seeding is not idempotent"
