from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import User
from django.shortcuts import redirect, render

from .models import InvitationToken, generate_invitation_link


def index(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("index")
        else:
            return render(
                request,
                "authentication/index.html",
                {"error": "Invalid username or password"},
            )
    else:
        return render(request, "authentication/index.html")

def generate_invitation(request):
    if request.method == "POST":
        email = request.POST.get("email")
        base_url = request.build_absolute_uri("register")
        link = generate_invitation_link(base_url, email)
        if link is None:
            return render(
                request,
                "authentication/generate_invitation.html",
                {"error": "Email already registered"},
            )
        return render(
            request, "authentication/generate_invitation.html", {"link": link}
        )
    return render(request, "authentication/generate_invitation.html")

def register(request, token):
    try:
        invitation = InvitationToken.objects.get(token=token)
    except InvitationToken.DoesNotExist:
        return render(
            request,
            "authentication/register_from_invitation.html",
            {"error": "Invalid invitation link"},
        )

    if request.method == "POST":
        form = SetPasswordForm(User(), request.POST)
        if form.is_valid():
            invitation.delete()
            user = User.objects.create_user(
                username=invitation.email, email=invitation.email
            )
            user.set_password(form.cleaned_data["new_password1"])
            user.save()
            invitation.is_used = True
            invitation.save()
            login(request, user)
            print("Login successful")
            return redirect("index")
    else:
        form = SetPasswordForm(User())

    return render(
        request,
        "authentication/register_from_invitation.html",
        {"form": form, "email": invitation.email},
    )
