import copy
import datetime

import flask


class ChargeTarget:
    def __init__(self, logger):
        self.logger = logger
        self.default_target_soc = 60  # in percentage points
        self.default_target_time: int = 6

        self.target_time = None
        self.target_soc = copy.copy(self.default_target_soc)
        self.mode = "auto"
        self.update_target_time()

    def get_mode(self):
        return flask.jsonify(mode=self.mode)

    def get_critical_time(self, curr_capacity: float, max_capacity: float, max_power: float, safety_offset: int) \
            -> datetime.datetime:
        """
        compute and return the critical timestamp, after which we have to start charging at max_power to reach the
        target soc at least safety offset minutes before before the target time.
        :param curr_capacity: the current soc in kWh of the vehicle
        :param max_capacity: the capacity of the vehicle battery at 100% soc
        :param max_power: the maximum charging power in W
        :param safety_offset: the offset in minutes we would like to finish before the target time
        :return: a datetime object representing the critical time
        """
        target_capacity = self.target_soc / 100 * max_capacity
        capacity_delta = target_capacity - curr_capacity
        hours = capacity_delta / (max_power * 1000)
        return self.target_time - datetime.timedelta(minutes=safety_offset) - datetime.timedelta(hours=hours)

    def change_charge_target(self):
        if flask.request.method == 'PUT':
            return self.set_charge_target()
        elif flask.request.method == "GET":
            return flask.jsonify(time=int(self.target_time.timestamp()), soc=self.target_soc, mode=self.mode)

    def update_target_time(self):
        if self.mode == "auto":
            self.target_soc = self.default_target_soc
            target_date = datetime.date.today()
            if datetime.datetime.now().hour > self.default_target_time:
                target_date = target_date + datetime.timedelta(days=1)

            self.target_time = datetime.datetime.combine(target_date, datetime.time(hour=self.default_target_time))

        elif self.mode == "manual":
            # if we have passed a manually set target time we return to automatic mode
            if self.target_time < datetime.datetime.now():
                self.mode = "auto"
                self.update_target_time()

        else:
            raise ValueError(f"Invalid mode {self.mode} encountered")

    def set_charge_target(self):
        mode = flask.request.args.get('mode')
        if mode == "manual":
            target_time = flask.request.args.get('time')
            target_soc = flask.request.args.get('soc')

            if target_time is None or target_soc is None or not (0 < int(target_soc) <= 100):
                return 'You must specify time and 0 < soc <= 100 when setting manual mode', 400
            else:
                self.logger.info(f"Setting new target time with offset {int(target_time)}")
                self.target_time = datetime.datetime.now() + datetime.timedelta(hours=int(target_time))
                self.target_soc = int(target_soc)
                self.mode = mode
                return "switched to manual mode", 200
        elif mode == "auto":
            self.mode = mode
            self.update_target_time()

            return "switched to automatic mode", 200

        else:
            return 'You must specify a mode query (either manual or auto) when setting mode', 400

