from django.urls import path
from .views import (
    home_view,
    signup,
    login_view,
    logout_view,
    search_view,
    pending_requests,
    friends_list,
    reject_request,
    send_request,
    accept_request,
)

urlpatterns = [
    path("signup/", signup, name="signup"),
    path("", login_view, name="login"),
    path("home/", home_view, name="home"),
    path("logout/", logout_view, name="logout"),
    path("search/", search_view, name="search"),
    path("pending-requests/", pending_requests, name="pending_requests"),
    path("friends/", friends_list, name="friends"),
    path("send_request/<int:user_id>/", send_request, name="send_request"),
    path("accept_request/<int:request_id>/", accept_request, name="accept_request"),
    path(
        "reject_request/<int:request_id>/",
        reject_request,
        name="reject_friend_request",
    ),
]
