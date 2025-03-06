from azure.identity import DefaultAzureCredential
# from azure.keyvault.secrets import SecretClient
import azure.functions as func
import os
# import datetime
import json
import logging
import requests

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

do_not_delete = ["thielman@sggtech.com","test.user1@insightglobal.com","newrelic.svc@insightglobal.com"]

BB_URL = 'https://api.bitbucket.org/2.0/repositories'
BB_API_KEY = os.getenv('BB_API_KEY')
# NR_URL = 'https://api.newrelic.com/graphql'  # Endpoint for fetching users
api_key = os.getenv('NR_LICENSE_KEY')

# Define the headers
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {BB_API_KEY}"}
# headers = {"Content-Type": "application/json", "Api-Key": f"{NR_API_KEY}"}

# # Retrieve the Key Vault URL from environment variables
# # key_vault_url       = os.getenv["NR_LICENSE_KEY"]

# # Create a SecretClient using DefaultAzureCredential
# # credential = DefaultAzureCredential()
# # client     = SecretClient(vault_url=key_vault_url, credential=credential)

# # secret_key_name = "newrelic-license-key"
# # api_key         = client.get_secret(secret_key_name)
# api_key         = os.getenv("NR_LICENSE_KEY")

def print_version_line(file_contents):
    for line in file_contents.splitlines():
        if line.startswith("version:"):
            return line
    return None


def get_file_contents(url, access_token=None):
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.text
    else:
        print(f"Failed to retrieve file: {response.status_code}")
        return None
    

def get_meta_config_files(repo_owner, repo_slug, file_path, branch, output_file):
    url = f'{BB_URL}/{repo_owner}/{repo_slug}/src/{branch}/{file_path}'
    response = requests.get(url, headers=headers)
    meta_files = []
    if response.status_code == 200:
        data = response.json()
        for escape_path in data['values']:
            if escape_path['path'].endswith('meta.yml'):
                meta_files.append(escape_path['path'])
        return meta_files
    

def list_repos_with_keyword(workspace, keyword):
    url = f'{BB_URL}/{workspace}'
    params = {"q": f"name~\"{keyword}\""}
    repos = []
    response = requests.get(url, headers=headers, params=params)

    while url:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            break
        data = response.json()
        repos.extend(data.get("values", []))
        url = data.get("next")
    return repos


def format_output_text(input_text: dict) -> str:
    output_text = ""
    sorted_dict_by_values = dict(sorted(input_text.items()))
    for appname, version_num in sorted_dict_by_values.items():
        output_text = f"{output_text}\n{str(appname)}: {str(version_num)}" 
    return output_text


def create_user_remove_list(azure_response, new_relic_users):
    # print the user names and emails addresses
    if new_relic_users is not None:
        nr_emails = {user['email'].lower() for user in new_relic_users}

    # Convert the sets to lists
    list_nr = list(nr_emails)
    list_az = list(azure_response)

    list_nr.sort()
    list_az.sort()

    nr_not_az = [item for item in list_nr if item not in list_az]

    return nr_not_az


def get_users_from_azure():
    # Create a credential object using the DefaultAzureCredential class
    credential    = DefaultAzureCredential()
    group_id      = '9436c231-56f9-4b31-a6c6-5784f54d80f3'
    ms_graph_base = "https://graph.microsoft.com"
    default_url   = f"{ms_graph_base}/.default"
    url           = f"{ms_graph_base}/v1.0/groups/{group_id}/members"

    # Acquire token for Microsoft Graph
    token_response = credential.get_token(default_url)

    # set up header with access token
    headers = {
        'Authorization': 'Bearer ' + token_response.token,
        'Content-Type': 'application/json'
    }

    names = []

    while url:
        # Grab the list of users from Azure
        resp = requests.get(url, headers=headers)
        data = resp.json()
        names.extend([item['mail'].lower() for item in data['value']])
        url = data.get('@odata.nextLink')  # Get the URL for the next page of results

    return names


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

@app.route(route="get_newrelic_users")
def get_newrelic_users(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    # gets a list of users from Entra ID
    azure_user_list  = get_users_from_azure()

    # get a list of users from New Relic
    new_relic_users  = get_users_from_new_relic(api_key)

    # # creats a list of users to be deleted from New Relic based on list in Entra ID
    # user_remove_list = create_user_remove_list(azure_user_list, new_relic_users)

    # if user_remove_list:
    #     print(f"\n\tThese are the users who will be removed from New Relic:\n")
    #     for nr_user_name in user_remove_list:
    #         print(f"\t\t{nr_user_name}")

    if new_relic_users: # user_remove_list:
        user_list = "<ul>"
        for user in new_relic_users: # user_remove_list:
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

@app.route(route="http_trigger")
def http_trigger(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    keyword = "k8s-config-repo"
    bitbucket_workspace = "insightglobal"
    app_versions = {}
    repos = list_repos_with_keyword(bitbucket_workspace, keyword)
    excluded_repos = {"backstage-k8s-config-repo", "k8s-config-repo", "platform-k8s-config-repo"}
    branch = 'main'
    output_file = 'output.txt'

    if repos:
        for repo in repos:
            stub = 'k8s'
            file_path = ""
            branch = 'main'
            output_file = 'output.txt'
            excluded_repos = ("backstage-k8s-config-repo","k8s-config-repo","platform-k8s-config-repo")

            if repo['name'] not in excluded_repos:
                stub = repo['name'].split("-k8s-")[0]
                namespace = f"{stub}-prd"
                file_path = f'env/{namespace}/task'
        
            if repo['name'] not in excluded_repos:
                meta_config_files = get_meta_config_files(bitbucket_workspace, repo['slug'], file_path, branch, output_file)

                if meta_config_files:
                    for meta_files_path in meta_config_files:
                        app_name         = meta_files_path.split('/')[-1][:-9] # meta_file_yml[:-9]
                        version_file_url = f"{BB_URL}/{bitbucket_workspace}/{repo['slug']}/src/{branch}/{meta_files_path}"
                        file_contents    = get_file_contents(version_file_url, access_token=BB_API_KEY)
                        if file_contents:
                            version_value = print_version_line(file_contents)
                            app_versions[app_name] = version_value[9:]

        output = format_output_text(app_versions)

        return func.HttpResponse(f"These are the Application Versions in PROD...\n\n{output}")
    else:
        return func.HttpResponse(
             f"This is without using any parameters.\n{output}",
             status_code=200
        )
