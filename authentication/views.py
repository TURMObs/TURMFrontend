import logging
import django.contrib.auth as auth
from django import forms
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_not_required
from django.conf import settings
import os

from .models import InvitationToken, generate_invitation_link

logger = logging.getLogger(__name__)


class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.TextInput(attrs={"placeholder": "Email"}))
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Password"})
    )


class GenerateInvitationForm(forms.Form):
    email = forms.EmailField()


@require_GET
@login_not_required
def login(request):
    if request.user.is_authenticated:
        return redirect("index")
    else:
        # If this is a DEBUG build we want to pre-populate the form with a default user
        if settings.DEBUG:
            form = create_prepopulated_debug_login_form()
            return index_template(request, form=form)
        else:
            return index_template(request, form=LoginForm())


@require_POST
@login_not_required
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
    logger.info(f"User {username} logged in successfully")
    return redirect(settings.LOGIN_REDIRECT_URL)


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
    base_url = f"{request.scheme}://{request.get_host()}/authentication/register"
    link = generate_invitation_link(base_url, email)
    if link is None:
        return generate_invitation_template(
            request, form=GenerateInvitationForm(), error="Email already registered"
        )
    logger.info(f"Invitation generated for email {email} by {request.user.username}")
    return generate_invitation_template(request, link=link)


@require_GET
@login_not_required
def register(request, token):
    try:
        invitation = InvitationToken.objects.get(token=token)
    except InvitationToken.DoesNotExist:
        return register_from_invitation_template(
            request, token, error="Invalid invitation link"
        )

    return register_from_invitation_template(
        request, token, form=SetPasswordForm(User()), email=invitation.email
    )


@require_POST
@login_not_required
def register_user(request, token):
    try:
        invitation = InvitationToken.objects.get(token=token)
    except InvitationToken.DoesNotExist:
        return register_from_invitation_template(
            request, token, error="Invalid invitation link"
        )

    form = SetPasswordForm(User(), request.POST)
    if not form.is_valid():
        return register_from_invitation_template(
            request, token, error="Invalid password"
        )

    invitation.delete()
    user = User.objects.create_user(username=invitation.email, email=invitation.email)
    user.set_password(form.cleaned_data["new_password1"])
    user.save()
    invitation.save()
    auth.login(request, user)
    logger.info(f"Created new account for {user.username}")
    return redirect(settings.LOGIN_REDIRECT_URL)


def index_template(request, error=None, form=None):
    return render(request, "authentication/index.html", {"error": error, "form": form})


def generate_invitation_template(request, error=None, link=None, form=None):
    return render(
        request,
        "authentication/generate_invitation.html",
        {"error": error, "form": form, "link": link},
    )


def register_from_invitation_template(
    request, token, error=None, email=None, form=None
):
    return render(
        request,
        "authentication/register_from_invitation.html",
        {"error": error, "form": form, "email": email, "token": token},
    )


def create_prepopulated_debug_login_form() -> LoginForm:
    """
    Creates a login form where the email field is prepopulated, with the value
    that is specified in the `ADMIN_EMAIL` environment variable, useful for debugging
    :return: LoginForm with pre-populated email field
    """

    email = os.environ.get("ADMIN_EMAIL")
    return LoginForm(initial={"email": email})
