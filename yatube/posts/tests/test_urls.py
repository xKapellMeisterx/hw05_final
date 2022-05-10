from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from ..models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )
        cls.url_edit = f'/posts/{cls.post.id}/edit/'

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='HasNoName')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(PostURLTests.user)
        self.templates_url_names = {
            'posts/index.html': '/',
            'posts/group_list.html': '/group/Test_slug/',
            'posts/profile.html': '/profile/HasNoName/',
            'posts/post_detail.html': '/posts/1/',
        }
        self.url_names_public = [
            '/', '/group/Test_slug/', '/profile/HasNoName/',
            f'/posts/{self.post.id}/']
        self.url_names_private = [
            '/create/', f'/posts/{self.post.id}/edit/'
        ]

    def test_urls_are_accessible_guest_client(self):
        """Проверяем коды HTTP для
        неавторизованного пользователя."""
        for fild in self.url_names_public:
            with self.subTest():
                response = self.guest_client.get(fild)
                self.assertEqual(response.status_code, HTTPStatus.OK)
        for fild in self.url_names_private:
            with self.subTest():
                response = self.guest_client.get(fild)
                self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_urls_are_accessible_authorized_client(self):
        """Проверяем коды HTTP для
        авторизованного пользователя."""
        self.url_names_public.extend(self.url_names_private)
        for fild in self.url_names_public:
            with self.subTest():
                response = self.authorized_client_author.get(fild)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_unexisting_page(self):
        """Проверяем код HTTP несуществующей страницы для авторизованного
        и не авторизованного пользователей."""
        for client in (self.guest_client, self.authorized_client_author):
            response_unexisting_page_guest = client.get(
                '/unexisting_page/'
            )
            self.assertEqual(
                response_unexisting_page_guest.status_code,
                HTTPStatus.NOT_FOUND
            )

    def test_urls_uses_correct_template_unexisting_page(self):
        """Проверяем что страница 404 отдает кастомный шаблон."""
        for client in (self.guest_client, self.authorized_client_author):
            response_unexisting_page_guest = client.get(
                '/unexisting_page/'
            )
            self.assertTemplateUsed(
                response_unexisting_page_guest, 'core/404.html'
            )

    def test_urls_uses_correct_template_guest_client(self):
        """URL-адрес использует соответствующий шаблон для
        неавторизованного пользователя."""
        for template, address in self.templates_url_names.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_urls_uses_correct_template_authorized_client(self):
        """URL-адрес использует соответствующий шаблондля для
        авторизованного пользователя."""
        for template, address in self.templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)
        response = self.authorized_client.get('/create/')
        self.assertTemplateUsed(response, 'posts/post_create.html')
        response = self.authorized_client_author.get(self.url_edit)
        self.assertTemplateUsed(response, 'posts/post_create.html')

    def test_of_the_right_to_create_a_post(self):
        """Проверяем доступ страницы создания поста."""
        responce = self.guest_client.get('/create/', follow=True)
        self.assertRedirects(responce, '/auth/login/?next=/create/')
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_of_the_right_to_edit_a_post(self):
        """Проверяем доступ страницы редактирования поста."""
        responce = self.guest_client.get(self.url_edit, follow=True)
        self.assertRedirects(responce, '/auth/login/?next=/posts/1/edit/')
        responce = self.authorized_client.get(self.url_edit, follow=True)
        self.assertRedirects(responce, '/posts/1/'),
        response = self.authorized_client_author.get(self.url_edit)
        self.assertEqual(response.status_code, HTTPStatus.OK)
