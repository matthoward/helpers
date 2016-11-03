import requests
import sys

if (len(sys.argv) != 3):
    print('Usage: python swagger.py <host1> <host2>')
    sys.exit(0);

class Param:
    def __init__(self, json):
        self.name = json['name']
        self.required = json['required']
        self.type = json['type']
        self.paramType = json['paramType']
        self.description = ""
        if (json.has_key('description')):
            self.description = json['description']
        self.itemsType = None
        if (json.has_key('items')):
            if (json['items'].has_key('$ref')):
                self.itemsType = json['items']["$ref"]
            elif (json['items'].has_key('type')):
                self.itemsType = json['items']["type"]

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __hash__(self):
        return hash((self.name, self.required, self.type, self.paramType,
                    self.description, self.itemsType))

class ApiDefinition:
    def __init__(self, base, path, method, params):
        self.base = base
        self.path = path
        self.method = method
        self.params = params

    def __key(self):
        return (self.path, self.method, str(self.params))

    def __repr__(self):
        return '{}:{}'.format(self.method.rjust(4, ' '),
                              self.path)

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __hash__(self):
        return hash(self.__key())

    def __getitem__(self, item):
        return self.__dict__.get(item)

class Swagger:
    versionBase = ''
    def __init__(self, url):
        self.url = url

    def __repr__(self):
        return '{}: {}'.format(self.__class__.__name__,
                                  self.url)
    def _url(self, path):
        return self.url + path

    def get_api_versions(self):
        return requests.get(self._url('/apiVersions'))

    def get_api_resources(self):
        self.versionBase = self.get_api_versions().json()[0] # tango only uses a single version
        apis = requests.get(self._url('{}'.format(self.versionBase)))
        return apis

    def get_api_resource_details(self, resource):
        url = self._url('{}'.format(resource))
        resources = requests.get(url)
        return resources


s1 = Swagger(sys.argv[1]) # 'http://tanrflowsrv.tango.qa.wmg.com'
s2 = Swagger(sys.argv[2]) # 'http://tanrflowsrv.tango-roy.e2e.wmg.com'

def safeGet(obj, prop):
    if obj is not None:
        return obj[prop]
    return None

def strPadL(obj, len, pad):
    return str(obj).ljust(len, pad)

def strPadR(obj, len, pad):
    return str(obj).rjust(len, pad)

def printCompareParams(p1, p2):
    s1 = { x['name']: Param(x) for x in p1}
    s2 = { x['name']: Param(x) for x in p2}
    diffs = set(s1.values()) ^ set(s2.values())
    diff_params = {x.name for x in diffs}
    for paramName in diff_params:
        if (s1.has_key(paramName) and not s2.has_key(paramName)):
            print('       + {}'.format(paramName))
        elif (s2.has_key(paramName) and not s1.has_key(paramName)):
            print('       - {}'.format(paramName))
        else:
            print('       ~ {}'.format(paramName))
            for prop in s1[paramName].__dict__.keys():
                p1 = s1[paramName].__dict__[prop]
                p2 = s2[paramName].__dict__[prop]
                if (s1[paramName].__dict__[prop] != s2[paramName].__dict__[prop]):
                    print('           + {}={}'.format(strPadR(prop,11,' '), p1))
                    print('           - {}={}'.format(strPadR(prop,11,' '), p2))

def printCompare(strapi, api1, api2):
    l=40
    print('**************************')
    #print('{}:{}'.format(strapi[1].rjust(4, ' '),strapi[0]))
    if ((api1 is not None) and (api2 is None)):
        print('+ {}:{}'.format(strapi[1],strapi[0]))
    elif ((api1 is None) and (api2 is not None)):
        print('- {}:{}'.format(strapi[1],strapi[0]))
    else:
        print('~ {}:{}'.format(strapi[1],strapi[0]))

    if ((api1 is not None) and (api2 is not None)):
        print('   PARAMS:')
        printCompareParams(api1.params, api2.params)
        #for param in api2.params:

    print('')


def get_api_defs(swagger):
    apiDefs = {}
    for base_api in sorted(swagger.get_api_resources().json()['apis'], key=lambda a: a['path']):
        resourcePath = '{}{}'.format(swagger.versionBase, base_api['path'])
        resources = swagger.get_api_resource_details(resourcePath).json()
        for api in sorted(resources['apis'], key=lambda a: a['path']):
            for op in api['operations']:
                apiDefs[api['path'], op['method']] = ApiDefinition(swagger.url, api['path'], op['method'], op['parameters'])
                ## print('{} {}'.format(op['method'],api['path']))
    return apiDefs

s1Defs = get_api_defs(s1)
s2Defs = get_api_defs(s2)

sym_diffs = set(s1Defs.values()) ^ set(s2Defs.values())
diff_keys = []

for apiDef in sorted(sym_diffs, key=lambda a: (a.path, a.method)):
    diff_keys.append((apiDef.path, apiDef.method))
    #print('{} === {}'.format(apiDef, apiDef in s2Defs))

for api in sorted(diff_keys):
    printCompare(api, s1Defs.get(api), s2Defs.get(api))

#for apiDef in sorted(sym_diffs, key=lambda a: (a.path, a.method)):
#    print('{} === {}'.format(apiDef, apiDef in s2Defs))
