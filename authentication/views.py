from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import User
from .models import InvitationToken
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages

def index(request):
    # The user clicked on login
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('index')
        else:
            return render(request, 'authentication/index.html', {'error': 'Invalid username or password'})
    else:
        return render(request, 'authentication/index.html')

def generate_invitation_link(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        link = generate_url(request, email)
        return render(request, 'authentication/generate_invitation_link.html', {'link': link})
    return render(request, 'authentication/generate_invitation_link.html')

def register(request, token):
    try:
        invitation = InvitationToken.objects.get(token=token)
    except InvitationToken.DoesNotExist:
        return render(request, 'authentication/register_from_invitation.html', {'error': 'Invalid invitation link'})

    if request.method == 'POST':
        form = SetPasswordForm(User(), request.POST)
        if form.is_valid():
            invitation.delete()
            user = User.objects.create_user(username=invitation.email, email=invitation.email)
            user.set_password(form.cleaned_data['new_password1'])
            user.save()
            invitation.is_used = True
            invitation.save()
            login(request, user)
            print("Login successful")
            return redirect('index')
    else:
        form = SetPasswordForm(User())

    return render(request, 'authentication/register_from_invitation.html', {'form': form, 'email': invitation.email})

def generate_url(request, email):
    # TODO: check if email is already registered
    invitation = InvitationToken.objects.create(email=email)
    current_site = get_current_site(request)
    invitation_link = f"http://{current_site.domain}{reverse('register_from_invitation', args=[str(invitation.token)])}"
    return invitation_link
