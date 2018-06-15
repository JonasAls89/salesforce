from flask import Flask, request, Response

import json
from simple_salesforce import Salesforce
import logging
import os
import requests
from collections.__init__ import OrderedDict
from datetime import datetime, timedelta
import pytz
from dateutil.parser import parse
from iso8601 import iso8601
from werkzeug.exceptions import abort

app = Flask(__name__)
API_VERSION = '43.0'
logger = logging.getLogger("salesforce")


class DataAccess:
    def __init__(self):
        self._entities = dict(Activity=[], Contact=[], Account=[], Lead=[], Task=[], Event=[],
                              Group=[], Opportunity=[], User=[], EventRelation=[], Case=[],
                              Flight__c=[])

    def get_entities(self, since, datatype, sf):
        if datatype not in self._entities:
            abort(404)
        if not self._entities[datatype]:
            fields = getattr(sf, datatype).describe()["fields"]
            self._entities[datatype] = fields
        if since is None:
            return self.get_entitiesdata(datatype, since, sf)
        else:
            return [entity for entity in self.get_entitiesdata(datatype, since, sf) if
                    entity["_updated"] > since]

    def get_entitiesdata(self, datatype, since, sf):
        now = datetime.now(pytz.UTC)
        entities = []
        end = datetime.now(pytz.UTC)  # we need to use UTC as salesforce API requires this

        if since is None:
            result = [x['Id'] for x in sf.query("SELECT Id FROM %s" % datatype)["records"]]
        else:
            start = iso8601.parse_date(since)
            if getattr(sf, datatype):
                if end > (start + timedelta(seconds=60)):
                    result = getattr(sf, datatype).updated(start, end)["ids"]
                    deleted = getattr(sf, datatype).deleted(start, end)["deletedRecords"]
                    for e in deleted:
                        c = OrderedDict({"_id": e["id"]})
                        c.update({"_updated": "%s" % e["deletedDate"]})
                        c.update({"_deleted": True})

                        entities.append(c)
        if result:
            for e in result:
                c = getattr(sf, datatype).get(e)
                c.update({"_id": e})
                c.update({"_updated": "%s" % c["LastModifiedDate"]})

                for property, value in c.items():
                    schema = [item for item in self._entities[datatype] if item["name"] == property]
                    if value and len(schema) > 0 and "type" in schema[0] and schema[0][
                        "type"] == "datetime":
                        c[property] = to_transit_datetime(parse(value))

                entities.append(c)

        return entities


data_access_layer = DataAccess()
env = os.environ.get


def get_access_token(url, client_id, client_secret, username, password, user_security_token,
                     grant_type='password'):
    """function to obtain SalesForce access token using username/password auth flow"""
    payload = (('client_id', client_id), ('client_secret', client_secret), ('username', username),
               ('password', password + user_security_token), ('grant_type', grant_type))
    res = requests.post(url=url, data=payload).json()
    if res.get('error'):
        raise Exception(res.get('error_description'))
    return res


token = get_access_token(env('URL', ""),
                         env('CLIENT_ID', ""),
                         env('CLIENT_SECRET', ""),
                         env('SALESFORCE_USERNAME', ""),
                         env('SALESFORCE_PASSWORD', ""),
                         env('SALESFORCE_USER_TOKEN', ""))

sf = Salesforce(instance_url=token.get('instance_url'), session_id=token.get('access_token'),
                version=API_VERSION)


@app.route('/<datatype>', methods=['GET'])
def get_entities(datatype):
    since = request.args.get('since')
    entities = sorted(data_access_layer.get_entities(since, datatype, sf),
                      key=lambda k: k["_updated"])
    return Response(json.dumps(entities), mimetype='application/json')


def datetime_format(dt):
    return '%04d' % dt.year + dt.strftime("-%m-%dT%H:%M:%SZ")


def to_transit_datetime(dt_int):
    return "~t" + datetime_format(dt_int)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
