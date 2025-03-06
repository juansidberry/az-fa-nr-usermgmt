import azure.functions as func
import os
import datetime
import json
import logging
import requests

app = func.FunctionApp()

do_not_delete = ["thielman@sggtech.com","test.user1@insightglobal.com","newrelic.svc@insightglobal.com"]
api_key       = os.getenv["KEY_VAULT_URL"]
url           = 'https://api.newrelic.com/graphql'  # Endpoint for fetching users
headers       = {
    "Api-Key": api_key,
    "Content-Type": "application/json"
}


def get_users_from_new_relic(api_key):
    results = []
    url     = 'https://api.newrelic.com/graphql'  # Endpoint for fetching users
    headers = {
        "Api-Key": api_key,
        "Content-Type": "application/json"
    }

    # Define the GraphQL query
    query = """
    {
      actor {
        organization {
          userManagement {
            authenticationDomains(id: "6e2749c6-e744-4bc8-b30e-587ec574aca7") {
              authenticationDomains {
                users {
                  users {
                    id
                    email
                  }
                }
              }
            }
          }
        }
      }
    }
    """

    # Make the request
    response = requests.post(url, headers=headers, json={'query': query})

    if response.status_code == 200:
        # Parse the response JSON and extract the user data
        data = json.loads(json.dumps(response.json()))

        user_data = data['data']['actor']['organization']['userManagement']['authenticationDomains']['authenticationDomains'][0]['users']['users']

        for user in user_data:
            if user['email'] in do_not_delete:
                pass
            else:
                results.append(user)

        return results
    else:
        logging.info("Failed to fetch users:", response.status_code, response.text)
        return None

@app.route(route="get_newrelic_users", auth_level=func.AuthLevel.Anonymous)
def get_newrelic_users(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    # get a list of users from New Relic
    new_relic_email  = get_users_from_new_relic(api_key)

    # name = req.params.get('name')
    # if not name:
    #     try:
    #         req_body = req.get_json()
    #     except ValueError:
    #         pass
    #     else:
    #         name = req_body.get('name')

    if new_relic_email:
        user_list = "<ul>"
        for user in new_relic_email:
            user_list += f"<li>{user}</li>"
        user_list += "</ul>"
        logging.info('YEA! email addresses from New Relic.')
        return func.HttpResponse(f"<html><body>{user_list}</body></html>", mimetype="text/html")
        # return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        logging.info('NAH! no email addresses from New Relic.')
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )