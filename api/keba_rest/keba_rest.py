import logging

from keba_udp import KebaUDP

import flask


class KebaP30:
    def __init__(self, config: dict, vehicles: dict, logger: logging.Logger):
        self.udp = KebaUDP(config["host"], logger=logger.getChild("udp_interface"))
        self.logger = logger
        self.vehicles = {vehicle["rfid_token"]: vehicle for vehicle in vehicles}
        self.udp.connect()

    def attach_endpoints(self, app: flask.Flask):
        self.logger.info("Attached endpoints.")
        app.add_url_rule("/keba/power", "keba_power", self.power, methods=["PUT", "GET"])
        app.add_url_rule("/keba/session", "keba_session", self.session, methods=["GET"])
        app.add_url_rule("/keba/report", "keba_report", self.report, methods=["GET"])

    def report(self):
        report_id = flask.request.args.get('id', type=int)
        if report_id in (1, 2, 3) or report_id in range(100, 131):
            return self.udp.get_report(report_id)
        else:
            flask.abort(400, f"Requested report_id {report_id} neither in (1,2,3) nor in range(100, 131)")

    def power(self):
        if flask.request.method == 'PUT':
            current = flask.request.args.get('current')
            if current is None:
                flask.abort(400, "PUT requests must specify current value")
            delay = flask.request.args.get('delay')
            self.udp.set_currtime(current, delay)
            return {}
        elif flask.request.method == "GET":
            report3 = self.udp.get_report(3)
            report2 = self.udp.get_report(2)
            return {"power": report3["P"] / 1000, "current_limit": report2["Curr timer"]}

    def session(self):
        report = self.udp.get_report(100)
        vehicle = self.vehicles.get(report["RFID tag"], None)
        if vehicle is not None:
            report["vehicle name"] = vehicle["name"]
            report["vehicle alias"] = vehicle["alias"]
        else:
            report["vehicle name"] = "Unbekannt"
            report["vehicle alias"] = "Unbekannt"
        return report
