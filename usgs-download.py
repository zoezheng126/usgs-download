# =============================================================================
#  USGS/EROS Inventory Service Example
#  Python - JSON API
#
#  Script Last Modified: 6/17/2020
#  Note: This example does not include any error handling!
#        Any request can throw an error, which can be found in the errorCode proprty of
#        the response (errorCode, errorMessage, and data properies are included in all responses).
#        These types of checks could be done by writing a wrapper similiar to the sendRequest function below
#  Usage: python download_data.py -u username -p password
# =============================================================================

import json
import requests
import sys
import time
import argparse
import os
import zipfile, io
import urllib.request

failure_download = []

# download zip from url 
def download_file(url,filename, output_dir='.'):
    response = requests.get(url, stream=True)
    print(response.status_code)
    if response.status_code == 200:
        filename = filename + '.zip'
        filepath = os.path.join(output_dir, filename)
        urllib.request.urlretrieve(url, filepath)
        print(f'successfully downloaded {filename}')
    else:
        failure_download.append(filename)
        print(f'{filename} not successfully downloaded')

# send http request
def send_request(url, data, api_key=None):
    json_data = json.dumps(data)

    if api_key is None:
        response = requests.post(url, json_data)
    else:
        headers = {'X-Auth-Token': api_key}
        response = requests.post(url, json_data, headers=headers)

    try:
        http_status_code = response.status_code
        if response is None:
            print("No output from service")
            sys.exit()
        output = json.loads(response.text)
        if output['errorCode'] is not None:
            print(output['errorCode'], "- ", output['errorMessage'])
            sys.exit()
        if http_status_code == 404:
            print("404 Not Found")
            sys.exit()
        elif http_status_code == 401:
            print("401 Unauthorized")
            sys.exit()
        elif http_status_code == 400:
            print("Error Code", http_status_code)
            sys.exit()
    except Exception as e:
        response.close()
        print(e)
        sys.exit()
    response.close()

    return output['data']


