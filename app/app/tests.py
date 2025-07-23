"""
Sample test module for the app.
"""
from django.test import SimpleTestCase

from app import calc


class CalcTests(SimpleTestCase):
    """Test the calc module."""

    def test_add_numbers(self):
        """Test adding two numbers together."""
        self.assertEqual(calc.add(3, 8), 11)

    def test_substract_numbers(self):
        """Test substracting two numbers together."""
        self.assertEqual(calc.substract(15, 10), 5)
