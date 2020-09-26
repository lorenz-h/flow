import json

import flask
from audiapi.API import API
from audiapi.Services import LogonService, CarService


class AudiCache:

    def __init__(self, config, vehicles, logger):
        self.config = config
        self.vehicles = [vehicle for vehicle in vehicles if vehicle["manufacturer"]=="audi"]
        self.logger = logger

    def find_vehicle(self):
        alias = flask.request.args.get('vehicle')
        for vehicle in self.vehicles:
            if vehicle["alias"] == alias:
                return vehicle

        return None

    def get_thumbnail(self):
        vehicle = self.find_vehicle()
        if vehicle is not None:
            return flask.send_file("api/audi_cache/etron.png", mimetype='image/png')
        else:
            return flask.abort(501, description=f"Unknown Vehicle Alias")

    def attach_endpoints(self, app):
        app.add_url_rule("/audi/thumbnail", "get_audi_thumbnail", self.get_thumbnail)


