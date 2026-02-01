from django.urls import path
from . import views

urlpatterns = [
    path('', views.IndexPage.as_view(), name='index'),
    path('login/', views.LoginPage.as_view(), name='login'),
    path('logout/', views.LogoutPage.as_view(), name='logout'),
    path('signup/', views.RegisterPage.as_view(), name='register'),
    path('lost-password/', views.LostPasswordPage.as_view(), name='lost-password'),
    path('restore-password/', views.RestorePasswordPage.as_view(), name='restore-password'),
    path('verify/', views.VerifyPage.as_view(), name='verify'),
    path('account/', views.AccountPage.as_view(), name='account'),
    path('pricing/', views.PricingPage.as_view(), name='pricing'),
    path('checkout/', views.CheckoutPage.as_view(), name='checkout'),
    path('contact/', views.ContactPage.as_view(), name='contact'),
    path('about/', views.AboutPage.as_view(), name='about'),
    path('terms/', views.TermsPage.as_view(), name='terms'),
    path('privacy/', views.PrivacyPage.as_view(), name='privacy'),
    path('refund/', views.RefundPage.as_view(), name='refund'),
    path('success/', views.SuccessPage.as_view(), name='success'),
    path('cancel/', views.CancelSubscriptionPage.as_view(), name='cancel'),
    path('delete-account/', views.DeleteAccountPage.as_view(), name='delete'),
]
