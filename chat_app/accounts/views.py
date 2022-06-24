from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView, DestroyAPIView, UpdateAPIView,ListAPIView,RetrieveAPIView
from rest_framework import status
from rest_framework.response import Response

from django.conf import settings
from django.core.mail import send_mail

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import UserLoginSerializer, UserRegisterSerializer
from .models import User
from config.redisConnection import *

import random
import string


class LoginView(TokenObtainPairView):
    serializer_class = UserLoginSerializer
    permission_classes = [permissions.AllowAny]
    queryset = User.objects.all()
    

class RegistrationView(APIView):
    permission_classes = [permissions.AllowAny]#first all permissions are allowed
    
    def post(self, request):
        #check if email and username is in request data . if not ???
        if "email" in request.data:
            #if email was written in requested data , the user is searched in database
            user = User.objects.filter(email=request.data["email"]).first()
            if user is not None:#if the user is found and it's not active then it's deleted
                if not user.is_active:
                    user.delete()
        #if username was written in requested data , the user is searched in database.it's as same as user          
        if "username" in request.data:
            user = User.objects.filter(username=request.data["username"]).first()
            if user is not None:
                if not user.is_active:
                    user.delete()

        data = UserRegisterSerializer(data=request.data)#the data is sent to front 
        #the validations is set.
        data.is_valid(raise_exception=True)
        data.save()
        code = ''.join(random.choice(string.digits) for i in range(5))#5 digit code with 300s duration is made
        is_set = redis_conn.set(code, request.data["email"], 300, nx=True)#check if the 5 digit code is set correctly in database . nx????
            #the email is sent
            subject = 'verification code for chat app'
            message = code
            email_from = settings.EMAIL_HOST_USER
            recipient_list = [request.data['email'],]
            send_mail( subject, message, email_from, recipient_list, fail_silently=False)
        #the function returns the validation of user
        return Response(data.data, status=status.HTTP_200_OK)
    

class VerifyEmailView(APIView): 
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        #in previous for verification of email , a 5 digit code was sent . here we gonna get that 5 digit .
        if 'code' in request.data:#if the code was written , this part is gonna check if it's true .
            code = request.data['code']
            validation_code = redis_conn.get(code)#check if the written code is as same as the code in database
            if validation_code is not None:#if the code was valid :???
                email = validation_code
                user = User.objects.get(email=email)
                if user is not None:#if the 5 digit code was written correctly the user is saved and activated
                    refresh = RefreshToken.for_user(user)
                    user.active = True
                    user.save()
                    data = {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                        'message': "email verified successfully",
                    }
                    #errors which is discussed in .view
                    return Response(data=data, status=status.HTTP_200_OK)
                return Response(data={"invalid code"}, status=status.HTTP_400_BAD_REQUEST)
            return Response(data={"invalid code"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data={"field code is required"}, status=status.HTTP_400_BAD_REQUEST)
