from django.urls import path
from .views import LoginAndJWTView, UserProfileView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('login/', LoginAndJWTView.as_view(), name='login_and_jwt'),
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
