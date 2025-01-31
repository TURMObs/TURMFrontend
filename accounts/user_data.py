import logging

from django.forms.models import model_to_dict

from accounts.models import ObservatoryUser
from observation_data.models import AbstractObservation
from observation_data.observation_management import delete_observation

logger = logging.getLogger(__name__)


def delete_user(user: ObservatoryUser):
    """
    Deletes all data associated with a user. This includes all observation requests and uploaded files.
    :param user: The user to delete
    """
    observation_requests = AbstractObservation.objects.filter(user=user.id)
    for request in observation_requests:
        delete_observation(
            user=ObservatoryUser.objects.get(id=user.id), observation_id=request.id
        )
    user.deletion_pending = True  # cannot be deleted right away because we have to wait until the morning to delete the users observations and afterward the user itself
    user.save()


def get_all_data(user: ObservatoryUser):
    """
    Get all data associated with a user. This includes all observation requests.
    :param user: The user to get the data from
    :return: A dictionary containing all associated data
    """
    data = {}
    # Convert the Polymorphic QuerySet into a list of dictionaries
    observation_requests = AbstractObservation.objects.filter(user=user.id)
    data["observation_requests"] = [
        serialize_to_string_rep(request) for request in observation_requests
    ]

    data["user"] = model_to_dict(user)
    data["user"]["password"] = "PASSWORD HASH"
    empty_fields = []
    for key, value in data["user"].items():
        if value is None or value == "" or value == []:
            empty_fields.append(key)

    for field in empty_fields:
        data["user"].pop(field)

    if "groups" in data["user"]:
        data["user"]["groups"] = [str(group) for group in data["user"]["groups"]]
    return data


def serialize_to_string_rep(instance):
    """
    Serialize a model instance to a dict but represent nested models as strings.
    """
    serialized_data = model_to_dict(instance)
    for key, value in serialized_data.items():
        if hasattr(value, "__str__"):
            serialized_data[key] = str(value)
    return serialized_data
