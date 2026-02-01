var stripe = Stripe('pk_live_51JJTVXFyIAItYvcSkRa2SFeKAKx1d3P7k086PzJ3R6tEWkTDyEwOJz42lTQ16K7bWhQQQcvKA0vZYymg2sJ58m1S00KWaX9ba4');
var elements = stripe.elements();
var cardElement = elements.create('card');
var cardElement = elements.getElement('card');
cardElement.mount('#card-element');
cardElement.on('change', function (event) {
  displayError(event);
});
const btn = document.getElementById('submit');
btn.addEventListener('click', async (e) => {
  e.preventDefault();

  // Create payment method and confirm payment intent.
  stripe.confirmCardPayment(clientSecret, {
    payment_method: {
      card: cardElement,
      billing_details: {
      },
    }
  }).then((result) => {
    console.log('result', result)
    if(result.error) {
      alert(result.error.message);
    } else {
      window.location = "https://removebackground.app/success";
    }
  });
});
function displayError(event) {
  //changeLoadingStatePrices(false);
  let displayError = document.getElementById('card-element-errors');
  if (event.error) {
    displayError.textContent = event.error.message;
  } else {
    displayError.textContent = '';
  }
}