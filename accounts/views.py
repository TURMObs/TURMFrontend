import logging
from datetime import datetime, timedelta

import django.contrib.auth as auth
from django import forms
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import Group, Permission
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_not_required
from django.conf import settings
import os

from rest_framework.decorators import api_view

from . import user_data
from .models import (
    InvitationToken,
    generate_invitation_link,
    ObservatoryUser,
    UserPermission,
    UserGroup,
)

logger = logging.getLogger(__name__)


class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.TextInput(attrs={"placeholder": "Email"}))
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Password"})
    )


class GenerateInvitationForm(forms.Form):
    email = forms.EmailField(widget=forms.TextInput(attrs={"placeholder": "Email"}))
    username = forms.CharField(
        widget=forms.TextInput(attrs={"placeholder": "User Alias (optional)"}),
        required=False,
    )
    quota = forms.IntegerField(
        widget=forms.NumberInput(attrs={"placeholder": "Quota"}),
        min_value=1,
        max_value=100,
        initial=5,
        required=False,
    )
    lifetime = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "min": datetime.now().date()}),
        initial=(datetime.now() + timedelta(days=90)),
        required=False,
    )
    role = forms.ChoiceField(
        widget=forms.Select(),
        choices=[],
        initial=UserGroup.USER,
        required=True,
    )
    expert = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={"id": "id_expert"}),
        label="expert",
        required=False,
        initial=False,
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        choices = [(UserGroup.USER, "Nutzer*in")]

        if user:
            if user.has_perm(UserPermission.CAN_INVITE_ADMINS):
                choices.append((UserGroup.ADMIN, "Admin"))
            if user.has_perm(UserPermission.CAN_INVITE_GROUP_LEADERS):
                choices.append((UserGroup.GROUP_LEADER, "Gruppenleiter*in"))

        self.fields["role"].choices = choices

    def clean_expert(self):
        expert = self.cleaned_data.get("expert")
        if expert is None:
            expert = False
        if self.cleaned_data.get("role") == UserGroup.ADMIN:
            expert = True
        return expert


class SetPasswordForm(forms.Form):
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Password"})
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Confirm Password"})
    )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("new_password1")
        password2 = cleaned_data.get("new_password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match")
        return cleaned_data


@require_GET
@login_not_required
def login(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)
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
    if not isinstance(user, ObservatoryUser):
        return index_template(request, form=LoginForm(), error="Invalid user")
    if user.deletion_pending:
        return index_template(
            request, form=LoginForm(), error="This account has been marked for deletion"
        )
    auth.login(request, user)
    logger.info(f"User {username} logged in successfully")
    return redirect(settings.LOGIN_REDIRECT_URL)


@require_GET
@user_passes_test(lambda u: u.has_perm(UserPermission.CAN_GENERATE_INVITATION))
def generate_invitation(request):
    return generate_invitation_template(
        request, form=GenerateInvitationForm(user=request.user)
    )


