"""Micro service for getting data from SalesForce API"""

import json
from os import environ
from flask import Flask, request, Response
from simple_salesforce import Salesforce
from dao.data_access import DataAccess
from utils.auth_utils import get_access_token

app = Flask(__name__)
env = environ.get

API_VERSION = env('API_VERSION', '43.0')
PORT = env('PORT', 5000)
ADDITIONAL_SALESFORCE_TYPES = json.loads(env('SALESFORCE_TYPES', '[]'))
RESPONSE_MIME_TYPE = env('RESPONSE_MIME_TYPE', 'application/json');
AUTH_SCHEMA = env('AUTH_SCHEMA', 'password')

DAO = DataAccess(ADDITIONAL_SALESFORCE_TYPES)


@app.route('/<datatype>', methods=['GET'])
def get_entities(datatype):
    token = None

    if 'password' == AUTH_SCHEMA:
        token = get_access_token(env('URL', ""),
                                 env('CLIENT_ID', ""),
                                 env('CLIENT_SECRET', ""),
                                 env('SALESFORCE_USERNAME', ""),
                                 env('SALESFORCE_PASSWORD', ""),
                                 env('SALESFORCE_USER_TOKEN', ""))
    else:
        raise Exception("Authentication schema is not supported")

    sf = Salesforce(instance_url=token.get('instance_url'), session_id=token.get('access_token'),
                    version=API_VERSION)
    since = request.args.get('since')
    print(since)
    entities = sorted(DAO.get_entities(since, datatype, sf),
                      key=lambda k: k["_updated"])
    return Response(json.dumps(entities), mimetype=RESPONSE_MIME_TYPE)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', threaded=True, port=PORT)
