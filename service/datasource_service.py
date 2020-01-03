"""Micro service for getting data from SalesForce API"""

import json
import logging
import requests
from os import environ
from flask import Flask, request, Response
from simple_salesforce import Salesforce
from dao.data_access import DataAccess
from utils.auth_utils import get_access_token

app = Flask(__name__)
env = environ.get

LOG_LEVEL = logging.getLevelName(env('LOG_LEVEL', 'INFO'))
logging.basicConfig(level=LOG_LEVEL)  # stdout logging

API_VERSION = env('API_VERSION', '43.0')
PORT = env('PORT', 5000)
ADDITIONAL_SALESFORCE_TYPES = json.loads(env('SALESFORCE_TYPES', '[]'))
RESPONSE_MIME_TYPE = env('RESPONSE_MIME_TYPE', 'application/json');
AUTH_SCHEMA = env('AUTH_SCHEMA', 'password')

DAO = DataAccess(ADDITIONAL_SALESFORCE_TYPES)

SESAM_JWT = env('SESAM_JWT')
SESAM_API = env('SESAM_API')


def store_token_to_sesam(sesam_api, sesam_jwt, token):
    headers = {"Authorization": "Bearer " + sesam_jwt}
    res = requests.post(sesam_api + "secrets", json={"salesforce_access_token": "Bearer {}".format(token)},
                        headers=headers)
    logging.info("Store salesforce access token to Sesam performed with status code  {}".format(res.status_code))
    if res.status_code > 299:
        logging.warning("Something went wrong while sending token to Sesam node: {}".format(r.text))


@app.route('/<datatype>', methods=['GET'])
def get_entities(datatype):
    token = None
    logging.info("Serving request %s from %s", request.query_string, request.remote_addr)
    if 'password' == AUTH_SCHEMA:
        logging.debug("Getting access token for auth schema 'password'")
        token = get_access_token(env('URL', ""),
                                 env('CLIENT_ID', ""),
                                 env('CLIENT_SECRET', ""),
                                 env('SALESFORCE_USERNAME', ""),
                                 env('SALESFORCE_PASSWORD', ""),
                                 env('SALESFORCE_USER_TOKEN', ""))
        if SESAM_JWT and SESAM_API:
            store_token_to_sesam(SESAM_API, SESAM_JWT, token.get('access_token'))
    else:
        logging.error("Authentication schema is not presented or not supported")
        raise Exception("Authentication schema is not supported")

    sf = Salesforce(instance_url=token.get('instance_url'), session_id=token.get('access_token'),
                    version=API_VERSION)
    since = request.args.get('since')

    entities = sorted(DAO.get_entities(since, datatype, sf),
                      key=lambda k: k["_updated"])
    return Response(json.dumps(entities), mimetype=RESPONSE_MIME_TYPE)


@app.route('/post/<datatype>', methods=['POST'])
def post_data(datatype):
    if 'password' != AUTH_SCHEMA:
        logging.error("Authentication schema is not presented or not supported")
        raise Exception("Authentication schema is not supported")

    logging.debug("Getting access token for auth schema 'password'")
    token = get_access_token(env('URL'), env('CLIENT_ID'), env('CLIENT_SECRET'), env('SALESFORCE_USERNAME'),
                             env('SALESFORCE_PASSWORD'), env('SALESFORCE_USER_TOKEN'))
    sf = Salesforce(instance_url=token.get('instance_url'), session_id=token.get('access_token'))

    entities = request.get_json()

    for entity in entities:
        print(entity)
    return Response()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', threaded=True, port=PORT)
