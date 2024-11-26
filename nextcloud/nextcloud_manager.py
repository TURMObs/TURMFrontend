"""
This module provides a simple interface to interact with the Nextcloud server using the nc_py_api library.
Functions:
    - initialize_connection: Initializes the connection to the Nextcloud server using the credentials from the .env file
    - upload_file: Uploads a file to the Nextcloud server
    - download_file: Downloads a file from the Nextcloud server
    - download_folder: Downloads a folder from the Nextcloud server into a zip file

Environment Variables:
    - NC_URL: The URL of the Nextcloud server
    - NC_USER: The username to authenticate with
    - NC_PASSWORD: The password to authenticate with
"""

import json
import os
from io import BytesIO
from os import PathLike
from nc_py_api import Nextcloud
from dotenv import load_dotenv

nc: Nextcloud


def initialize_connection() -> None:
    """
    Initializes the connection to the Nextcloud server using the credentials from the .env file.
    Needs to be run once before using other functions of this manager
    """
    global nc
    load_dotenv()
    nc_url = os.getenv("NC_URL")
    nc_auth_user = os.getenv("NC_USER")
    nc_auth_pass = os.getenv("NC_PASSWORD")

    nc = Nextcloud(
        nextcloud_url=nc_url, nc_auth_user=nc_auth_user, nc_auth_pass=nc_auth_pass
    )


def _check_initialized(method):
    """
    Wrapper to check whether the Nextcloud connection was initialized.
    :raises Exception: If connection has not been initialized
    """

    def wrapper(*args, **kwargs):
        try:
            nc
        except NameError:
            raise Exception(
                "Call initialize_connection() first to initialize the Nextcloud connection"
            )
        return method(*args, **kwargs)

    return wrapper


@_check_initialized
def upload_file(nc_path: str, local_path: PathLike[bytes] | str) -> None:
    """
    Uploads a file to the Nextcloud server

    Example: ``upload_file("Documents/test.json", "./test.json")``

    :param nc_path: Files path on the Nextcloud server
    :param local_path: Local path of the file to upload
    """
    with open(local_path, "rb") as file:
        nc.files.upload_stream(nc_path, file)


@_check_initialized
def upload_dict(nc_path: str, data: dict) -> None:
    """
    Uploads a file_stream to the Nextcloud

    Example: ``upload_dict("Documents/test.json", json.load(f))``

    :param nc_path: Files path on the Nextcloud server
    :param data: Dict to be uploaded
    """
    json_stream = BytesIO(json.dumps(data, indent=4).encode("utf-8"))
    nc.files.upload_stream(path=nc_path, fp=json_stream)


@_check_initialized
def download_file(nc_path: str, local_path: PathLike[bytes] | str) -> None:
    """
    Downloads a file from the Nextcloud server

    Example: ``download_file("Documents/test.json", "./test.json")``

    :param nc_path: File path on the Nextcloud server
    :param local_path: Local path to save the file
    :raises NextcloudException: If the file does not exist on the server
    """
    with open(local_path, "wb") as file:
        file.write(nc.files.download(nc_path))


@_check_initialized
def download_dict(nc_path: str) -> dict:
    """
    Downloads a dict from the Nextcloud server and return it without storing it

    :param nc_path: File path on the Nextcloud server
    :raises NextcloudException: If the file does not exist on the server

    """
    byte_stream = nc.files.download(path=nc_path)
    return json.loads(byte_stream.decode("utf-8"))


@_check_initialized
def download_folder(nc_path: str, local_path: PathLike[bytes] | str) -> None:
    """
    Downloads a folder from the Nextcloud server into a zip file
    Example: ``download_folder("Documents", "./Documents.zip")``
    :param nc_path: Folder path on the Nextcloud server
    :param local_path: Local path to save the zip file
    :raises NextcloudException: If the folder does not exist on the server
    """
    nc.files.download_directory_as_zip(nc_path, local_path)


@_check_initialized
def delete(nc_path: str) -> None:
    """
    Deletes a file/directory from the Nextcloud server
    :raises NextcloudException: If the file does not exist on the server
    """
    nc.files.delete(nc_path)
