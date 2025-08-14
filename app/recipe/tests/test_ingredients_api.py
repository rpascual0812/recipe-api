"""
Tests for Ingredient API endpoints.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (Ingredient, Recipe)
from recipe.serializers import IngredientSerializer

INGREDIENTS_URL = reverse('recipe:ingredient-list')


def detail_url(ingredient_id):
    """Create and return an ingredient detail URL."""
    return reverse('recipe:ingredient-detail', args=[ingredient_id])


def create_user(email='user@example.com', password='password123'):
    """Create and return a sample user."""
    return get_user_model().objects.create_user(email=email, password=password)


class PublicIngredientApiTests(TestCase):
    """Test the publicly available ingredient API."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required to access the ingredient API."""
        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientApiTests(TestCase):
    """Test the authorized user ingredient API."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients(self):
        """Test retrieving a list of ingredients."""
        Ingredient.objects.create(user=self.user, name='Salt')
        Ingredient.objects.create(user=self.user, name='Pepper')

        res = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        """Test that only ingredients for the authenticated user are returned."""
        user2 = create_user(email='other@example.com', password='testpass123')
        Ingredient.objects.create(user=user2, name='Vinegar')
        ingredient = Ingredient.objects.create(user=self.user, name='Turmeric')

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], ingredient.name)
        self.assertEqual(res.data[0]['id'], ingredient.id)

    def test_update_ingredient(self):
        """Test updating an ingredient."""
        ingredient = Ingredient.objects.create(user=self.user, name='Cumin')
        payload = {'name': 'Cumin Powder'}

        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload['name'])

    def test_delete_ingredient(self):
        """Test deleting an ingredient."""
        ingredient = Ingredient.objects.create(user=self.user, name='Oregano')

        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Ingredient.objects.filter(id=ingredient.id).exists())

    def test_filter_ingredients_assigned_to_recipes(self):
        """Test listing ingredients assigned to recipes."""
        ingredient1 = Ingredient.objects.create(user=self.user, name='Garlic')
        ingredient2 = Ingredient.objects.create(user=self.user, name='Onion')
        recipe = Recipe.objects.create(
            user=self.user,
            title='Garlic Bread',
            time_minutes=10,
            price=Decimal('2.50'),
            description='Delicious garlic bread',
            link='http://example.com/garlic-bread'
        )
        recipe.ingredients.add(ingredient1)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        serializer1 = IngredientSerializer(ingredient1)
        serializer2 = IngredientSerializer(ingredient2)
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_filter_ingredients_assigned_unique(self):
        """Test filtering ingredients assigned to recipes returns unique items."""
        ingredient1 = Ingredient.objects.create(user=self.user, name='Basil')
        ingredient2 = Ingredient.objects.create(user=self.user, name='Parsley')
        recipe1 = Recipe.objects.create(
            user=self.user,
            title='Pasta',
            time_minutes=15,
            price=Decimal('3.00'),
            description='Pasta with basil',
            link='http://example.com/pasta'
        )
        recipe1.ingredients.add(ingredient1)
        recipe2 = Recipe.objects.create(
            user=self.user,
            title='Salad',
            time_minutes=5,
            price=Decimal('1.50'),
            description='Salad with basil and parsley',
            link='http://example.com/salad'
        )
        recipe2.ingredients.add(ingredient1, ingredient2)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 2)
        # self.assertIn(IngredientSerializer(ingredient1).data, res.data)
        # self.assertIn(IngredientSerializer(ingredient2).data, res.data)
