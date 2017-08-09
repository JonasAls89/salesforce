from functools import wraps
from flask import Flask, request, Response, abort
from datetime import datetime, timedelta
import os

import json
import pytz
from simple_salesforce import Salesforce
import iso8601
import logging
from collections import OrderedDict

app = Flask(__name__)

logger = None

class DataAccess:
    def __init__(self):
        self._entities = {"Activity": [], "Contact": [], "Account": [], "Lead": [], "Task": [], "Event": [], "Group": [], "Opportunity": [], "User": [], "EventRelation": [], "Case": []}

    def get_entities(self, since, datatype, sf):
        if not datatype in self._entities:
            abort(404)
        if since is None:
            return self.get_entitiesdata(datatype, since, sf)
        else:
            return [entity for entity in self.get_entitiesdata(datatype, since, sf) if entity["_updated"] > since]

    def get_entitiesdata(self, datatype, since, sf):
        # if datatype in self._entities:
        #     if len(self._entities[datatype]) > 0 and self._entities[datatype][0]["_updated"] > "%sZ" % (datetime.now() - timedelta(hours=12)).isoformat():
        #        return self._entities[datatype]
        now = datetime.now(pytz.UTC)
        entities = []
        end = datetime.now(pytz.UTC)  # we need to use UTC as salesforce API requires this

        if since is None:
            #fields = getattr(sf, datatype).describe()["fields"]
            result = [x['Id'] for x in sf.query("SELECT Id FROM %s" % (datatype))["records"]]
        else:
            start = iso8601.parse_date(since)
            if getattr(sf, datatype):
                if end > (start + timedelta(seconds=60)):
                    result = getattr(sf, datatype).updated(start, end)["ids"]
                    deleted = getattr(sf, datatype).deleted(start, end)["deletedRecords"]
                    for e in deleted:
                        c = OrderedDict({"_id": e["id"]})
                        # c = {k: v for k, v in c.items() if v}
                        c.update({"_updated": "%s" % e["deletedDate"]})
                        c.update({"_deleted": True})

                        entities.append(c)
        if result:
            for e in result:
                c = getattr(sf, datatype).get(e)
               # c = {k: v for k, v in c.items() if v}
                c.update({"_id": e})
                c.update({"_updated": "%s" % c["LastModifiedDate"]})

                entities.append(c)

        self._entities[datatype] = entities
        return self._entities[datatype]

data_access_layer = DataAccess()

def get_var(var):
    envvar = None
    if var.upper() in os.environ:
        envvar = os.environ[var.upper()]
    else:
        envvar = request.args.get(var)
    logger.info("Setting %s = %s" % (var, envvar))
    return envvar

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth:
            return authenticate()
        return f(*args, **kwargs)

    return decorated

@app.route('/<datatype>', methods=['GET'])
@requires_auth
def get_entities(datatype):
    since = request.args.get('since')
    instance = get_var('instance') or "prod"
    use_sandbox = False
    if instance == "sandbox":
        use_sandbox = True
        logger.info("Using sandbox")
    auth = request.authorization
    token, username = auth.username.split('\\', 1)
    password = auth.password
    sf = Salesforce(username, password, token, sandbox=use_sandbox)
    entities = sorted(data_access_layer.get_entities(since, datatype, sf), key=lambda k: k["_updated"])

    return Response(json.dumps(entities), mimetype='application/json')



@app.route('/<datatype>', methods=['POST'])
@requires_auth
def receiver(datatype):
    # get entities from request and write each of them to a file
    entities = request.get_json()
    app.logger.info("Updating entity of type %s" % (datatype))
    app.logger.debug(json.dumps(entities))
    instance = get_var('instance') or "prod"
    use_sandbox = False
    if instance == "sandbox":
        use_sandbox = True
        logger.info("Using sandbox")
    auth = request.authorization
    token, username = auth.username.split('\\', 1)
    sf = Salesforce(username, auth.password, token, sandbox=use_sandbox)

    if getattr(sf, datatype):
        transform(datatype, entities, sf)# create the response
    return Response("Thanks!", mimetype='text/plain')

def transform(datatype, entities, sf):
    global ids
    # create output directory
    c = None
    listing = []
    if not isinstance(entities, (list)):
        listing.append(entities)
    else:
        listing = entities
    for e in listing:
        app.logger.info("Updateing entity internal id %s of type %s" % (e["_id"], datatype))
        del e["_id"]
        if not ("_deleted" in e and e["_deleted"]):
            if "Id" in e:
                app.logger.debug("Getting entity %s of type %s" % (e["Id"], datatype))
                c = getattr(sf, datatype).get(e["Id"])
            if not c and "sesam_id__c" in e:
                try:
                    c = getattr(sf, datatype).get_by_custom_id("sesam_id__c", e["sesam_id__c"])
                except:
                    pass
            if not c:
                d = []
                for p in e.keys():
                    if p.startswith("_"):
                        d.append(p)
                for p in d:
                    del(e[p])
                if "Id" in e:
                    del (e["Id"])
                getattr(sf, datatype).create(e)
        if "_deleted" in e and e["_deleted"] :
            if "Id" in e:
                app.logger.info("Deleting entity %s of type %s" % (e["Id"],datatype))
                try:
                    getattr(sf, datatype).delete(c["Id"])
                except Exception as err:
                    app.logger.info("Entity %s of type %s does not exist. Ignoring error: %s..." % (e["Id"], datatype, type(err)))
                    pass
        else:
            d = []
            for p in e.keys():
                if p.startswith("_"):
                    d.append(p)
            for p in d:
                del(e[p])
            if "Id" in e:
                del (e["Id"])
            getattr(sf, datatype).update(c["Id"], e)


if __name__ == '__main__':
    # Set up logging
    format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logger = logging.getLogger('salesforce-microservice')

    # Log to stdout
    stdout_handler = logging.StreamHandler()
    stdout_handler.setFormatter(logging.Formatter(format_string))
    logger.addHandler(stdout_handler)

    logger.setLevel(logging.DEBUG)

    app.run(debug=True, host='0.0.0.0')

