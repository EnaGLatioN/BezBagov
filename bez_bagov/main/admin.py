from django.contrib import admin
from .models import Work

@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("title", "description")