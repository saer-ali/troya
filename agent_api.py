import requests
import os

class AgentAPI:
    def __init__(self):
        self.base_url = os.getenv("BASE_URL")
        self.agent_user = os.getenv("AGENT_USER")
        self.agent_pass = os.getenv("AGENT_PASS")
        self.parent_id = os.getenv("PARENT_ID")
        self.access_token = None
        self.login()

    def login(self):
        try:
            url = self.base_url + "global/api/Auth/login"
            payload = {
                "userName": self.agent_user,
                "password": self.agent_pass,
                "parentId": self.parent_id
            }
            r = requests.post(url, json=payload, timeout=30)
            if r.status_code == 200:
                data = r.json()
                self.access_token = data.get("result", {}).get("accessToken")
        except Exception as e:
            print(f"Login error: {e}")

    def auth_headers(self):
        return {"Authorization": f"Bearer {self.access_token}"}

    def register_player(self, username, password):
        url = self.base_url + "global/api/UserApi/registerPlayer"
        payload = {"username": username, "password": password}
        try:
            r = requests.post(url, json=payload, headers=self.auth_headers(), timeout=30)
            return {"success": r.status_code == 200, "error": r.text if r.status_code != 200 else None}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_player_id(self, username):
        url = self.base_url + "global/api/UserApi/getPlayersForCurrentAgent"
        try:
            r = requests.post(url, headers=self.auth_headers(), json={"start": 0, "limit": 100}, timeout=30)
            if r.status_code == 200:
                data = r.json()
                for player in data.get("result", {}).get("records", []):
                    if player.get("username") == username:
                        return player.get("playerId")
        except Exception as e:
            print(f"get_player_id error: {e}")
        return None

    def get_balance(self, player_id):
        url = self.base_url + "global/api/UserApi/getBalance"
        try:
            r = requests.post(url, headers=self.auth_headers(), json={"playerId": player_id}, timeout=30)
            if r.status_code == 200:
                return r.json().get("result", [])
        except Exception as e:
            print(f"get_balance error: {e}")
        return []

    def deposit(self, player_id, amount):
        url = self.base_url + "global/api/UserApi/deposit"
        payload = {"playerId": player_id, "amount": amount}
        try:
            r = requests.post(url, json=payload, headers=self.auth_headers(), timeout=30)
            return {"success": r.status_code == 200, "message": r.text}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def withdraw(self, player_id, amount):
        url = self.base_url + "global/api/UserApi/withdraw"
        payload = {"playerId": player_id, "amount": amount}
        try:
            r = requests.post(url, json=payload, headers=self.auth_headers(), timeout=30)
            return {"success": r.status_code == 200, "message": r.text}
        except Exception as e:
            return {"success": False, "message": str(e)}
