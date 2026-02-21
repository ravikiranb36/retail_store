from django.shortcuts import render
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

# Helper function to get user roles
def get_user_roles(user):
    roles = []
    if user.is_admin():
        roles.append('Admin')
    if user.is_store_manager():
        roles.append('Store Manager')
    if user.is_customer():
        roles.append('Customer')
    return roles

@method_decorator(csrf_exempt, name='dispatch')
class LoginAndJWTView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [] # Disable authentication for this view

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'username': user.username,
                'roles': get_user_roles(user)
            })
        return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        user = request.user
        return Response({
            'username': user.username,
            'roles': get_user_roles(user)
        })
