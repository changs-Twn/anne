import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DB_SERVER = os.environ["DB_SERVER"]
    DB_NAME = os.environ["DB_NAME"]
    DB_UID = os.environ["DB_UID"]
    DB_PWD = os.environ["DB_PWD"]
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev")

    CONN_STR = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={DB_SERVER};"
        f"DATABASE={DB_NAME};"
        f"UID={DB_UID};"
        f"PWD={DB_PWD};"
        "TrustServerCertificate=yes;"
        "Encrypt=yes;"
    )
