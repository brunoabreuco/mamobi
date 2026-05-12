import logging

from flask import has_request_context, request
from flask.logging import default_handler


# ref: https://flask.palletsprojects.com/en/stable/logging/
class RequestFormatter(logging.Formatter):
    def format(self, record):
        if has_request_context():
            record.url = request.url
            record.remote_addr = request.remote_addr
        else:
            record.url = None
            record.remote_addr = None

        return super().format(record)


formatter = RequestFormatter(
    "[%(asctime)s] %(remote_addr)s requested %(url)s\n"
    "%(levelname)s in %(module)s: %(message)s"
)

logging.basicConfig(level=logging.INFO)

default_handler.setFormatter(formatter)
