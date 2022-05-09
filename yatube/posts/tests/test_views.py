from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from django import forms

from ..forms import PostForm
from ..models import Group, Follow, Post

User = get_user_model()
POSTS_COUNT = 13


class PostViewsTests(TestCase):

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
            group=cls.group
        )
        cls.url_post_index = reverse('posts:index')
        cls.url_post_follow_index = reverse('posts:follow_index')
        cls.url_post_group_list = reverse(
            'posts:group_list', kwargs={'slug': 'Test_slug'}
        )
        cls.url_post_create = reverse('posts:post_create')
        cls.url_post_profile = reverse(
            'posts:profile', kwargs={'username': cls.user.username}
        )
        cls.url_post_detail = reverse(
            'posts:post_detail', kwargs={'post_id': f'{cls.post.pk}'}
        )
        cls.url_post_create_authorized_client_author = reverse(
            'posts:post_edit', kwargs={'post_id': f'{cls.post.pk}'}
        )
        cls.url_post_profile_follow = reverse(
            'posts:profile_follow', kwargs={'username': f'{cls.post.author}'}
        )
        cls.url_post_profile_unfollow = reverse(
            'posts:profile_unfollow', kwargs={'username': f'{cls.post.author}'}
        )
        cls.form = PostForm()

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(self.user)
        self.user_follower = User.objects.create_user(username='Follower')
        self.authorized_client_follower = Client()
        self.authorized_client_follower.force_login(self.user_follower)
        self.form_fields = {
            'group': forms.fields.ChoiceField,
            'text': forms.fields.CharField,
        }
        self.templates_pages_names_guest = {
            'posts/index.html': self.url_post_index,
            'posts/group_list.html': self.url_post_group_list,
            'posts/profile.html': self.url_post_profile,
        }
        post_create = 'posts/post_create.html'
        self.templates_pages_names_authorized = {
            'posts/post_detail.html': self.url_post_detail,
            'posts/post_create.html': self.url_post_create,
            post_create: self.url_post_create_authorized_client_author
        }

    def compare_posts(self, post_obj_from_db, post_obj_from_context):
        """Функция сравнивания содержимого полей двух постов."""
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_fields = {
            'text': self.post.text,
            'group': Group.objects.get(slug='Test_slug').id,
            'image': uploaded
        }
        self.authorized_client_author.post(
            reverse('posts:post_edit', kwargs={'post_id': f'{self.post.id}'}),
            data=form_fields,
            follow=True
        )
        compare_params = ('author', 'text', 'group', 'image')
        for field_name in compare_params:
            with self.subTest():
                self.assertEqual(
                    getattr(post_obj_from_db, field_name),
                    getattr(post_obj_from_context, field_name)
                )

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        self.templates_pages_names_guest.update(
            self.templates_pages_names_authorized)
        for template, reverse_name in self.templates_pages_names_guest.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """Шаблон index страницы сформирован с правильным контекстом."""
        response = self.authorized_client.get(self.url_post_index)
        first_object = response.context['page_obj'][0]
        PostViewsTests.compare_posts(self, first_object, self.post)

    def test_group_posts_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            self.url_post_group_list)
        first_object = response.context['group']
        context_dict_expected_value = {
            first_object.title: self.group.title,
            first_object.slug: self.group.slug,
            first_object.description: self.group.description,
        }
        for context_key, expected in context_dict_expected_value.items():
            with self.subTest():
                self.assertEqual(context_key, expected)

    def test_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(self.url_post_profile)
        first_object = response.context['page_obj'][0]
        PostViewsTests.compare_posts(self, first_object, self.post)

    def test_post_detail_pages_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = (self.authorized_client.get(self.url_post_detail))
        first_object = response.context.get('post')
        PostViewsTests.compare_posts(self, first_object, self.post)

    def test_post_create_page_show_correct_context(self):
        """Шаблон post_create сформированы с правильной формой поста."""
        response = self.authorized_client.get(self.url_post_create)
        for value, expected in self.form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_page_show_correct_context(self):
        """Шаблон edit_post сформированы с правильной формой поста."""
        response = self.authorized_client_author.get(
            self.url_post_create_authorized_client_author)
        for value, expected in self.form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_appears_on_correct_pages(self):
        """Проверка появления поста на главной, групповой страницах и странице
        поста."""
        urls = (self.url_post_index,
                self.url_post_group_list,
                self.url_post_detail
                )
        for url in urls:
            with self.subTest(url=url):
                response = self.authorized_client_author.get(url)
                self.assertContains(response, self.post.pk)

    def test_paginator(self):
        """Проверка пагинатора"""
        Post.objects.bulk_create([Post(
            author=self.user,
            text='Тестовый пост',
            group=self.group) for i in range(POSTS_COUNT)
        ])
        post_per_page_first = 10
        post_per_page_second = 4
        data_page = (
            (1, post_per_page_first),
            (2, post_per_page_second)
        )
        for _, reverse_name in self.templates_pages_names_guest.items():
            with self.subTest(reverse_name=reverse_name):
                for page, count in data_page:
                    response = self.authorized_client.get(
                        reverse_name, {'page': page}
                    )
                    self.assertEqual(
                        len(response.context['page_obj']), count
                    )

    def test_cache_timeout(self):
        """Проверяем, что кэш страницы index работает."""
        response = self.authorized_client_author.get(self.url_post_index)
        Post.objects.filter(pk=self.post.pk).delete()
        new_response = self.authorized_client_author.get(self.url_post_index)
        self.assertEqual(response.content, new_response.content)
        cache.clear()
        check_response = self.authorized_client_author.get(self.url_post_index)
        self.assertNotEqual(response.content, check_response.content)

    def test_authorized_user_can_subscribe_unsubscribe(self):
        """Проверяем, что авторизованный пользователь
        может подписываться на других пользователей и отписываться от них."""
        subscribe_count = Follow.objects.count()
        self.authorized_client_follower.get(self.url_post_profile_follow)
        create_new_subscribe_count = Follow.objects.count()
        self.assertEqual(subscribe_count + 1, create_new_subscribe_count)
        self.authorized_client_follower.get(self.url_post_profile_unfollow)
        del_new_subscribe_count = Follow.objects.count()
        self.assertEqual(subscribe_count, del_new_subscribe_count)

    def test_authorized_user_cannot_subscribe_to_himself(self):
        """Проверяем, что авторизованный пользователь
        не может подписываться на самого себя."""
        subscribe_count = Follow.objects.count()
        self.authorized_client_author.get(self.url_post_profile_follow)
        new_subscribe_count = Follow.objects.count()
        self.assertEqual(subscribe_count, new_subscribe_count)

    def test_new_post_appears_in_follow_index(self):
        """Проверяем, что новая запись пользователя появляется в ленте тех,
        кто на него подписан и не появляется в ленте тех, кто не подписан."""
        self.authorized_client_follower.get(self.url_post_profile_follow)
        response = self.authorized_client_author.get(
            self.url_post_follow_index
        )
        self.assertContains(response, self.post.pk)
        response = self.authorized_client.get(self.url_post_follow_index)
        post_object = response.context['page_obj']
        self.assertEqual(len(post_object), 0)
