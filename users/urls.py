from django.urls import path
from .views import LoginAndJWTView

urlpatterns = [
    path('login/', LoginAndJWTView.as_view(), name='login_and_jwt'),
]

