from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.contrib.auth.views import LogoutView
from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'groups', views.GroupViewSet)
router.register(r'societies', views.SocietyViewSet)
router.register(r'profiles', views.UserProfileViewSet)
router.register(r'claims', views.ClaimViewSet)
router.register(r'receipts', views.ReceiptViewSet)
router.register(r'bank-details', views.BankDetailsViewSet, basename='bank-details')

urlpatterns = [
    path('', include(router.urls)),
    path('logout/', LogoutView.as_view(), name='logout'),
]