def main():
    # NOTE :: Passing credentials over a command line argument is not considered secure
    #        and is used only for the purpose of being example - credential parameters
    #        should be gathered in a more secure way for production usage
    # Define the command line arguments

    # user input
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--username', required=True, help='Username')
    parser.add_argument('-p', '--password', required=True, help='Password')
    parser.add_argument('-o', '--output_dir', required=True, help='output directory')

    args = parser.parse_args()

    username = args.username
    password = args.password
    output_dir = args.output_dir

    print("\nRunning Scripts...\n")

    service_url = "https://m2m.cr.usgs.gov/api/api/json/stable/"

    # login
    payload = {'username': username, 'password': password}

    api_key = send_request(service_url + "login", payload)

    print("API Key: " + api_key + "\n")

    dataset_name = "high_res_ortho"

    spatial_filter = {'filterType': "mbr",
                      'lowerLeft': {'latitude': 38.9829, 'longitude': -90.1607},
                      'upperRight': {'latitude': 39.5241, 'longitude': -89.7031}}

    temporal_filter = {'start': '2000-3-1', 'end': '2016-1-1'}

    payload = {'datasetName': dataset_name,
               'spatialFilter': spatial_filter,
               'temporalFilter': temporal_filter}

    print("Searching datasets...\n")
    datasets = send_request(service_url + "dataset-search", payload, api_key)
    print("Found ", len(datasets), " datasets\n")

    # download datasets
    for dataset in datasets:

        # Because I've run this before I know that I want GLS_ALL, I don't want to download anything I don't
        # want, so we will skip any other datasets that might be found, logging it incase I want to look into
        # downloading that data in the future.
        print(dataset['datasetAlias'])
        if dataset['datasetAlias'] != dataset_name:
            print("Found dataset " + dataset['collectionName'] + " but skipping it.\n")
            continue

        # I don't want to limit my results, but using the dataset-filters request, you can
        # find additional filters

        acquisition_filter = {"end": "2015-4-1", "start": "2015-3-1"}

        payload = {'datasetName': dataset['datasetAlias'],
                   'maxResults': 50000,
                   'startingNumber': 1,
                   'sceneFilter': {
                       'spatialFilter': spatial_filter,
                       'acquisitionFilter': acquisition_filter}}

        # Now I need to run a scene search to find data to download
        print("Searching scenes...\n\n")

        scenes = send_request(service_url + "scene-search", payload, api_key)

        # Did we find anything?
        if scenes['recordsReturned'] > 0:
            # Aggregate a list of scene ids
            scene_ids = []
            for result in scenes['results']:
                # Add this scene to the list I would like to download
                scene_ids.append(result['entityId'])

            # Find the download options for these scenes
            # NOTE :: Remember the scene list cannot exceed 50,000 items!
            payload = {'datasetName': dataset['datasetAlias'], 'entityIds': scene_ids}

            download_options = send_request(service_url + "download-options", payload, api_key)
            # Aggregate a list of available products
            downloads = []
            for product in download_options:
                # Make sure the product is available for this scene
                if product['available']:
                    downloads.append({'entityId': product['entityId'],
                                      'productId': product['id']})

            # Did we find products?
            if downloads:
                requested_downloads_count = len(downloads)
                # set a label for the download request
                label = "download-sample"
                payload = {'downloads': downloads,
                           'label': label}
                # Call the download to get the direct download urls
                request_results = send_request(service_url + "download-request", payload, api_key)

                # PreparingDownloads has a valid link that can be used but data may not be immediately available
                # Call the download-retrieve method to get download that is available for immediate download
                if request_results['preparingDownloads'] is not None and len(request_results['preparingDownloads']) > 0:
                    payload = {'label': label}
                    more_download_urls = send_request(service_url + "download-retrieve", payload, api_key)

                    download_ids = []

                    for download in more_download_urls['available']:
                        if str(download['downloadId']) in request_results['newRecords'] or str(
                                download['downloadId']) in \
                                request_results['duplicateProducts']:
                            download_ids.append(download['downloadId'])
                            print("DOWNLOAD: " + download['url'])
                            download_file(download['url'], download['displayId'], output_dir)

                    for download in more_download_urls['requested']:
                        if str(download['downloadId']) in request_results['newRecords'] or str(
                                download['downloadId']) in \
                                request_results['duplicateProducts']:
                            download_ids.append(download['downloadId'])
                            print("DOWNLOAD: " + download['url'])
                            download_file(download['url'],download['displayId'], output_dir)

                    # Didn't get all the requested downloads, call the download-retrieve method again probably
                    # after 30 seconds
                    while len(download_ids) < (requested_downloads_count - len(request_results['failed'])):
                        preparing_downloads = requested_downloads_count - len(download_ids) - len(
                            request_results['failed'])
                        print("\n", preparing_downloads, "downloads are not available. Waiting for 30 seconds.\n")
                        time.sleep(30)
                        print("Trying to retrieve data\n")
                        more_download_urls = send_request(service_url + "download-retrieve", payload, api_key)
                        for download in more_download_urls['available']:
                            if download['downloadId'] not in download_ids and (
                                    str(download['downloadId']) in request_results['newRecords'] or str(
                                download['downloadId']) in request_results['duplicateProducts']):
                                download_ids.append(download['downloadId'])
                                print("DOWNLOAD: " + download['url'])
                                download_file(download['url'], download['displayId'], output_dir)


                else:
                    # Get all available downloads
                    for download in request_results['availableDownloads']:
                        # TODO :: Implement a downloading routine
                        print("DOWNLOAD: " + download['url'])
                        download_file(download['url'], download['displayId'], output_dir)
                        print('# Get all available downloads')
                        
                print("\nAll downloads are available to download.\n")
        else:
            print("Search found no results.\n")

    # Logout so the API Key cannot be used anymore
    endpoint = "logout"
    if send_request(service_url + endpoint, None, api_key) is None:
        print("Logged Out\n\n")
    else:
        print("Logout Failed\n\n")

if __name__ == '__main__':
    main()
    print(failure_download)
