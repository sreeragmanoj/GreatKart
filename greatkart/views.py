from django.shortcuts import render
from store.models import Product,ReviewRating

def home(request):
    products = Product.objects.all().filter(is_available=True).order_by('-created_date')

    # get stars
    for product in products:
        review = ReviewRating.objects.filter(product_id = product.id, status = True)



    context = {
        'products' : products,
        'review': review,
    }
    return render(request, 'home.html',context)