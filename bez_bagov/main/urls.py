from django.urls import path
from django.contrib import admin

from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("chat/send/",    views.send_message, name="chat-send"),
    path("chat/history/", views.history,      name="chat-history"),

    # Портфолио
    path("works/",        views.work_list,    name="work-list"),
]