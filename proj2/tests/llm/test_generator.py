"""
LLM-based menu generator integration tests.

These tests are marked with @pytest.mark.llm and are excluded from CI
by default in pytest.ini to prevent model loading timeouts.

To run these tests locally:
  pytest -m llm

To run all tests including LLM:
  pytest -m ""
"""
import re
import pytest
import os
import pandas as pd

import proj2.menu_generation as menu_generation
from proj2.sqlQueries import *
from proj2.Flask_app import parse_generated_menu

db_file = os.path.join(os.path.dirname(__file__), "../../CSC510_DB.db")

# Lazy initialization - only loads when tests run, not at import time
_generator_instance = None
_menu_items_cache = None

def _get_generator():
    """Lazy load generator on first access"""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = menu_generation.MenuGenerator()
    return _generator_instance

def _get_menu_items():
    """Lazy load menu items on first access"""
    global _menu_items_cache
    if _menu_items_cache is None:
        conn = create_connection(db_file)
        _menu_items_cache = pd.read_sql_query("SELECT * FROM MenuItem WHERE instock == 1", conn)
        close_connection(conn)
    return _menu_items_cache

# Module-level variables (lazily populated)
generator = None
menu_items = None

@pytest.fixture(scope="session", autouse=True)
def setup_module_vars():
    """Initialize module-level variables lazily when tests start"""
    global generator, menu_items
    generator = _get_generator()
    menu_items = _get_menu_items()


# ==================== TEST GROUPS ====================
# All tests are intentionally marked with @pytest.mark.llm
# These tests require the LLM model to load (~200MB) which is slow in CI

@pytest.mark.llm
class TestMenuGeneratorSingleMeal:
    """Tests for single meal menu generation"""
    
    def test_single_meal_generation(self):
        """Test that generator can create a menu for a single meal"""
        gen = _get_generator()
        menu = gen.update_menu(
            menu=None,
            preferences="high protein",
            allergens="Peanuts",
            date="2025-10-14",
            meal_numbers=[1]
        )
        assert menu is not None
        assert len(menu) > 0
        
    def test_single_meal_sequential(self):
        """Test sequential menu updates for single meals"""
        gen = _get_generator()
        menu1 = gen.update_menu(menu=None, preferences="high protein", allergens="", date="2025-10-14", meal_numbers=[1])
        menu2 = gen.update_menu(menu=menu1, preferences="high protein", allergens="", date="2025-10-14", meal_numbers=[2])
        assert menu1 is not None
        assert menu2 is not None


@pytest.mark.llm
class TestMenuGeneratorMultipleMeals:
    """Tests for multiple meals in a single day"""
    
    def test_multiple_meals_same_day(self):
        """Test generating menus for multiple meals in one day"""
        gen = _get_generator()
        menu = gen.update_menu(
            menu=None,
            preferences="low carb",
            allergens="Shellfish",
            date="2025-10-14",
            meal_numbers=[1, 2, 3]
        )
        assert menu is not None


@pytest.mark.llm
class TestMenuGeneratorMultipleDays:
    """Tests for multi-day menu generation"""
    
    def test_multiple_days_generation(self):
        """Test generating menus for multiple consecutive days"""
        gen = _get_generator()
        menu = gen.update_menu(
            menu=None,
            preferences="high protein",
            allergens="",
            date="2025-10-14",
            meal_numbers=[1],
            number_of_days=3
        )
        assert menu is not None


@pytest.mark.llm
class TestMenuGeneratorEdgeCases:
    """Edge case tests for menu generator"""
    
    def test_menu_with_all_allergens(self):
        """Test menu generation with multiple allergen restrictions"""
        gen = _get_generator()
        menu = gen.update_menu(
            menu=None,
            preferences="",
            allergens="Peanuts,Shellfish,Dairy",
            date="2025-10-15",
            meal_numbers=[1]
        )
        # Should still generate something even with restrictions
        assert menu is not None
        
    def test_menu_no_preferences(self):
        """Test menu generation with no dietary preferences"""
        gen = _get_generator()
        menu = gen.update_menu(
            menu=None,
            preferences="",
            allergens="",
            date="2025-10-15",
            meal_numbers=[2]
        )
        assert menu is not None
