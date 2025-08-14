"""
Tests for the Recipe API endpoints.
"""
from decimal import Decimal
import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (Recipe, Tag, Ingredient)

from recipe.serializers import (RecipeSerializer,
                                RecipeDetailSerializer,)

RECIPES_URL = reverse('recipe:recipe-list')


def image_upload_url(recipe_id):
    """Create and return an image upload URL for a recipe."""
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


def detail_url(recipe_id):
    """Create and return a recipe detail URL."""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def create_recipe(user, **params):
    """Create and return a sample recipe."""
    defaults = {
        'title': 'Sample Recipe',
        'time_minutes': 30,
        'price': Decimal('5.00'),
        'description': 'Sample description for the recipe.',
        'link': 'http://example.com/recipe.pdf',
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


def create_user(**params):
    """Create and return a sample user."""
    return get_user_model().objects.create_user(**params)


class PublicRecipeApiTests(TestCase):
    """Test the publicly available recipe API."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required to access the recipe API."""
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):
    """Test the authorized user recipe API."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email='user@example.com', password='testpassword123')
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """Test retrieving a list of recipes."""
        create_recipe(user=self.user)
        create_recipe(user=self.user, title='Another Recipe')

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_recipes_limited_to_user(self):
        """Test retrieving recipes for the authenticated user only."""
        other_user = get_user_model().objects.create_user(
            'other@example.com',
            'testpassword123'
        )
        create_recipe(user=other_user, title='Other User Recipe')
        create_recipe(user=self.user, title='My Recipe')

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user).order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        """Test retrieving a recipe detail."""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        """Test creating a new recipe."""
        payload = {
            'title': 'New Recipe',
            'time_minutes': 45,
            'price': Decimal('10.00'),
            'description': 'A delicious new recipe.',
            'link': 'http://example.com/new-recipe.pdf',
        }
        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_partial_update_recipe(self):
        """Test partially updating a recipe."""
        original_link = 'https://example.com/original-recipe.pdf'
        original_title = 'Original Recipe'
        recipe = create_recipe(user=self.user, title=original_title, link=original_link)

        payload = {'title': 'Updated Recipe'}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update_recipe(self):
        """Test updating a recipe with PUT."""
        recipe = create_recipe(user=self.user)

        payload = {
            'title': 'Updated Recipe',
            'time_minutes': 60,
            'price': Decimal('15.00'),
            'description': 'An updated description.',
            'link': 'http://example.com/updated-recipe.pdf',
        }
        url = detail_url(recipe.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_update_user_returns_error(self):
        """Test that updating the user field returns an error."""
        new_user = create_user(email='user2@example.com', password='newpassword123')
        recipe = create_recipe(user=self.user)

        payload = {'user': new_user.id}
        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """Test deleting a recipe."""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_delete_other_users_recipe_error(self):
        """Test trying to delete another user's recipe returns an error."""
        other_user = create_user(email='user2@example.com', password='newpassword123')
        recipe = create_recipe(user=other_user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_tags(self):
        """Test creating a recipe with tags."""
        payload = {
            'title': 'Recipe with Tags',
            'time_minutes': 30,
            'price': Decimal('7.50'),
            'tags': [{'name': 'Tag1'}, {'name': 'Tag2'}],
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in recipe.tags.all():
            self.assertEqual(tag.user, self.user)
            self.assertIn(tag.name, ['Tag1', 'Tag2'])

    def test_create_recipe_with_existing_tags(self):
        """Test creating a recipe with existing tags."""
        tag1 = Tag.objects.create(user=self.user, name='Tag1')
        payload = {
            'title': 'Recipe with Existing Tags',
            'time_minutes': 20,
            'price': Decimal('4.00'),
            'description': 'A recipe that uses existing tags.',
            'link': 'http://example.com/recipe-existing-tags.pdf',
            'tags': [{'name': 'Tag1'}, {'name': 'Tag2'}],
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag1, recipe.tags.all())

        for tag in recipe.tags.all():
            self.assertEqual(tag.user, self.user)
            self.assertIn(tag.name, ['Tag1', 'Tag2'])

    def test_create_tag_on_update(self):
        """Test creating a new tag when updating a recipe."""
        recipe = create_recipe(user=self.user)

        payload = {'tags': [{'name': 'New Tag'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(name='New Tag', user=self.user)
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assigns_tags(self):
        """Test updating a recipe assigns existing tags."""
        tag1 = Tag.objects.create(user=self.user, name='Tag1')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag1)

        tag2 = Tag.objects.create(user=self.user, name='Tag2')
        payload = {'tags': [{'name': 'Tag2'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag2, recipe.tags.all())
        self.assertNotIn(tag1, recipe.tags.all())

    def test_clear_recipe_tags(self):
        """Test clearing tags from a recipe."""
        tag1 = Tag.objects.create(user=self.user, name='Tag1')
        tag2 = Tag.objects.create(user=self.user, name='Tag2')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag1, tag2)

        payload = {'tags': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)

    def test_create_recipe_with_ingredients(self):
        """Test creating a recipe with ingredients."""
        payload = {
            'title': 'Recipe with Ingredients',
            'time_minutes': 25,
            'price': Decimal('6.00'),
            'ingredients': [{'name': 'Flour'}, {'name': 'Sugar'}],
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        for ingredient in recipe.ingredients.all():
            self.assertEqual(ingredient.user, self.user)
            self.assertIn(ingredient.name, ['Flour', 'Sugar'])

    def test_create_recipe_with_existing_ingredients(self):
        """Test creating a recipe with existing ingredients."""
        ingredient1 = Ingredient.objects.create(user=self.user, name='Flour')
        payload = {
            'title': 'Recipe with Existing Ingredients',
            'time_minutes': 15,
            'price': Decimal('3.50'),
            'description': 'A recipe that uses existing ingredients.',
            'link': 'http://example.com/recipe-existing-ingredients.pdf',
            'ingredients': [{'name': 'Flour'}, {'name': 'Sugar'}],
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ingredient1, recipe.ingredients.all())

        for ingredient in recipe.ingredients.all():
            self.assertEqual(ingredient.user, self.user)
            self.assertIn(ingredient.name, ['Flour', 'Sugar'])

    def test_create_ingredient_on_update(self):
        """Test creating a new ingredient when updating a recipe."""
        recipe = create_recipe(user=self.user)

        payload = {'ingredients': [{'name': 'New Ingredient'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_ingredient = Ingredient.objects.get(name='New Ingredient', user=self.user)
        self.assertIn(new_ingredient, recipe.ingredients.all())

    def test_update_recipe_assigns_ingredients(self):
        """Test updating a recipe assigns existing ingredients."""
        ingredient1 = Ingredient.objects.create(user=self.user, name='Flour')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient1)

        ingredient2 = Ingredient.objects.create(user=self.user, name='Sugar')
        payload = {'ingredients': [{'name': 'Sugar'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient2, recipe.ingredients.all())
        self.assertNotIn(ingredient1, recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):
        """Test clearing ingredients from a recipe."""
        ingredient1 = Ingredient.objects.create(user=self.user, name='Flour')
        ingredient2 = Ingredient.objects.create(user=self.user, name='Sugar')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient1, ingredient2)

        payload = {'ingredients': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)

    def test_filter_recipes_by_tags(self):
        """Test filtering recipes by tags."""
        recipe1 = create_recipe(user=self.user, title='Recipe with Tag1')
        recipe2 = create_recipe(user=self.user, title='Recipe with Tag2')
        tag1 = Tag.objects.create(user=self.user, name='Tag1')
        tag2 = Tag.objects.create(user=self.user, name='Tag2')
        recipe1.tags.add(tag1)
        recipe2.tags.add(tag2)
        recipe3 = create_recipe(user=self.user, title='Recipe with Both Tags')

        res = self.client.get(RECIPES_URL, {'tags': f'{tag1.id},{tag2.id}'})

        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        serializer3 = RecipeSerializer(recipe3)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_recipes_by_ingredients(self):
        """Test filtering recipes by ingredients."""
        recipe1 = create_recipe(user=self.user, title='Recipe with Ingredient1')
        recipe2 = create_recipe(user=self.user, title='Recipe with Ingredient2')
        ingredient1 = Ingredient.objects.create(user=self.user, name='Ingredient1')
        ingredient2 = Ingredient.objects.create(user=self.user, name='Ingredient2')
        recipe1.ingredients.add(ingredient1)
        recipe2.ingredients.add(ingredient2)
        recipe3 = create_recipe(user=self.user, title='Recipe with Both Ingredients')

        res = self.client.get(RECIPES_URL, {'ingredients': f'{ingredient1.id},{ingredient2.id}'})

        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        serializer3 = RecipeSerializer(recipe3)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)


class RecipeImageUploadTests(TestCase):
    """Test image upload functionality for recipes."""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'user@example.com',
            'testpassword123'
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self):
        """Clean up temporary files created during tests."""
        self.recipe.image.delete()

    def test_upload_image_to_recipe(self):
        """Test uploading an image to a recipe."""
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as temp_file:
            img = Image.new('RGB', (100, 100))
            img.save(temp_file, format='JPEG')
            temp_file.seek(0)

            res = self.client.post(url, {'image': temp_file}, format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image fails."""
        url = image_upload_url(self.recipe.id)
        res = self.client.post(url, {'image': 'notanimage'}, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(self.recipe.image)
