import datetime
import json
import logging
import threading
import time
from math import sqrt
from typing import List

import flask
import requests

from ...utils import get_cache_dir


class MeterHistory:
    def __init__(self, logger: logging.Logger, max_entries: int = 100):
        self.logger = logger
        self.cache = get_cache_dir()

        self.max_entries: int = max_entries
        self.entries: List = self.restore_entries()

    def restore_entries(self):
        try:
            with open(self.cache / "meter_history.json", "r") as fp:
                return json.load(fp)["history"]
        except (FileNotFoundError, json.JSONDecodeError):
            self.logger.warning("Could not restore previous meter history")
            return []

    def save_entries(self):
        with open(self.cache / "meter_history.json", "w") as fp:
            json.dump({"history": self.entries}, fp)

    def add_entry(self, meter_info: dict):
        meter_info["timestamp"] = time.time()
        self.entries.append(meter_info)

        while len(self.entries) > self.max_entries:
            self.entries.pop(0)

        self.save_entries()

    def filter_entries(self, timestamp: float):
        return [info for info in self.entries if info["timestamp"] > timestamp]


class Manager:
    def __init__(self, config, app, logger: logging.Logger):
        self.config = config
        self.logger: logging.Logger = logger
        self.cache = get_cache_dir()

        self.automatic_mode = None
        self.manual_power_limit = None
        self.session_info = None

        self.restore_session()

        self.history = MeterHistory(self.logger.getChild("history"))

        self.daemon = threading.Thread(target=self.background_update, args=(app, ), name="charge_manager_daemon", daemon=True)
        self.daemon.start()

    def restore_session(self):
        try:
            with open(self.cache / "manager_session.json", "r") as fp:
                sess = json.load(fp)
                self.session_info = sess
                self.automatic_mode = sess["automatic_mode"]
                self.manual_power_limit = sess["manual_power_limit"]
        except (FileNotFoundError, json.JSONDecodeError):
            self.logger.warning("Could not restore previous manager session")
            self.session_info = None
            self.automatic_mode = True
            self.manual_power_limit = 23000.0

    def persist_session(self):
        with open(self.cache / "manager_session.json", "w") as fp:
            self.session_info["automatic_mode"] = self.automatic_mode
            self.session_info["manual_power_limit"] = self.manual_power_limit
            json.dump(self.session_info, fp)

    def background_update(self, app):
        client = app.test_client()
        try:
            while True:
                meter_info = self.handle_meters(client)
                self.history.add_entry(meter_info)

                for _ in range(20):
                    sess = json.loads(client.get("/keba/session").data)
                    if self.session_info is None or sess["Session ID"] != self.session_info["Session ID"]:
                        self.start_session(sess)
                    self.persist_session()
                    for _ in range(2):
                        time.sleep(5)
                        if self.automatic_mode:
                            percent_soc = 100.

                            if self.session_info["RFID tag"] == "0400069ad8648500":
                                vehicle_info: dict = json.loads(client.get(f"/bmw/state?vehicle=i32020").data)
                                percent_soc = vehicle_info["chargingLevelHv"]

                            if percent_soc < 60.:
                                client.put(f"/keba/power?current={6000}&delay=1")
                            else:
                                meter_info = self.handle_meters(client)
                                powerwall_soe = self.handle_powerwall_soe()["percentage"]

                                if powerwall_soe > 80.:
                                    self.session_info["charging"] = True
                                elif powerwall_soe < 50.:
                                    self.session_info["charging"] = False
                                else:
                                    self.session_info["charging"] = self.session_info.get("charging", False)

                                if self.session_info["charging"]:
                                    client.put(f"/keba/power?current={6000}&delay=1")
                                else:
                                    client.put(f"/keba/power?current=0&delay=1")
                        else:
                            current = 1000 * self.power_to_phase_current(self.manual_power_limit)  # current limit in mA
                            if current < 6000 and current != 0:
                                current = 6000
                            if current > 63000:
                                current = 63000
                            client.put(f"/keba/power?current={current}&delay=1")
        except:
            self.logger.exception("exception occurred!")
            self.background_update(app)

    def start_session(self, new_session_info: dict):
        self.logger.info("New session started!")
        self.session_info = new_session_info
        self.automatic_mode = True

    @staticmethod
    def power_to_phase_current(power):
        # returns the current in A from Watts of power
        # this assumes 384 volts of effective voltage
        return power / (sqrt(3) * 384)

    def attach_endpoints(self, app: flask.Flask):
        app.add_url_rule("/manager/meters", "manager_meters", self.handle_meters, methods=["GET"])
        app.add_url_rule("/manager/meters/history", "manager_meters_history", self.handle_history, methods=["GET"])
        app.add_url_rule("/manager/mode", "manager_mode", self.handle_mode, methods=["GET", "PUT"])
        app.add_url_rule("/manager/limit", "manager_limit", self.handle_manual_current_limit, methods=["GET", "PUT"])
        app.add_url_rule("/manager/session", "manager_session", self.handle_session, methods=["GET"])
        app.add_url_rule("/manager/powerwall/soe", "manager_powerwall_soe", self.handle_powerwall_soe, methods=["GET"])
        self.logger.info("Attached endpoints.")

    def handle_powerwall_soe(self):
        logging.captureWarnings(True)
        resp = requests.get(f'{self.config["powerwall_host"]}/api/system_status/soe', verify=False)
        logging.captureWarnings(False)
        return json.loads(resp.text)

    def handle_history(self):
        timestamp = flask.request.args.get('timestamp')
        if timestamp is None:
            return {"history": self.history.entries}
        else:
            self.logger.info(f"sending history more recent than {timestamp}")
            return {"history": self.history.filter_entries(float(timestamp))}

    def handle_session(self):
        return self.session_info

    def handle_manual_current_limit(self):
        if flask.request.method == 'PUT':
            limit = flask.request.args.get('limit')
            if limit is None:
                return flask.abort(400, "you must specify the mode")
            else:
                limit = float(limit)
                self.logger.info(f"setting new limit {limit}")
                if 0 <= limit <= 23:
                    self.manual_power_limit = limit * 1000
                    return flask.jsonify(limit=limit)
                else:
                    flask.abort(400, "the limit must be between 4 and 23 kW.")

        elif flask.request.method == "GET":
            return {"limit": int(self.manual_power_limit / 1000)}
        else:
            flask.abort(405)

    def handle_mode(self):
        if flask.request.method == 'PUT':
            mode = flask.request.args.get('mode')
            self.logger.info(f"setting new mode {mode}")
            if mode in ("manual", "automatic"):
                self.automatic_mode = mode == "automatic"
                return flask.jsonify(mode=mode)
            else:
                flask.abort(400, "you must specify the mode")

        elif flask.request.method == "GET":
            if self.automatic_mode:
                return {"mode": "automatic"}
            else:
                return {"mode": "manual"}
        else:
            flask.abort(405)

    def handle_meters(self, client=None):
        tesla_power_readings = self.get_tesla_power_reading()
        wallbox_power: float = self.get_wallbox_power(client)
        house = float(tesla_power_readings["load"]["instant_power"]) - wallbox_power
        return {"house": house,
                "wallbox": wallbox_power,
                "solar": float(tesla_power_readings["solar"]["instant_power"]),
                "grid": float(tesla_power_readings["site"]["instant_power"]),
                "battery": float(tesla_power_readings["battery"]["instant_power"])
                }

    def get_tesla_power_reading(self):
        logging.captureWarnings(True)
        resp = requests.get(f'{self.config["powerwall_host"]}/api/meters/aggregates', verify=False)
        logging.captureWarnings(False)
        return json.loads(resp.text)

    def get_wallbox_power(self, client) -> float:
        if client is None:
            client = flask.current_app.test_client()
        self.logger.info("Getting wallbox power")
        resp = client.get('/keba/power')
        return float(json.loads(resp.data)["power"])
