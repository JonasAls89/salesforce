# salesforce
Sesam datasource that reads data from Salesforce

[![Build Status](https://travis-ci.org/timurgen/salesforce.svg?branch=master)](https://travis-ci.org/timurgen/salesforce)

# example config
```json
  {
  "_id": "salesforce",
  "type": "system:microservice",
  "docker": {
    "environment": {
      "AUTH_SCHEMA": "password",
      "CLIENT_ID": "$ENV(salesforce-client_id)",
      "CLIENT_SECRET": "$SECRET(salesforce-client_secret)",
      "SALESFORCE_PASSWORD": "$SECRET(salesforce-password)",
      "SALESFORCE_TYPES": "{\"Custom_type__c\":[]}",
      "SALESFORCE_USERNAME": "$ENV(salesforce-user)",
      "SALESFORCE_USER_TOKEN": "$SECRET(salesforce-security_token)",
      "URL": "$ENV(salesforce-auth_url)"
    },
    "image": "ohuenno/salesforce",
    "port": 5000
  }
},{
  "_id": "salesforce-account",
  "type": "pipe",
  "source": {
    "type": "conditional",
    "alternatives": {
      "dev": {
        "type": "embedded",
        "entities": []
      },
      "prod": {
        "type": "json",
        "system": "salesforce",
        "url": "Account"
      },
      "test": {
        "type": "json",
        "system": "salesforce",
        "url": "Account"
      }
    },
    "condition": "$ENV(node-env)"
  },
  "transform": {
    "type": "dtl",
    "rules": {
      "default": [
        ["copy", "*"],
        ["add", "_id", "_S.Id"],
        ["add", "rdf:type",
          ["ni", "salesforce", "_S.attributes.type"]
        ],
        ["make-ni", "account", "Id"],
        ["make-ni", "contact", "PersonContactId"],
        ["make-ni", "recordtype", "RecordTypeId"]
      ]
    }
  },
  "pump": {
    "cron_expression": "0 0 1 1 ?"
  }
}

```
