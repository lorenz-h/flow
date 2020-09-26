import copy
import datetime
import json
import logging
import threading
import time
import urllib3

import flask
import requests

from .utils import MovingAverageFilter
from .charge_target import ChargeTarget


class ChargeManager:
    def __init__(self, config, vehicles, logger: logging.Logger):
        self.vehicles = vehicles
        self.config = config
        assert self.config["wallbox_update_interval"] >= self.config["power_read_interval"]

        self.logger: logging.Logger = logger
        self.target = ChargeTarget(self.logger.getChild("target"))

        self.meter_information = None

        self.wallbox_target_power = 0.  # Watts
        self.wallbox_actual_power = 0.  # Watts
        self.avg_filter = MovingAverageFilter()

        self.daemon = threading.Thread(target=self.background_update, args=(), name="charge_manager_daemon")
        self.daemon.start()

    def attach_endpoints(self, app: flask.Flask):
        self.logger.info("Attached endpoints.")
        app.add_url_rule("/charge_manager/target", "charge_manager_set_charge_target",
                         self.target.change_charge_target, methods=["PUT", "GET"])

        app.add_url_rule("/charge_manager/mode", "charge_manager_get_current_mode",
                         self.target.get_mode, methods=["GET"])

        app.add_url_rule("/charge_manager/meters/consumption", "charge_manager_get_consumption",
                         self.get_consumption, methods=["GET"])

    def get_consumption(self):
        # ("powerwall", "grid", "solar", "house", "wallbox"):
        meter_name = flask.request.args.get('meter')
        if self.meter_information is not None:
            if meter_name == "powerwall":
                return flask.jsonify(load=float(self.meter_information["battery"]["instant_power"]))
            elif meter_name == "grid":
                return flask.jsonify(load=float(self.meter_information["site"]["instant_power"]))
            elif meter_name == "solar":
                return flask.jsonify(load=float(self.meter_information["solar"]["instant_power"]))
            elif meter_name == "house":
                load = float(self.meter_information["load"]["instant_power"]) - self.wallbox_actual_power
                return flask.jsonify(load=load)
            elif meter_name == "wallbox":
                return flask.jsonify(load=self.wallbox_actual_power)
            else:
                return flask.abort(400, description=f"Unknown meter {meter_name}")

        else:
            return flask.jsonify(load=0.0)

    def background_update(self):
        while True:
            self.target.update_target_time()
            last_update = time.time()
            while time.time() - last_update < self.config["wallbox_update_interval"]:
                load_power, solar_power = self.get_power_readings()
                time.sleep(self.config["power_read_interval"])

            self.update_wallbox_target_power()
            self.send_wallbox_target()

    def ensure_target_completion(self):
        self.logger.info("Querying current vehicle soc from Flow API")
        resp = requests.get(f'http://127.0.0.1:80/bmw/state?vehicle={self.config["vehicle_alias"]}', verify=False)
        if resp.ok:
            percent_soc = json.loads(resp.text)["chargingLevelHv"]

            if float(percent_soc) < float(self.target.target_soc):
                # we have not yet reached the charging goal
                current_soc = self.config["vehicle_capacity"] * percent_soc / 100
                critical_time = self.target.get_critical_time(current_soc, self.config["vehicle_capacity"],
                                                              self.config["max_charging_power"],
                                                              self.config["safety_offset"])
                self.logger.info(f"computed critical time {critical_time}")

                if critical_time < datetime.datetime.now():
                    self.logger.info(f"Overwriting max charging power to maximum {self.config['max_charging_power']} "
                                     f"to ensure target completion")
                    self.wallbox_target_power = self.config["max_charging_power"]
                else:
                    self.logger.info(f"Critical time {critical_time} was not yet reached for target time "
                                     f"{self.target.target_time}")
            else:
                self.wallbox_target_power = 0
                self.logger.info(f"Set charging power to 0 because goal of {self.target.target_soc} % was reached."
                                 f"Current vehicle soc {percent_soc} %")

        else:
            raise requests.RequestException(resp)

    def update_wallbox_target_power(self):
        excess = self.avg_filter["solar_power"] - self.avg_filter["load_power"]

        if self.wallbox_target_power > 0 or excess > self.config["required_minimum_excess"]:
            # adjust the target power according to the excess, if we are already charging (target power > 0).
            # Only start charging if the excess is larger than the required_minimum_excess.
            self.wallbox_target_power += excess

        if self.wallbox_target_power < self.config["minimum_power"]:
            # if we currently have less than the minimum charging power available, stop charging altogether
            self.wallbox_target_power = 0

        if self.wallbox_target_power < 0:
            # we can only have positive target powers.
            self.wallbox_target_power = 0
        self.logger.info(f"New power bound wallbox target {self.wallbox_target_power} after error {excess}")

        self.ensure_target_completion()

    def send_wallbox_target(self):
        pass

    def get_power_readings(self):
        logging.captureWarnings(True)
        resp = requests.get(f'{self.config["powerwall_host"]}/api/meters/aggregates', verify=False)
        logging.captureWarnings(False)
        meters = json.loads(resp.text)

        self.meter_information = meters

        load_power = self.avg_filter("load_power", float(meters["load"]["instant_power"]), self.config["power_smoothing_window"])
        solar_power = self.avg_filter("solar_power", float(meters["solar"]["instant_power"]), self.config["power_smoothing_window"])
        self.logger.debug(f"Got Power Reading: Load {load_power} Solar {solar_power}")
        return load_power, solar_power


if __name__ == '__main__':
    urllib3.disable_warnings()
    logging.basicConfig(level=logging.INFO)
    cm = ChargeManager({
        "wallbox_update_interval": 5,
        "power_read_interval": 1,
        "power_smoothing_window": 5,
        "vehicle_capacity": 29.5,
        "max_charging_power": 5.5,
        "safety_offset": 120,
        "required_minimum_excess": 1000,
        "minimum_power": 500,
        "vehicle_alias": "i32020"
    }, logging.getLogger())
    readings = cm.get_power_readings()






