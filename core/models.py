from datetime import datetime

class Account:
    def __init__(self, email, password, token=None):
        self.email = email
        self.password = password
        self.token = token
        self.connections = []
        self.account_info = {}
        self.stats = {
            "connectCount": 0,
            "livenessCount": 0,
            "statsChecks": 0,
            "totalPoints": 0,
            "referralPoints": 0,
            "lastUpdated": None,
            "startTime": datetime.now(),
            "earningsTotal": 0,
            "connectedNodesRewards": 0,
            "connectedNodesCount": 0,
            "firstName": "",
            "lastName": ""
        }

class Connection:
    def __init__(self, token, extension_id, proxy=None):
        self.token = token
        self.extension_id = extension_id
        self.proxy = proxy
        self.last_ip = None
        self.connect_count = 0
        self.liveness_count = 0
        self.stats_checks = 0
        self.last_connect = None