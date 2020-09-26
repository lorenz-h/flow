import calendar
import datetime
import json
import logging
import threading
import time
from typing import List, Generator

import flask
import jinja2

from ...utils import get_cache_dir


class Billing:
    def __init__(self, config: dict, vehicles: dict, app: flask.Flask, logger: logging.Logger):
        self.logger = logger
        self.vehicles = vehicles

        self.sessions_cache = get_cache_dir() / "sessions"
        self.sessions_cache.mkdir(exist_ok=True, parents=True)

        self.daemon = threading.Thread(target=self.background_update, args=(app,), name="charge_manager_daemon",
                                       daemon=True)
        self.daemon.start()

    def background_update(self, app):
        client = app.test_client()
        try:
            while True:
                self.update_charging_session_cache(client)
                time.sleep(60 * 20)
        except:
            self.logger.exception("exception occurred!")
            self.background_update(app)

    def update_charging_session_cache(self, client):
        for idx in range(101, 131):
            raw_report = client.get(f"/keba/report?id={idx}").data
            report = json.loads(raw_report)
            if report["Session ID"] == -1:
                break
            fpath = self.sessions_cache / f"session_{report['Session ID']}.json"
            if fpath.exists():
                break
            with open(fpath, "wb") as fp:
                fp.write(raw_report)

    def attach_endpoints(self, app: flask.Flask):
        app.add_url_rule("/billing/downloads", "billing_download", self.create_bill, methods=["GET"])

    def filter_sessions(self, year: int = None, month: int = None, rfid_tag: str = None):
        max_idx = 0
        for session in self.sessions_cache.iterdir():
            idx = int(session.stem.split("_")[1])
            if max_idx < idx:
                max_idx = idx
        for idx in range(max_idx, 0, -1):
            fpath = self.sessions_cache / f"session_{idx}.json"
            with open(fpath, "r") as fp:
                session_info = json.load(fp)

            session_started = datetime.datetime.fromtimestamp(int(session_info["started[s]"]))

            if (year is None or session_started.year == year) and (
                    month is None or session_started.month == month) and (
                    rfid_tag is None or session_info["RFID tag"] == rfid_tag) and (session_info["E pres"] != 0):
                yield session_info

            if (session_started - datetime.datetime(year=year, month=month, day=1)).total_seconds() < 0:
                # since the sessions are sorted new to old we can exit the loop once we have
                # found a session which started before the month, year that we are looking for
                break

    def create_billing_information(self, raw_sessions: Generator[dict, None, None], euros_per_kWh: float):
        total_Wh = 0
        total_cost = 0
        sessions = list()
        datetime_format = "%d.%m.%Y %H:%M"
        for s in raw_sessions:
            energy = s["E pres"] * 0.1
            cost = energy / 1000 * euros_per_kWh
            total_cost += cost
            total_Wh += energy

            session_started = datetime.datetime.fromtimestamp(int(s["started[s]"]))
            session_ended = datetime.datetime.fromtimestamp(
                int(s["ended[s]"]))

            session = {
                "uid": s['Session ID'],
                "started": session_started.strftime(datetime_format),
                "ended": session_ended.strftime(datetime_format),
                "energy": round(energy / 1000, 2),
                "cost": round(cost, 2)
            }
            sessions.append(session)

        total_Wh = round(total_Wh, 3)
        total_cost = round(total_cost, 2)
        return sessions, total_Wh, total_cost

    def render_bill(self, year, month, sessions, netto_euros_per_kWh: float,
                    brutto_euros_per_kWh: float, total_cost: float, total_Wh: float, rfid_tag: str):

        date_format = "%d.%m.%Y"
        start_day = datetime.date(year=year, month=month, day=1).strftime(date_format)
        end_day = datetime.date(year=year, month=month, day=calendar.monthrange(year, month)[1]).strftime(date_format)

        return flask.render_template("bill.html", sessions=sessions, netto_euros_per_kWh=netto_euros_per_kWh,
                                     brutto_euros_per_kWh=brutto_euros_per_kWh, total_cost=total_cost,
                                     total_kWh=round(total_Wh / 1000, 2), start_day=start_day, end_day=end_day,
                                     rfid_tag=rfid_tag)

    def create_bill(self):
        year = int(flask.request.args.get('year', int))
        month = int(flask.request.args.get('month', int))
        rfid_tag = flask.request.args.get('rfid', str)
        netto_euros_per_kWh = float(flask.request.args.get('euros_per_kWh', float))
        brutto_euros_per_kWh = 1.16 * netto_euros_per_kWh

        self.logger.info(f"Creating bill for year {year} month {month} rfid tag {rfid_tag} for cost {netto_euros_per_kWh}")
        raw_sessions = self.filter_sessions(year, month, rfid_tag)

        sessions, total_Wh, total_cost = self.create_billing_information(raw_sessions, brutto_euros_per_kWh)
        return self.render_bill(year, month, sessions, netto_euros_per_kWh, brutto_euros_per_kWh, total_cost, total_Wh, rfid_tag)
