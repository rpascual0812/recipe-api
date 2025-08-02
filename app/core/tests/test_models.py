"""
Tests for models in the core application.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model


class ModelTests(TestCase):
    """Test models in the core application."""
    def test_create_user_with_email_successful(self):
        """Test creating a user with an email is successful."""
        email = "test@example.com"
        password = "testpass123"
        user = get_user_model().objects.create_user(
            email=email,
            password=password
        )

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_new_user_email_normalized(self):
        """Test the email for a new user is normalized."""
        sample_emails = [
            ['test1@EXAMPLE.com', 'test1@example.com'],
            ['Test2@Example.com', 'Test2@example.com'],
            ['TEST3@EXAMPLE.COM', 'TEST3@example.com'],
            ['test4@example.COM', 'test4@example.com']
        ]
        for email, expected in sample_emails:
            user = get_user_model().objects.create_user(email, 'test123')
            self.assertEqual(user.email, expected)

    def test_new_user_without_email_raises_error(self):
        """Test creating user without an email raises ValueError."""
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user('', 'test123')

    def test_create_superuser_with_email_successful(self):
        """Test creating a superuser with an email is successful."""
        user = get_user_model().objects.create_superuser(
            email="admin@example.com",
            password='testpass123'
        )

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
