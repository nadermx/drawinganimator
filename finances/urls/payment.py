from django.urls import path

from finances.views.payment import *

urlpatterns = [
    path('coinbase', CoinbaseIPN.as_view()),
    path('paypal-order', PaymentPaypal.as_view(), name='api_payment_paypal'),
    path('paypal', PaypalIPN.as_view()),
]
