from django.shortcuts import render,redirect,get_object_or_404
from . forms import RegistrationForm,UserForm,UserProfileform
from . models import Account, UserProfile
from orders.models import OrderProduct,Order
from django.contrib import messages,auth
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from carts.models import Cart,CartItem
from carts.views import _cart_id
from orders.models import Order

# VERIFICATION EMAIL

from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode,urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage
import requests

# Create your views here.

def register(request):

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            first_name   = form.cleaned_data['first_name']
            last_name    = form.cleaned_data['last_name']
            phone_number = form.cleaned_data['phone_number']
            email        = form.cleaned_data['email']
            password     = form.cleaned_data['password']
            username     = email.split('@')[0]


            user = Account.object.create_user(first_name=first_name, last_name=last_name, email=email, username=username, password=password)
            user.phone_number=phone_number
            user.save()

            # Create user profile
            profile=UserProfile()
            profile.user_id = user.id
            profile.profile_picture = 'default/default-user.png'
            profile.save()

            # USER ACTIVATION
            current_site = get_current_site(request)
            mail_subject = "Please activate your account"
            message = render_to_string('accounts/account_verification_email.html', {
                'user' : user,
                'domain' : current_site,
                'uid' : urlsafe_base64_encode(force_bytes(user.pk)),
                'token' : default_token_generator.make_token(user),

            })
            to_email=email
            send_email=EmailMessage(mail_subject, message, to=[to_email])
            send_email.send()
            # messages.success(request, 'Thank you for registering with us. We have sent you a verification email to verify your email address. Please verify it.')
            return redirect('/accounts/login/?command=verification&email='+email)

    else:
        form = RegistrationForm()
    context = {
        'form' : form,
        }
    return render(request, 'accounts/register.html', context)


