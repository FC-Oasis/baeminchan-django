from random import randint

from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from rest_framework import generics, permissions, status, mixins, serializers
from rest_framework.authtoken.models import Token
from rest_framework.compat import authenticate
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from members.models import Phone
from ..serializers import UserSerializer, PasswordChangeSerializer, EmailChangeSerializer, ContactPhoneChangeSerializer, \
    PhoneSerializer, PhoneAuthSerializer


User = get_user_model()


class UserList(generics.ListAPIView):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer


class UserCreate(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (
        permissions.AllowAny,
    )
    serializer_class = UserSerializer


class UserDetail(mixins.DestroyModelMixin,
                 generics.GenericAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def delete(self, request, *args, **kwargs):
        user = request.user
        if request.user.is_authenticated:
            message = render_to_string('users/goodbye_email.html',
               {
                   'user': user,
               })

            mail_subject = '정상적으로 탈퇴가 완료 되었습니다.'
            to_email = user.email
            email = EmailMessage(mail_subject, message, to=[to_email])
            email.send()

        return self.destroy(request, *args, **kwargs)


class UserDetailSearch(APIView):
    def get(self, request):
        if request.user.is_authenticated:
            return Response(UserSerializer(request.user).data)
        raise NotAuthenticated('로그인을 먼저 해주세요')


class PasswordChange(APIView):
    permission_classes = (
        permissions.IsAuthenticated,
    )

    def patch(self, request, *args, **kwargs):
        serializer = PasswordChangeSerializer(request.user, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.is_valid(raise_exception=True))


class EmailChange(APIView):
    permission_classes = (
        permissions.IsAuthenticated,
    )

    def patch(self, request, *args, **kwargs):
        serializer = EmailChangeSerializer(request.user, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ContactPhoneChange(APIView):
    permission_classes = (
        permissions.IsAuthenticated,
    )

    def patch(self, request, *args, **kwargs):
        serializer = ContactPhoneChangeSerializer(request.user, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AuthToken(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)

        if user:
            token, __ = Token.objects.get_or_create(user=user)
            data = {
                'token': token.key,
            }
            return Response(data)
        raise AuthenticationFailed('인증정보가 올바르지 않습니다')


class AuthenticationTest(APIView):
    def get(self, request):
        if request.user.is_authenticated:
            return Response(UserSerializer(request.user).data)
        raise NotAuthenticated('로그인 상태가 아닙니다')


class Logout(APIView):
    """
    유저 객체를 받아 쿼리셋에 담고,
    request 받은 유저의 auth_token이 맞으면 로그아웃을 시켜줌
    """
    queryset = User.objects.all()

    def get(self, request, format=None):
        request.user.auth_token.delete()

        data = {
            'result': '정상적으로 로그아웃 되었습니다.'
        }
        return Response(data, status=status.HTTP_200_OK)


class PhoneCreate(generics.CreateAPIView, mixins.UpdateModelMixin):
    queryset = Phone.objects.all()
    permission_classes = (
        permissions.AllowAny,
    )
    serializer_class = PhoneSerializer
    lookup_field = 'contact_phone'

    def get_object(self):
        return get_object_or_404(Phone, contact_phone=self.request.data.get('contact_phone'))

    def create(self, request, *args, **kwargs):
        contact_phone = request.data.get('contact_phone')
        auth_key = str(randint(100000, 999999))
        mutable = request.data._mutable
        request.data._mutable = True
        request.data['auth_key'] = auth_key
        request.data._mutable = mutable
        response = super(PhoneCreate, self).create(request, *args, **kwargs)
        PhoneCreate.send_sms(contact_phone, auth_key)
        return response

    def patch(self, request, *args, **kwargs):
        contact_phone = request.data.get('contact_phone')
        auth_key = str(randint(100000, 999999))
        mutable = request.POST._mutable
        request.POST._mutable = True
        request.POST['auth_key'] = auth_key
        request.POST._mutable = mutable
        response = self.update(request, *args, **kwargs)
        PhoneCreate.send_sms(contact_phone, auth_key)
        return response

    @staticmethod
    def send_sms(contact_phone, auth_key):
        import requests
        from config.settings.production import secrets

        BLUEHOUSELAB_SMS_API_ID = secrets['BLUEHOUSELAB_SMS_API_ID']
        BLUEHOUSELAB_SMS_API_KEY = secrets['BLUEHOUSELAB_SMS_API_KEY']
        BLUEHOUSELAB_SENDER = secrets['BLUEHOUSELAB_SENDER']
        receiver = contact_phone.replace('-', '')
        content = f'[배민찬COPY] 인증번호는 {auth_key}입니다.'

        requests.post(
            'https://api.bluehouselab.com/smscenter/v1.0/sendsms',
            auth=requests.auth.HTTPBasicAuth(
                BLUEHOUSELAB_SMS_API_ID,
                BLUEHOUSELAB_SMS_API_KEY,
            ),
            headers={
                'Content-Type': 'application/json; charset=utf-8',
            },
            json={
                'sender': BLUEHOUSELAB_SENDER,
                'receivers': [receiver],
                'content': content,
            }
        )


class PhoneAuth(APIView):
    def post(self, request):
        contact_phone = request.data.get('contact_phone')
        auth_key = request.data.get('auth_key')
        obj = get_object_or_404(Phone, contact_phone=contact_phone, auth_key=auth_key)
        if obj is not None:
            created_at = obj.created_at
            now = timezone.now()

            if created_at + timezone.timedelta(minutes=5) <= now:
                raise serializers.ValidationError('인증 가능 시간이 지났습니다.')
            else:
                obj.delete()
                data = {
                    'result': '핸드폰 번호가 인증되었습니다.'
                }
                return Response(data, status=status.HTTP_200_OK)
