from django.urls import path

from . import views

urlpatterns = [
    # Чат
    path("chat/send/",    views.send_message, name="chat-send"),
    path("chat/history/", views.history,      name="chat-history"),

    # Портфолио
    path("works/",        views.work_list,    name="work-list"),
]