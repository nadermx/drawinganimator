import json

from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from finances.models.payment import Payment


@method_decorator(csrf_exempt, name='dispatch')
class CoinbaseIPN(View):
    def post(self, request):
        webhook = json.loads(request.body)
        event = webhook.get('event')
        data = event.get('data')
        payment_code = data.get('code')
        metadata = data.get('metadata')
        event_type = event.get('type')
        plan_name = data.get('name', '').lower()
        email = metadata.get('custom', '').lower()

        if email:
            email = email.lower()

        Payment.coinbase_ipn(email, plan_name, payment_code, event_type, webhook)

        return HttpResponse({'status': True})


class PaymentPaypal(APIView):
    def post(self, request):
        data = request.data
        from finances.models.payment import Payment
        order_id, subs_link, errors = Payment.create_paypal_order_or_subscription(request.user, data)

        if not order_id and not subs_link:
            return Response({'error': errors}, status=status.HTTP_400_BAD_REQUEST)

        if order_id:
            return Response({'id': order_id})
        else:
            return Response({'link': subs_link})


@method_decorator(csrf_exempt, name='dispatch')
class PaypalIPN(APIView):
    def post(self, request):
        webhook = request.data

        if not webhook:
            print('Paypal webhook empty')
            return HttpResponse({'status': True})

        payment, errors = Payment.save_ipn_response(webhook)

        if errors:
            print('Paypal webhook error: %s' % errors)

        return HttpResponse({'status': True})
