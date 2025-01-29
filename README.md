# Deployment

## Prerequisites
1. [Docker](https://www.docker.com/get-started)
2. [Docker Compose](https://docs.docker.com/compose/install/) (already packaged in Docker Desktop)
3. Environment variables:


    | **Environment Variable** | **Description**                                                                                                                                               | **Required** | **Recommended Value**                          |
    |--------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|------------------------------------------------|
    | `POSTGRES_DB`            | Name of the Postgres database. Should be lowercase                                                                                                                               | **Yes**      | `turmfrontend`                                 |
    | `POSTGRES_USER`          | Superuser of the Postgres Database                                                                                                                            | **Yes**      | `admin`                                        |
    | `POSTGRES_PASSWORD`      | Superuser password                                                                                                                                            | **Yes**      | Secure password                                |
    | `DEBUG`                  | Whether Django runs the server in DEBUG mode (default: False)                                                                                                 | **No**       | `True` for development, `False` for deployment |
    | `ADMIN_EMAIL`            | Email of the admin user that is logged in by default when `DEBUG` is set to `True`                                                                            | **Yes**      | `admin@admin.com`                              |
    | `ADMIN_PASSWORD`         | Password of the admin user that is assigned in by default when `DEBUG` is set to `True`                                                                       | **Yes**      | `admin`                                        |
    | `DB_VOLUME`              | Location of DB Volume. If left empty the data will only be saved in the docker volume and will not be mapped to a local folder (increases first startup time) | **No**       | `./data/db` for mapping to local folder        |
    | `DB_PORT`                | Local Port that the Postgres DB can be accessed on (outside the container)                                                                                    | **Yes**      | `5432`                                         |
    | `WEB_PORT`               | Local Port used for the website                                                                                                                               | **Yes**      | `8000`                                         |
    | `NC_PORT`                | Local Port that the Nextcloud can be accessed on                                                                                                              | **No**       | `8080`, only required for Nextcloud testing    |
    | `NC_USER`                | User for the Nextcloud instance                                                                                                                               | **No**       | Nextcloud User                                 |
    | `NC_PASSWORD`            | Password for the Nextcloud instance                                                                                                                           | **No**       | Nextcloud password                             |
    | `NC_URL`                 | URL to the Nextcloud instance                                                                                                                                 | **YES**      | `http://localhost:8080`, when testing locally. `http://turmfrontend-nextcloud:80` when run in Docker                                |
    | `NC_PREFIX`              | Top level folders in the nextcloud to store the observations in . Entered as string (without "" or leading/following '/' for multiple folders)                | **No**.      | `test`, default/non-existing: root directory of nextcloud,                                  |
    | `NC_TEST`                | The nextcloud test cannot run in CI. If set to false these test are skipped                                                                                   | **No**.      | default/non-existing `True`                                 |
    | `SUBPATH`                | Subpath the website is being deployed on                                                                                  | **No**.      | /tom                              |
    | `SECRET_KEY`              | Secret Django Key. Keep private!                                                                               | **Yes**.      | See https://djecrety.ir/                           |
   | `BASE_URL`              | Base Website URL                                                                              | **Yes**.      | https://turm.physik.tu-darmstadt.de                      |


The easiest way is to create a local `.env` file in the root directory of the project with the following content:
```.env
POSTGRES_DB=TURMFrontend
POSTGRES_USER=<user>
POSTGRES_PASSWORD=<password>
DB_VOLUME=./data/db
DEBUG=True
ADMIN_EMAIL=<email>
ADMIN_PASSWORD=<password>
DB_PORT=5432
WEB_PORT=8000
NC_PORT=8080
NC_USER=<user>
NC_PASSWORD=<password>
```

## Development

To develop the project locally, install the dependencies running both
`pip install -r requirements.txt` and  `pip install -r requirements_dev.txt`.

Prettier is used to format JS and CSS files, you can install it [here](https://prettier.io/docs/en/install)

Run the server using `docker-compose up`.

Our CI enforces properly formatted code. To format the code, run `scripts/format.sh`.
Alternatively, you can comment `/format` on any pull request to automatically run the formatting script and commit the changes.

To run the tests, run `python manage.py test` or `docker exec turmfrontend-web python manage.py test` to run the tests inside Docker.

Once you run the app you will be prompted to login.
If you set both the `ADMIN_EMAIL` and  the `ADMIN_PASSWORD` environment variable,
a admin user will be created with the given credentials, which can be used to login.

## Docker Compose
Run using `docker-compose up` in the root directory of the project. The application will be available at `http://localhost:8000`.
Hot reloading is supported. The data will be saved in a PostgreSQL database, inside the `data` folder.
Optionally use `docker-compose --profile test up` to run a (non-persisting) Nextcloud Container useful for testing.

# Known Limitations
- The Nextcloud container is not persistent. This is by design, as the Nextcloud container is only used for testing purposes.
- The test that interact with the nextcloud will automatically add `test` to the `NC_PREFIX` defined in .env
- When changing the nextcloud prefix while files are uploaded in the nextcloud, the update fails as the prefix is not stored with the observation in the database.  
- During development some migration files might have been deleted. This means that the database might need to be reset when running the application for the first time. If the database was used without mapping the volume to a local folder, simply run `docker-compose down -v` to remove all docker volumes. If the volume was mapped to a local folder, simply delete the folder and run `docker-compose up` again.
- Dependencies are only installed when building the Docker image. If a new dependency is added, you can rebuild the image using `docker-compose up --build` or install `requirements.txt` using `docker exec turmfrontend-web pip install -r requirements.txt`.
