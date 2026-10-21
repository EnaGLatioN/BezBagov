import uuid

from django.db import models
from django.utils import timezone


def work_image_upload_to(instance, filename):
    """Разбиваем файлы по годам/месяцам, чтобы не было тысяч файлов в одной папке."""
    ext = filename.split(".")[-1].lower()
    now = timezone.now()
    return f"portfolio/{now:%Y/%m}/{uuid.uuid4().hex}.{ext}"


class Work(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="ID",
    )
    image = models.ImageField(
        upload_to=work_image_upload_to,
        verbose_name="Изображение",
        help_text="Основное фото работы",
    )
    title = models.CharField(
        max_length=255,
        verbose_name="Название",
    )
    task = models.TextField(
        blank=True,
        verbose_name="Описание",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Описание",
    )
    url = models.URLField(
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Дата создания",
    )
    status = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Активность",
    )

    class Meta:
        app_label = "main"
        db_table = "portfolio_work"  # нормальное имя таблицы
        verbose_name = "Работа"
        verbose_name_plural = "Работы"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title