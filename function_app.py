import azure.functions as func
import datetime
import json
import logging
import requests

app = func.FunctionApp()

for attr in dir(app):
    print(attr)

@app.route(route="get_newrelic_users", auth_level=func.AuthLevel.Anonymous)
def get_newrelic_users(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )