import logging
from datetime import datetime, timedelta

import django.contrib.auth as auth
from django import forms
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import Group, Permission
from django.http import JsonResponse
from django.core.validators import MinValueValidator
from django.shortcuts import redirect, render
from django.utils import timezone
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
    is_allowed_password,
    password_length_ok,
    password_requirements_met,
)

logger = logging.getLogger(__name__)


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.TextInput(attrs={"placeholder": "Email", "class": "textbox"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"placeholder": "Password", "class": "textbox"}
        )
    )


class GenerateInvitationForm(forms.Form):
    email = forms.EmailField(
        widget=forms.TextInput(attrs={"placeholder": "Email", "class": "textbox"})
    )
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={"placeholder": "User Alias (optional)", "class": "textbox"}
        ),
        required=False,
    )
    quota = forms.IntegerField(
        widget=forms.NumberInput(
            attrs={
                "placeholder": "Quota",
                "class": "textbox",
                "style": "display: none;",
            }
        ),
        min_value=1,
        max_value=100,
        initial=5,
        required=False,
    )
    lifetime = forms.DateField(
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "min": datetime.now().date(),
                "class": "textbox",
                "style": "display: none;",
            }
        ),
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

        choices = [(UserGroup.USER, "User")]

        if user:
            if user.has_perm(UserPermission.CAN_INVITE_OPERATORS):
                choices.append((UserGroup.OPERATOR, "Operator"))
            if user.has_perm(UserPermission.CAN_INVITE_ADMINS):
                choices.append((UserGroup.ADMIN, "Admin"))

        self.fields["role"].choices = choices

    def clean_expert(self):
        expert = self.cleaned_data.get("expert")
        if expert is None:
            expert = False
        if self.cleaned_data.get("role") == UserGroup.ADMIN:
            expert = True
        return expert


class EditUserForm(forms.Form):
    user_id = forms.IntegerField(
        validators=[MinValueValidator(1)],
    )
    new_alias = forms.CharField(
        max_length=64,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "New User Alias"}),
    )
    new_email = forms.EmailField(
        required=False,
        max_length=64,
        widget=forms.EmailInput(attrs={"placeholder": "New Email"}),
    )
    new_quota = forms.IntegerField(
        validators=[MinValueValidator(1)],
        required=False,
        widget=forms.NumberInput(attrs={"placeholder": "Set Quota", "min": 1}),
    )
    new_lifetime = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                "placeholder": "Set Lifetime",
                "type": "date",
                "min": datetime.now().date(),
            }
        ),
    )
    new_role = forms.ChoiceField(
        choices=[
            (UserGroup.USER, "User"),
            (UserGroup.ADMIN, "Admin"),
            (UserGroup.OPERATOR, "Operator"),
        ],
        required=False,
        widget=forms.Select(),
    )
    remove_quota = forms.BooleanField(required=False, widget=forms.CheckboxInput())
    remove_lifetime = forms.BooleanField(required=False, widget=forms.CheckboxInput())

    def clean_user_id(self):
        user_id = self.cleaned_data.get("user_id")
        if not ObservatoryUser.objects.filter(id=user_id).exists():
            raise forms.ValidationError("User does not exist.")
        return user_id

    def clean_new_alias(self):
        new_alias = self.cleaned_data.get("new_alias").strip()
        if new_alias == "":
            new_alias = self.cleaned_data.get("new_email")
        return new_alias

    def clean_new_email(self):
        new_email = self.cleaned_data.get("new_email").strip()
        if new_email and new_email == "":
            raise forms.ValidationError("Email cannot be an empty string.")
        return new_email

    def clean_remove_quota(self):
        if self.cleaned_data.get("remove_quota") and self.cleaned_data.get("new_quota"):
            raise forms.ValidationError(
                "Cannot remove quota and set a new quota at the same time."
            )
        return self.cleaned_data.get("remove_quota")

    def clean_remove_lifetime(self):
        if self.cleaned_data.get("remove_lifetime") and self.cleaned_data.get(
            "new_lifetime"
        ):
            raise forms.ValidationError(
                "Cannot remove lifetime and set a new lifetime at the same time."
            )
        return self.cleaned_data.get("remove_lifetime")


class SetPasswordForm(forms.Form):
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"placeholder": "Password", "class": "textbox"}
        )
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"placeholder": "Confirm Password", "class": "textbox"}
        )
    )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("new_password1")
        password2 = cleaned_data.get("new_password2")
        errors = []

        if password1 and password2 and password1 != password2:
            errors.append("The passwords are not the same.")
        if password1 and not is_allowed_password(password1):
            errors.append(
                "Only letters, numbers, and common special characters are allowed."
            )
        if password1 and not password_length_ok(password1):
            errors.append("Password must be between 8 and 64 characters long.")
        if password1 and not password_requirements_met(password1):
            errors.append(
                "Password must contain at least one letter, one number, and one special character."
            )

        if errors:
            raise forms.ValidationError(errors)

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

    email = form.cleaned_data["email"]
    password = form.cleaned_data["password"]

    user = auth.authenticate(request, email=email, password=password)
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
    logger.info(f"User {email} logged in successfully")
    return redirect(settings.LOGIN_REDIRECT_URL)


