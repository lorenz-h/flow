import json
import logging
import pathlib
import sys
import time
from typing import List, Dict, Optional

import flask
from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.country_selector import get_region_from_name
from bimmer_connected.vehicle import VehicleViewDirection, ConnectedDriveVehicle

from ...utils import get_cache_dir


class ConnectedDriveCache:
    def __init__(self, config, vehicles, logger):
        self.vehicles = [vehicle for vehicle in vehicles if vehicle["manufacturer"] == "bmw"]
        self.config = config
        self.logger = logger
        self.logger.info("BMW Connected Drive Cache started...")

        self.cache = get_cache_dir()

        self.max_staleness = self.config["max_staleness"]  # minutes

        credentials = self.config["credentials"]
        region = get_region_from_name(credentials["region"])
        self.account = ConnectedDriveAccount(credentials["user"], credentials["pwd"], region)
        self.vehicle_aliases: Dict[str, str] = {vehicle["vin"]: vehicle["alias"] for vehicle in self.vehicles}
        self.vehicle_update_timestamps: Dict[str, float] = {vehicle["vin"]: 0. for vehicle in self.vehicles}

    def get_last_update(self):
        vehicle = self.find_vehicle()
        return flask.jsonify(last_update=self.vehicle_update_timestamps[vehicle.vin])

    def attach_endpoints(self, app):
        app.add_url_rule("/bmw/last_update", "get_bmw_last_update", self.get_last_update)
        app.add_url_rule("/bmw/state", "get_bmw_state", self.get_full_state)
        app.add_url_rule("/bmw/thumbnail", "get_bmw_thumbnail", self.get_thumbnail)

    def find_vehicle(self) -> Optional[ConnectedDriveVehicle]:
        alias = flask.request.args.get('vehicle')
        if alias not in self.vehicle_aliases.values():
            self.logger.warning(f"Unknown vehicle requested: {alias}. "
                                f"Known aliases are {self.vehicle_aliases.values()}")
            flask.abort(404, description=f"Unknown Vehicle {alias}")
            return None

        for vehicle in self.account.vehicles:
            if vehicle.vin in self.vehicle_aliases.keys() and self.vehicle_aliases[vehicle.vin] == alias:
                return vehicle

        flask.abort(501, description=f"Unable to find vehicle in your account with VIN corresponding to alias {alias}. "
                                     f"Check the config of the ConnectedDriveCache.")
        return None

    def get_full_state(self):
        vehicle = self.find_vehicle()
        allow_cache_query: str = flask.request.args.get('allow_cache')
        allow_cache: bool = allow_cache_query is None or allow_cache_query == "true"
        self.check_staleness(vehicle, allow_cache)
        return flask.jsonify(**vehicle.state.attributes)

    def check_staleness(self, vehicle, allow_cache: bool = True):
        if time.time() - self.vehicle_update_timestamps[vehicle.vin] > self.max_staleness or not allow_cache:
            self.logger.info(f"Fetching fresh data from {self.account.server_url}...")
            vehicle.update_state()
            self.vehicle_update_timestamps[vehicle.vin] = time.time()
        else:
            self.logger.info(f"Serving cached data with timestamp {self.vehicle_update_timestamps[vehicle.vin]}")

    def get_thumbnail(self):
        if not self.cache.exists():
            self.cache.mkdir(exist_ok=True)

        vehicle = self.find_vehicle()
        fpath = self.cache / f"{self.vehicle_aliases[vehicle.vin]}.png"
        if not fpath.is_file():
            img_bytes = vehicle.get_vehicle_image(600, 600, VehicleViewDirection.FRONTSIDE)
            with open(fpath, "wb") as fp:
                fp.write(img_bytes)

        return flask.send_file(fpath, mimetype='image/png')
