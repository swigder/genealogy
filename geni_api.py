import json
import urllib.request
import urllib.parse
import urllib.error

GENI_BASE_URL = 'https://www.geni.com/api/'


class GeniApi:
    def __init__(self):
        with open('access-token', 'r') as f:
            self.access_token = f.read()

    def get(self, api, args):
        args['access_token'] = self.access_token
        url = '{}{}?{}'.format(GENI_BASE_URL, api, urllib.parse.urlencode(args))
        response = urllib.request.urlopen(url)
        return json.loads(response.read())