@require_GET
@user_passes_test(lambda u: u.has_perm(UserPermission.CAN_GENERATE_INVITATION))
def user_management(request):
    return generate_user_management_template(
        request, invitation_form=GenerateInvitationForm(user=request.user)
    )


@require_POST
@user_passes_test(lambda u: u.has_perm(UserPermission.CAN_GENERATE_INVITATION))
def generate_user_invitation(request):
    form = GenerateInvitationForm(request.POST, user=request.user)
    if not form.is_valid():
        logger.warning(f"Invalid form data on account creation: {form.errors}")
        return generate_user_management_template(
            request,
            invitation_form=GenerateInvitationForm(user=request.user),
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
        return generate_user_management_template(
            request,
            invitation_form=GenerateInvitationForm(request.user),
            error="You do not have permission to invite admins",
        )

    if role == UserGroup.OPERATOR and not request.user.has_perm(
        UserPermission.CAN_INVITE_OPERATORS
    ):
        return generate_user_management_template(
            request,
            invitation_form=GenerateInvitationForm(request.user),
            error="You do not have permission to invite operators",
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
        return redirect(settings.LOGIN_REDIRECT_URL)

    return register_from_invitation_template(
        request, token, form=SetPasswordForm(), email=invitation.email
    )


@require_POST
@login_not_required
def register_user(request, token):
    try:
        invitation = InvitationToken.objects.get(token=token)
    except InvitationToken.DoesNotExist:
        return redirect(settings.LOGIN_REDIRECT_URL)

    form = SetPasswordForm(request.POST)
    if not form.is_valid():
        return register_from_invitation_template(
            request,
            token,
            form=form,
            email=invitation.email,
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


@require_POST
@user_passes_test(lambda u: u.has_perm(UserPermission.CAN_EDIT_USERS))
def edit_user(request):
    edit_form = EditUserForm(request.POST)
    if not edit_form.is_valid():
        return JsonResponse({"status": "error", "error": edit_form.errors}, status=400)
    edit_form_data = edit_form.cleaned_data
    user = ObservatoryUser.objects.get(id=edit_form_data["user_id"])
    if edit_form_data["new_alias"]:
        user.username = edit_form_data["new_alias"]
    if edit_form_data["new_email"]:
        if user.username == user.email and not edit_form_data["new_alias"]:
            user.username = edit_form_data["new_email"]
        user.email = edit_form_data["new_email"]
    if edit_form_data["new_quota"]:
        user.quota = edit_form_data["new_quota"]
    if edit_form_data["new_lifetime"]:
        user.lifetime = edit_form_data["new_lifetime"]
    if edit_form_data["new_role"]:
        user.groups.clear()
        user.groups.add(Group.objects.get(name=edit_form_data["new_role"]))
    if edit_form_data["remove_quota"]:
        user.quota = None
    if edit_form_data["remove_lifetime"]:
        user.lifetime = None
    user.save()
    return JsonResponse({"status": "success"}, status=200)


@api_view(["POST"])
@user_passes_test(lambda u: u.has_perm(UserPermission.CAN_GENERATE_INVITATION))
def has_invitation(request):
    email = request.data.get("email")
    exists = InvitationToken.objects.filter(email=email).exists()
    return JsonResponse({"has_invitation": exists}, status=200)


@require_POST
@user_passes_test(lambda u: u.has_perm(UserPermission.CAN_GENERATE_INVITATION))
def delete_invitation(request, invitation_id):
    invitation = InvitationToken.objects.get(id=invitation_id)
    invitation.delete()
    return JsonResponse({"status": "success"}, status=200)


def delete_user(request, user_id):
    if request.method != "DELETE":
        return JsonResponse(
            {"status": "error", "message": "wrong method. Requires DELETE"}, status=405
        )

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
    user_data.delete_user(target_user)
    target_user.is_active = False  # prevents user from logging in again
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


def generate_user_management_template(request, error=None, invitation_form=None):
    return render(
        request,
        "accounts/user_management.html",
        {
            "error": error,
            "invitation_form": invitation_form,
            "edit_user_form": EditUserForm(),
            "UserGroups": UserGroup,
            "invitations": InvitationToken.objects.all(),
            "users": ObservatoryUser.objects.all().order_by("-lifetime"),
            "current_user": request.user,
            "time_now": timezone.now().date(),
        },
    )


def register_from_invitation_template(request, token, email=None, form=None):
    return render(
        request,
        "accounts/register_from_invitation.html",
        {"form": form, "email": email, "token": token},
    )


def create_prepopulated_debug_login_form() -> LoginForm:
    """
    Creates a login form where the email field is prepopulated, with the value
    that is specified in the `ADMIN_EMAIL` environment variable, useful for debugging
    :return: LoginForm with pre-populated email field
    """

    email = os.environ.get("ADMIN_EMAIL")
    return LoginForm(initial={"email": email})
