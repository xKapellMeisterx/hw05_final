from django.db import models
from django.contrib.auth import get_user_model
from django.db.models import SET_NULL
from django.utils.text import Truncator

MAX_LEN_TEXT = 3
User = get_user_model()


class Group(models.Model):
    title = models.CharField(
        'Здесь будет информация о группах проекта', max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()

    def __str__(self):
        return Truncator(self.title).words(MAX_LEN_TEXT)


class Post(models.Model):
    text = models.TextField(
        help_text='Текст нового поста'
    )
    pub_date = models.DateTimeField(
        auto_now_add=True
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='posts',
        verbose_name='Автор'
    )
    group = models.ForeignKey(
        Group,
        null=True,
        blank=True,
        on_delete=SET_NULL,
        related_name='posts',
        help_text='Группа, к которой относится пост',
        verbose_name='Группа'
    )
    image = models.ImageField(
        'Картинка',
        upload_to='posts/',
        blank=True
    )

    class Meta:
        ordering = ('-pub_date',)
        verbose_name = 'Пост'
        verbose_name_plural = 'Посты'

    def __str__(self):
        return Truncator(self.text).words(MAX_LEN_TEXT)


class Comment(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments',
        null=True
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="comments",
        null=True
    )
    text = models.TextField()
    created = models.DateTimeField(auto_now_add=True)


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="follower"
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="following"
    )

