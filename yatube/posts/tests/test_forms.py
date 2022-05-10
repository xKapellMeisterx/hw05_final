import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..forms import PostForm
from ..models import Comment, Post, Group

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TaskCreateFormTests(TestCase):
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
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='HasNoName')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(TaskCreateFormTests.user)

    def test_create_post(self):
        """Проверяем, что пост создается через форму."""
        tasks_count = Post.objects.count()
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
        form_data = {
            'text': 'Непохожий на меня, непохожий на тебя',
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response, reverse('posts:profile',
                              kwargs={'username': 'HasNoName'}))
        self.assertEqual(Post.objects.count(), tasks_count + 1)
        self.assertTrue(
            Post.objects.filter(
                author=self.user,
                text='Непохожий на меня, непохожий на тебя',
                group=self.group.id,
                image='posts/small.gif'
            ).exists()
        )
        response_group = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': 'Test_slug'})
        )
        first_object = response_group.context['page_obj'][0]
        self.assertEqual(
            first_object.text, 'Непохожий на меня, непохожий на тебя'
        )

    def test_post_edit_if_valid_form(self):
        """Проверяем, что пост редактируется через форму."""
        form_fields = {
            'text': 'Очень много сложного текста',
            'group': self.group.pk
        }
        response = self.authorized_client_author.post(
            reverse('posts:post_edit', kwargs={'post_id': f'{self.post.id}'}),
            data=form_fields,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': f'{self.post.id}'}
        ))
        self.assertTrue(
            Post.objects.filter(
                text='Очень много сложного текста',
                group=self.group.pk
            ).exists()
        )

    def test_auth_user_can_edit_post(self):
        """Проверяем, что пост появился на всех страницах."""
        urls = (reverse('posts:index'),
                reverse('posts:profile', args=(self.user.username,)),
                reverse('posts:post_detail',
                        kwargs={'post_id': f'{self.post.id}'}),
                reverse('posts:group_list', args=(self.group.slug,)),
                )

        for url in urls:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertContains(response, self.post.pk)

    def test_comment_post_authorized_user(self):
        """Проверяем, что авторизованный пользователь
        может комментировать пост."""
        form_fields = {
            'text': 'Текст коментатора',
        }
        response = self.authorized_client_author.post(
            reverse('posts:add_comment', args=[self.post.pk]),
            data=form_fields,
            follow=True
        )
        self.assertRedirects(
            response, reverse('posts:post_detail', args=[self.post.pk])
        )
        self.assertTrue(
            Comment.objects.filter(
                text=form_fields['text'],
                author=TaskCreateFormTests.user,
                post=self.post.pk
            ).exists()
        )

    def test_comment_post_unauthorized_user(self):
        """Проверяем, что неавторизированный пользователь
        не может комментировать пост."""
        form_fields = {
            'text': 'Текст коментатора',
        }
        response = self.guest_client.post(
            reverse('posts:add_comment', args=[self.post.pk]),
            data=form_fields,
            follow=True
        )
        self.assertRedirects(
            response,
            f'/auth/login/?next=/posts/{self.post.pk}/comment/'
        )
        self.assertFalse(
            Comment.objects.filter(
                text=form_fields['text'],
                author=self.user,
                post=self.post.pk
            ).exists()
        )
