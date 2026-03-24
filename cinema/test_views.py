from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIES_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_movie(**params):
    defaults = {
        "title": "Sample Movie",
        "description": "Sample description",
        "duration": 120,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIES_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="testpass"
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie()
        sample_movie(title="Another Movie")
        res = self.client.get(MOVIES_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_by_title(self):
        movie1 = sample_movie(title="Titanic")
        movie2 = sample_movie(title="Inception")
        res = self.client.get(MOVIES_URL, {"title": "tit"})
        self.assertIn(MovieListSerializer(movie1).data, res.data)
        self.assertNotIn(MovieListSerializer(movie2).data, res.data)

    def test_filter_by_genres(self):
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")
        genre = Genre.objects.create(name="Drama")
        movie1.genres.add(genre)
        res = self.client.get(MOVIES_URL, {"genres": genre.id})
        self.assertIn(MovieListSerializer(movie1).data, res.data)
        self.assertNotIn(MovieListSerializer(movie2).data, res.data)

    def test_filter_by_actors(self):
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")
        actor = Actor.objects.create(first_name="John", last_name="Doe")
        movie1.actors.add(actor)
        res = self.client.get(MOVIES_URL, {"actors": actor.id})
        self.assertIn(MovieListSerializer(movie1).data, res.data)
        self.assertNotIn(MovieListSerializer(movie2).data, res.data)

    def test_retrieve_movie(self):
        movie = sample_movie()
        movie.genres.add(Genre.objects.create(name="Drama"))
        url = detail_url(movie.id)
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "New Movie",
            "description": "Description",
            "duration": 120,
        }
        res = self.client.post(MOVIES_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com",
            password="testpass",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genre = Genre.objects.create(name="Drama")
        actor = Actor.objects.create(first_name="John", last_name="Doe")
        payload = {
            "title": "New Movie",
            "description": "Description",
            "duration": 120,
            "genres": [genre.id],
            "actors": [actor.id],
        }
        res = self.client.post(MOVIES_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.title, payload["title"])
        self.assertIn(genre, movie.genres.all())
        self.assertIn(actor, movie.actors.all())

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
