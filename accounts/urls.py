from django.urls import path

from accounts.views import *

urlpatterns = [
    path('rate_limit/', RateLimit.as_view(), name='rate-limit'),
    path('consume/', CreditsConsume.as_view(), name='credits-consume'),
    path('resend-verification/', ResendVerificationEmail.as_view(), name='resend-verification'),
    path('cancel-subscription/', CancelSubscription.as_view(), name='cancel-subscription'),
]
