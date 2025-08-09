"""
Serializers for the Recipe model in the recipe app.
"""
from rest_framework import serializers
from core.models import (Recipe, Tag)


class TagSerializer(serializers.ModelSerializer):
    """Serializer for the Tag model."""

    class Meta:
        model = Tag
        fields = ('id', 'name')
        read_only_fields = ('id',)


class RecipeSerializer(serializers.ModelSerializer):
    """Serializer for the Recipe model."""
    tags = TagSerializer(many=True, required=False)

    class Meta:
        model = Recipe
        fields = ('id', 'title', 'time_minutes', 'price', 'description', 'link', 'tags')
        read_only_fields = ('id',)

    def _get_or_create_tags(self, tags_data, recipe=None):
        """Get or create tags for the recipe."""
        for tag_data in tags_data:
            tag, created = Tag.objects.get_or_create(
                user=self.context['request'].user,
                **tag_data
            )
            recipe.tags.add(tag)

    def create(self, validated_data):
        """Create a new recipe with associated tags."""
        tags_data = validated_data.pop('tags', [])
        recipe = Recipe.objects.create(**validated_data)
        self._get_or_create_tags(tags_data, recipe)

        return recipe

    def update(self, instance, validated_data):
        """Update a recipe and its associated tags."""
        tags_data = validated_data.pop('tags', None)
        if tags_data is not None:
            instance.tags.clear()
            self._get_or_create_tags(tags_data, instance)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class RecipeDetailSerializer(RecipeSerializer):
    """Serializer for detailed view of the Recipe model."""

    class Meta(RecipeSerializer.Meta):
        fields = RecipeSerializer.Meta.fields + ('description',)
