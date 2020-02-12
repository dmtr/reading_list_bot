import os


def get_connection_url() -> str:
    host = os.environ.get("POSTGRES_HOST")
    port = int(os.environ.get("POSTGRES_PORT"))
    user = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")
    dbname = os.environ.get("POSTGRES_DBNAME")

    url = "postgresql://{}:{}@{}:{}/{}".format(user, password, host, port, dbname)
    return url
