import django.contrib.auth as auth
from django import forms
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from .models import InvitationToken, generate_invitation_link


class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.TextInput(attrs={"placeholder": "Email"}))
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Password"})
    )


class GenerateInvitationForm(forms.Form):
    email = forms.EmailField()


@require_GET
def login(request):
    if request.user.is_authenticated:
        return redirect("index")
    else:
        return index_template(request, form=LoginForm())


@require_POST
def login_user(request):
    form = LoginForm(request.POST)
    if not form.is_valid():
        return index_template(
            request, form=LoginForm(), error="Invalid username or password"
        )

    username = form.cleaned_data["email"]
    password = form.cleaned_data["password"]

    user = auth.authenticate(request, username=username, password=password)
    if not user:
        return index_template(
            request, form=LoginForm(), error="Invalid username or password"
        )
    auth.login(request, user)
    return redirect("index")


@require_GET
@user_passes_test(lambda u: u.is_superuser)
def generate_invitation(request):
    return generate_invitation_template(request, form=GenerateInvitationForm())


@require_POST
@user_passes_test(lambda u: u.is_superuser)
def generate_user_invitation(request):
    form = GenerateInvitationForm(request.POST)
    if not form.is_valid():
        return generate_invitation_template(
            request, form=GenerateInvitationForm(), error="Invalid email"
        )

    email = form.cleaned_data["email"]
    base_url = request.build_absolute_uri("register")
    link = generate_invitation_link(base_url, email)
    if link is None:
        return generate_invitation_template(
            request, form=GenerateInvitationForm(), error="Email already registered"
        )
    return generate_invitation_template(request, link=link)


@require_GET
def register(request, token):
    try:
        invitation = InvitationToken.objects.get(token=token)
    except InvitationToken.DoesNotExist:
        return register_from_invitation_template(
            request, error="Invalid invitation link"
        )

    return register_from_invitation_template(
        request, form=SetPasswordForm(User()), email=invitation.email
    )


@require_POST
def register_user(request, token):
    try:
        invitation = InvitationToken.objects.get(token=token)
    except InvitationToken.DoesNotExist:
        return register_from_invitation_template(
            request, error="Invalid invitation link"
        )

    form = SetPasswordForm(User(), request.POST)
    if not form.is_valid():
        return register_from_invitation_template(request, error="Invalid password")

    invitation.delete()
    user = User.objects.create_user(username=invitation.email, email=invitation.email)
    user.set_password(form.cleaned_data["new_password1"])
    user.save()
    invitation.save()
    auth.login(request, user)
    return redirect("index")


def index_template(request, error=None, form=None):
    return render(request, "authentication/index.html", {"error": error, "form": form})


def generate_invitation_template(request, error=None, link=None, form=None):
    return render(
        request,
        "authentication/generate_invitation.html",
        {"error": error, "form": form, "link": link},
    )


def register_from_invitation_template(request, error=None, email=None, form=None):
    return render(
        request,
        "authentication/register_from_invitation.html",
        {"error": error, "form": form, "email": email},
    )
