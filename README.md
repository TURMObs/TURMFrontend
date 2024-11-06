# Deployement
## Prerequisites
1. [Docker](https://www.docker.com/get-started)
2. [Docker Compose](https://docs.docker.com/compose/install/) (already packaged in Docker Desktop)
3. Environment variables:

    | **Environment Variable** | **Description**                                               | **Required** | **Recommended Value**                          |
    |--------------------------|---------------------------------------------------------------|--------------|------------------------------------------------|
    | ``POSTGRES_DB``          | Name of the Postgres database                                 | **Yes**      | `TURMFrontend`                                 |
    | `POSTGRES_USER`          | Superuser of the Postgres Database                            | **Yes**      | `admin`                                        |
    | `POSTGRES_PASSWORD`      | Superuser password                                            | **Yes**      | Secure password                                |
    | `DEBUG`                  | Whether Django runs the server in DEBUG mode (default: False) | **No**       | `True` for development, `False` for deployment |
    
    
    
The easiest way is to create a local `.env` file in the root directory of the project with the following content:
```.env
DEBUG=True
POSTGRES_DB=TURMFrontend
POSTGRES_USER=<user>
POSTGRES_PASSWORD=<password>
```

## Docker Compose
Run using `docker-compose up` in the root directory of the project. The application will be available at `http://localhost:8000`.
Hot reloading is supported. The data will be saved in a PostgreSQL database, inside the `data` folder.
