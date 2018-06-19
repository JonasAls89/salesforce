from collections.__init__ import OrderedDict
from datetime import datetime, timedelta

import pytz
from dateutil.parser import parse
from iso8601 import iso8601
from werkzeug.exceptions import abort

from utils.date_utils import to_transit_datetime


class DataAccess:
    def __init__(self, entities_dict=None):
        """creates object that support standard set of salesforce entities, supplementary entity
        types may be provided as dictionary argument to constructor """
        self._entities = dict(Activity=[], Contact=[], Account=[], Lead=[], Task=[], Event=[],
                              Group=[], Opportunity=[], User=[], EventRelation=[], Case=[])
        if entities_dict:
            self._entities.update(entities_dict)

    def get_entities(self, since, datatype, sf):
        """fetch and return entities of given type that were update since datetime provided in
        since. This function will send Flask.abort(404) error if entity datatype is not in
        supported types list"""
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