def login(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']

        user = auth.authenticate(email=email, password=password)

        if user is not None:
            try:
                cart=Cart.objects.get(cart_id=_cart_id(request))
                is_cart_item_exists = CartItem.objects.filter(cart=cart).exists()
                if is_cart_item_exists:
                    cart_item = CartItem.objects.filter(cart=cart)

                    # Getting the product variations by cart id
                    product_variation = []
                    for item in cart_item:
                        variation = item.variations.all()
                        product_variation.append(list(variation))
                    # Get the cart items from the user to access his product variation
                    cart_item = CartItem.objects.filter(user=user)
                    # Exsisting variation and current variations
                    ex_var_list = []
                    id = []
                    for item in cart_item:
                        exsisting_variation = item.variations.all()
                        ex_var_list.append(list(exsisting_variation))
                        id.append(item.id)

                    for pr in product_variation:
                        if pr in ex_var_list:
                            index = ex_var_list.index(pr)
                            item_id = id[index]
                            item = CartItem.objects.get(id=item_id)
                            item.quantity += 1
                            item.user = user
                            item.save()
                        else:
                            cart_item = CartItem.objects.filter(cart=cart) 
                            for item in cart_item:
                                item.user = user
                                item.save()



            except:
                pass
            auth.login(request, user)
            messages.success(request, "You are now logged in.")
            url = request.META.get('HTTP_REFERER')
            try:
                query = requests.utils.urlparse(url).query
                print('querry ->', query)
                # next=carts/checkout
                params = dict(x.split('=') for x in query.split('&'))
                if 'next' in params:
                    nextpage = params['next']
                    return redirect(nextpage)

                
            except:
                return redirect('dashboard')

        else:
            messages.error(request, "invalid login information")
            return redirect('login')


    # if request.method=="POST":
    #     email    = request.POST['email']
    #     password = request.POST['password']

    #     user = auth.authenticate(email=email, password=password)

    #     if user is not None:
    #         auth.login(request, user)
    #         # messages.success(request, "You are now logged in.")
    #         return redirect('home')
    #     else:
    #         messages.error(request, "invalid login information")
    #         return redirect('login')
    return render(request, 'accounts/login.html')

@login_required(login_url = 'login')
def logout(request):
    auth.logout(request)
    messages.success(request, "You are logged out")
    return redirect('login')


def activate(request, uidb64,token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)
    except(TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Congradulation your account is activated.')
        return redirect('login')
    else:
        messages.error(request, 'Invalid activation link')
        return redirect('register')

@login_required(login_url = 'login')
def dashboard(request):
    order = Order.objects.order_by('-created_at').filter(user_id=request.user.id, is_ordered=True)
    orders_count = order.count()
    userprofile = UserProfile.objects.get(user_id= request.user.id)
    context = {
        "orders_count" : orders_count,
        "userprofile" :userprofile
    }
    return render(request, 'accounts/dashboard.html', context)


def forgotpassword(request):
    if request.method == 'POST':
        email = request.POST['email']
        if Account.object.filter(email=email).exists():
            user = Account.object.get(email__exact=email)
            # RESET PASSWORD EMAIL
            current_site = get_current_site(request)
            mail_subject = "Please reset your password"
            message = render_to_string('accounts/reset_password_email.html', {
                'user' : user,
                'domain' : current_site,
                'uid' : urlsafe_base64_encode(force_bytes(user.pk)),
                'token' : default_token_generator.make_token(user),

            })
            to_email=email
            send_email=EmailMessage(mail_subject, message, to=[to_email])
            send_email.send()

            messages.success(request,'Password reset email has been sent to your email address')
            return redirect('login')



        else:
            messages.error(request, 'Account does not exists')
            return redirect('forgotpassword')

    return render(request, 'accounts/forgotpassword.html')

def resetpassword_validate(request, uidb64,token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)
    except(TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        request.session['uid'] = uid
        messages.success(request, 'Please reset your password')
        return redirect('resetpassword')
    else:
        messages.error(request, 'This link has been expired')
        return redirect('login')

def resetpassword(request):
    if request.method == 'POST':
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if password == confirm_password:
            uid = request.session.get('uid')
            user = Account.object.get(pk = uid)
            user.set_password(password)
            user.save()
            messages.success(request, 'Password reset successful')
            return redirect('login')
        else:
            messages.error(request, 'Password does not match!')
            return redirect('resetpassword')
    else:
        return render(request, 'accounts/resetpassword.html')

@login_required(login_url= 'login')
def my_orders(request):
    orders = Order.objects.filter(user = request.user, is_ordered = True).order_by('-created_at')
    context = {
        'orders' : orders
    }
    return render(request, 'accounts/my_orders.html', context)

@login_required(login_url= 'login')
def edit_profile(request):
    userprofile = get_object_or_404(UserProfile, user=request.user)
    if request.method== 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = UserProfileform(request.POST, request.FILES, instance=userprofile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profie has been updated succesfully')
            return redirect('edit_profile')
    else:
        user_form=UserForm(instance=request.user)
        profile_form=UserProfileform(instance=userprofile)
    
    context = {
        'user_form' : user_form,
        'profile_form' : profile_form,
        'userprofile' : userprofile,
    }

    return render(request, 'accounts/edit_profile.html', context)

@login_required(login_url= 'login')
def change_password(request):
    if request.method =='POST':
        current_password = request.POST['current_password']
        new_password = request.POST['new_password']
        confirm_password = request.POST['confirm_password']

        user = Account.object.get(username__exact= request.user.username)

        if new_password == confirm_password:
            success = user.check_password(current_password)
            if success:
                user.set_password(new_password)
                user.save()
                #auth.logout(request) ---------------------> to logout after changinng the passwod
                messages.success(request, 'Passwrod updated succefully')
                return redirect('change_password')
            else:
                messages.error(request,'Please enter valid password')
                return redirect('change_password')
        else:
            messages.error(request,'Password does not match!')
            return redirect('change_password')

    return render(request, 'accounts/change_password.html')

@login_required(login_url= 'login')
def order_detail(request, order_id):
    order_detail = OrderProduct.objects.filter(order__order_number = order_id)
    order = Order.objects.get(order_number = order_id)

    subtotal = 0
    for i in order_detail:
        subtotal+=i.product_price* i.quantity



    context ={
        'order_detail' : order_detail,
        'order' : order,
        'subtotal' : subtotal,
    }
    return render(request, 'accounts/order_detail.html', context)