@require_POST
@user_passes_test(lambda u: u.has_perm(UserPermission.CAN_GENERATE_INVITATION))
def generate_user_invitation(request):
    form = GenerateInvitationForm(request.POST, user=request.user)
    if not form.is_valid():
        logger.warning(f"Invalid form data on account creation: {form.errors}")
        return generate_invitation_template(
            request,
            form=GenerateInvitationForm(user=request.user),
            error="Invalid email",
        )

    email = form.cleaned_data["email"]
    username = form.cleaned_data["username"]
    quota = form.cleaned_data["quota"]
    lifetime = form.cleaned_data["lifetime"]
    role = form.cleaned_data["role"]
    expert = form.cleaned_data["expert"]

    if username is None or username == "":
        username = email

    if role == UserGroup.ADMIN and not request.user.has_perm(
        UserPermission.CAN_INVITE_ADMINS
    ):
        return generate_invitation_template(
            request,
            form=GenerateInvitationForm(request.user),
            error="You do not have permission to invite admins",
        )

    if role == UserGroup.GROUP_LEADER and not request.user.has_perm(
        UserPermission.CAN_INVITE_GROUP_LEADERS
    ):
        return generate_invitation_template(
            request,
            form=GenerateInvitationForm(request.user),
            error="You do not have permission to invite group leaders",
        )

    url = settings.BASE_URL
    subpath = settings.SUBPATH
    if subpath:
        url += subpath
    url += "/accounts/register"
    link = generate_invitation_link(
        base_url=url,
        email=email,
        username=username,
        quota=quota,
        lifetime=lifetime,
        role=role,
        expert=expert,
    )
    if link is None:
        return JsonResponse(
            {"status": "error", "error": "User with this email already exists"},
            status=400,
        )
    logger.info(f"Invitation generated for email {email} by {request.user.username}")
    return JsonResponse({"status": "success", "link": link}, status=200)


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
        request, token, form=SetPasswordForm(), email=invitation.email
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

    form = SetPasswordForm(request.POST)
    if not form.is_valid():
        return register_from_invitation_template(
            request,
            token,
            form=SetPasswordForm(),
            email=invitation.email,
            error="Invalid password",
        )
    user = ObservatoryUser.objects.create_user(
        username=invitation.username,
        email=invitation.email,
        quota=invitation.quota,
        lifetime=invitation.lifetime,
    )
    user.set_password(form.cleaned_data["new_password1"])
    user.groups.add(Group.objects.get(name=invitation.role))
    if invitation.expert:
        user.user_permissions.add(
            Permission.objects.get(
                codename=UserPermission.CAN_CREATE_EXPERT_OBSERVATION
            )
        )
    user.save()
    invitation.delete()
    auth.login(request, user)
    logger.info(
        f"Created new {invitation.role} account for {user.username} with quota {user.quota} and lifetime {user.lifetime} (expert: {invitation.expert})"
    )
    return redirect(settings.LOGIN_REDIRECT_URL)


@api_view(["POST"])
def has_invitation(request):
    email = request.data.get("email")
    print(email)
    exists = InvitationToken.objects.filter(email=email).exists()
    return JsonResponse({"has_invitation": exists}, status=200)


@require_POST
def delete_invitation(request, invitation_id):
    invitation = InvitationToken.objects.get(id=invitation_id)
    invitation.delete()
    return JsonResponse({"status": "success"}, status=200)


@require_POST
def delete_user(request, user_id):
    request_user = request.user
    if user_id != request_user.id and not request_user.has_perm(
        UserPermission.CAN_DELETE_USERS
    ):
        return JsonResponse(
            {
                "status": "error",
                "message": "You do not have permission to delete this user.",
            },
            status=403,
        )
    target_user = ObservatoryUser.objects.get(id=user_id)
    if not target_user:
        return JsonResponse(
            {
                "status": "error",
                "message": "User does not exist.",
            },
            status=400,
        )
    if not isinstance(target_user, ObservatoryUser):
        return JsonResponse(
            {
                "status": "error",
                "message": "You cannot delete this user.",
            },
            status=400,
        )
    target_user.deletion_pending = True
    target_user.save()
    logger.info(f"{target_user} has been marked for deletion by {request_user}")
    return JsonResponse({"status": "success"}, status=200)


@require_GET
def get_user_data(request):
    data = user_data.get_all_data(request.user)
    return JsonResponse(data)


@require_GET
def dsgvo_options(request):
    return render(request, "accounts/dsgvo.html", {"subpath": settings.SUBPATH})


def index_template(request, error=None, form=None):
    return render(request, "accounts/index.html", {"error": error, "form": form})


def generate_invitation_template(request, error=None, link=None, form=None):
    return render(
        request,
        "accounts/user_management.html",
        {
            "error": error,
            "form": form,
            "UserGroups": UserGroup,
            "invitations": InvitationToken.objects.all(),
            "users": ObservatoryUser.objects.all(),
            "current_user_id": request.user.id,
        },
    )


def register_from_invitation_template(
    request, token, error=None, email=None, form=None
):
    return render(
        request,
        "accounts/register_from_invitation.html",
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
