"""
This module provides a simple interface to interact with the Nextcloud server using the nc_py_api library.
Functions:
    - initialize_connection: Initializes the connection to the Nextcloud server using the credentials from the .env file
    - upload_file: Uploads a file to the Nextcloud server
    - download_file: Downloads a file from the Nextcloud server
    - download_folder: Downloads a folder from the Nextcloud server into a zip file

Environment Variables:
    - NC_URL: The URL of the Nextcloud server
    - NC_AUTH_USER: The username to authenticate with
    - NC_AUTH_PASSWORD: The password to authenticate with
"""

import os
from os import PathLike

from nc_py_api import Nextcloud, NextcloudException
from dotenv import load_dotenv

nc: Nextcloud


def initialize_connection() -> None:
    """
    Initializes the connection to the Nextcloud server using the credentials from the .env file
    """
    global nc
    load_dotenv()
    nc_url = os.getenv("NC_URL")
    nc_auth_user = os.getenv("NC_AUTH_USER")
    nc_auth_pass = os.getenv("NC_AUTH_PASSWORD")

    nc = Nextcloud(
        nextcloud_url=nc_url, nc_auth_user=nc_auth_user, nc_auth_pass=nc_auth_pass
    )


def upload_file(nc_path: str, local_path: PathLike[bytes] | str) -> None:
    """
    Uploads a file to the Nextcloud server

    Example: ``upload_file("Documents/test.json", "./test.json")``

    :param nc_path: Files path on the Nextcloud server
    :param local_path: Local path of the file to upload
    """
    with open(local_path, "rb") as file:
        nc.files.upload_stream(nc_path, file)


def download_file(nc_path: str, local_path: PathLike[bytes] | str) -> None:
    """
    Downloads a file from the Nextcloud server

    Example: ``download_file("Documents/test.json", "./test.json")``

    :param nc_path: File path on the Nextcloud server
    :param local_path: Local path to save the file
    :raises NextcloudException: If the file does not exist on the server
    """
    with open(local_path, "wb") as file:
        try:
            file.write(nc.files.download(nc_path))
        except NextcloudException as e:
            raise e


def download_folder(nc_path, local_path):
    """
    Downloads a folder from the Nextcloud server into a zip file

    Example: ``download_folder("Documents", "./Documents.zip")``

    :param nc_path: Folder path on the Nextcloud server
    :param local_path: Local path to save the zip file

    :raises NextcloudException: If the folder does not exist on the server
    """
    try:
        nc.files.download_directory_as_zip(nc_path, local_path)
    except NextcloudException as e:
        raise e
