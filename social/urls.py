from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "social"

urlpatterns = [
    path("", views.feed, name="feed"),
    path("posts/new/", views.post_create, name="post_create"),
    path("posts/<int:pk>/", views.post_detail, name="post_detail"),
    path("posts/<int:pk>/delete/", views.post_delete, name="post_delete"),
    path("posts/<int:pk>/comment/", views.comment_create, name="comment_create"),
    path("posts/<int:pk>/like/", views.like_toggle, name="like_toggle"),
    path("search/", views.search, name="search"),
    path("notifications/", views.notifications_list, name="notifications"),
    path("notifications/count/", views.notifications_unread_count, name="notifications_count"),
    path("users/<str:username>/", views.profile, name="profile"),
    path("users/<str:username>/follow/", views.follow_toggle, name="follow_toggle"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path("signup/", views.signup, name="signup"),
    path("login/", views.PersianLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
