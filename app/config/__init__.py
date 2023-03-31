import socket
from pathlib import Path

from omegaconf import OmegaConf

project_root = Path(__file__).resolve().parents[2]

CONFIG = OmegaConf.load(Path(__file__).parent.resolve() / "base.yml")

if not CONFIG.APP.get("HOST"):
    CONFIG.APP.HOST = socket.gethostname()

datadir = Path(__file__).parents[1] / "_data"
datadir.mkdir(exist_ok=True)

static = Path(__file__).parent.parent / "static"
static.mkdir(exist_ok=True)

CONFIG["datadir"] = datadir

account_slug = CONFIG["account_slug"]
event_slug = CONFIG["event_slug"]


def get_secret():
    secret_name = "tito/api_ah"
    region_name = "eu-central-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    # Decrypts secret using the associated KMS key.
    secret = get_secret_value_response["SecretString"]
    return secret


token_path = project_root / "_private/TOKEN.txt"
token_path.parent.mkdir(exist_ok=True, parents=True)
if token_path.exists():
    TOKEN = token_path.open().read()
else:
    # AWS
    TOKEN = get_secret()

import boto3
from botocore.exceptions import ClientError

__all__ = ["CONFIG", "TOKEN", "event_slug", "account_slug"]
