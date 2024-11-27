# Deployment

## Prerequisites
1. [Docker](https://www.docker.com/get-started)
2. [Docker Compose](https://docs.docker.com/compose/install/) (already packaged in Docker Desktop)
3. Environment variables:


    | **Environment Variable** | **Description**                                                                                                                                               | **Required** | **Recommended Value**                          |
    |--------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|------------------------------------------------|
    | ``POSTGRES_DB``          | Name of the Postgres database                                                                                                                                 | **Yes**      | `TURMFrontend`                                 |
    | `POSTGRES_USER`          | Superuser of the Postgres Database                                                                                                                            | **Yes**      | `admin`                                        |
    | `POSTGRES_PASSWORD`      | Superuser password                                                                                                                                            | **Yes**      | Secure password                                |
    | `DEBUG`                  | Whether Django runs the server in DEBUG mode (default: False)                                                                                                 | **No**       | `True` for development, `False` for deployment |
    | `DB_VOLUME`              | Location of DB Volume. If left empty the data will only be saved in the docker volume and will not be mapped to a local folder (increases first startup time) | **No**       | `./data/db` for mapping to local folder        |
    | `DB_PORT`                | Local Port that the Postgres DB can be accessed on (outside the container)                                                                                    | **Yes**      | `5432`                                         |
    | `WEB_PORT`               | Local Port used for the website                                                                                                                               | **Yes**      | `8000`                                         |
    | `NC_PORT`         | Local Port that the Nextcloud can be accessed on                                                                                                              | **No**       | `8080`, only required for Nextcloud testing |
    | `NC_USER`         | User for the Nextcloud instance                                                                                                                               | **No**       | Nextcloud User                                        |
    | `NC_PASSWORD`     | Password for the Nextcloud instance                                                                                                                           | **No**       | Nextcloud password                                |

The easiest way is to create a local `.env` file in the root directory of the project with the following content:
```.env
POSTGRES_DB=TURMFrontend
POSTGRES_USER=<user>
POSTGRES_PASSWORD=<password>
DB_VOLUME=./data/db
DEBUG=True
DB_PORT=5432
WEB_PORT=8000
NC_PORT=8080
NC_USER=<user>
NC_PASSWORD=<password>
```

## Development

To develop the project locally, install the dependencies using `pip install -r requirements_dev.txt`.
Run the server using `docker-compose up`.
To format the code, run `scripts/format.sh`.
To run the tests, run `python manage.py test`.

## Docker Compose
Run using `docker-compose up` in the root directory of the project. The application will be available at `http://localhost:8000`.
Hot reloading is supported. The data will be saved in a PostgreSQL database, inside the `data` folder.
Optionally use `docker-compose --profile test up` to run a (non-persisting) Nextcloud Container useful for testing.

# Known Limitations
- The Nextcloud container is not persistent. This is by design, as the Nextcloud container is only used for testing purposes.
  - This also means that the Nextcloud has to be initialized every time the container is started by visiting `http://localhost:8080` and setting up the Nextcloud instance with the same password and user defined in the Environment.
- During development some migration files where deleted, this means that the database might need to be reset when running the application for the first time. If the database was used without mapping the volume to a local folder, simply run `docker-compose down -v` to remove all docker volumes. If the volume was mapped to a local folder, simply delete the folder and run `docker-compose up` again.

