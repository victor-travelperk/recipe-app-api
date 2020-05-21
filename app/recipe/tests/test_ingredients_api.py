from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient, Recipe

from recipe.serializers import IngredientSerializer

INGREDIENTS_URL = reverse('recipe:ingredient-list')


class PublicIngredientsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_login_required(self):
        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsAPI(TestCase):

    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'test@test.com',
            'password'
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredient_list(self):
        Ingredient.objects.create(user=self.user, name='Kale')
        Ingredient.objects.create(user=self.user, name='Salt')

        res = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        user2 = get_user_model().objects.create_user(
            'other@test.com',
            'password'
        )
        Ingredient.objects.create(user=user2, name='Vinegar')
        ingredient = Ingredient.objects.create(user=self.user, name='Tumeric')

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], ingredient.name)

    def test_create_ingredient_successful(self):
        payload = {'name': 'Peperoni'}
        res = self.client.post(INGREDIENTS_URL, payload)
        exists = Ingredient.objects.all().filter(
            user=self.user,
            name=payload['name']
        ).exists()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['name'], payload['name'])

    def test_create_ingredients_invalid(self):
        payload = {'name': ''}
        res = self.client.post(INGREDIENTS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_ingredients_assigned_to_recipes(self):
        ingredient1 = Ingredient.objects.create(user=self.user, name='Salt')
        ingredient2 = Ingredient.objects.create(user=self.user, name='Pepper')
        recipe = Recipe.objects.create(
            user=self.user,
            title='Some fried eggs',
            time_minutes=7,
            price=8
        )
        recipe.ingredients.add(ingredient1)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        serializer1 = IngredientSerializer(ingredient1)
        serializer2 = IngredientSerializer(ingredient2)
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_retrieve_ingredients_assigned_unique(self):
        ingredient = Ingredient.objects.create(user=self.user, name='Lamb Sauce')
        Ingredient.objects.create(user=self.user, name='Raw Bass')
        recipe1 = Recipe.objects.create(
            title='Special Bass',
            time_minutes=30,
            price=16,
            user=self.user
        )
        recipe1.ingredients.add(ingredient)
        recipe2 = Recipe.objects.create(
            title='Posh Bass',
            time_minutes=20,
            price=60,
            user=self.user
        )

        recipe2.ingredients.add(ingredient)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)