import datetime


class ChargeTarget:
    def __init__(self, weekday_target: float, weekend_target: float, default_target_hour: int,
                 max_power_watts: int, vehicle_max_soe_watthours: float):
        self.weekday_target: float = weekday_target
        self.weekend_target: float = weekend_target
        self.default_target_hour: int = default_target_hour
        self.max_charge_watts: int = max_power_watts
        self.vehicle_max_soe_watthours: float = vehicle_max_soe_watthours

        self.target: dict = self.get_next_target()

    def get_next_target(self) -> dict:
        target = dict()
        target_date = datetime.date.today()
        if datetime.datetime.now().hour > self.default_target_hour:
            # if we have already passed the target hour the next target will be tomorrow
            target_date = target_date + datetime.timedelta(days=1)

        target["time"] = datetime.datetime.combine(target_date, datetime.time(hour=self.default_target_hour))
        if target["time"].weekday() < 5:
            target["soe"] = self.weekday_target
        else:
            target["soe"] = self.weekend_target
        return target

    def compute_power(self, vehicle_soe_percent: float, meter_info: dict):
        self.target = self.get_next_target()
        soe_delta: float = self.target["soe"] - vehicle_soe_percent
        capacity_delta = soe_delta * self.vehicle_max_soe_watthours
        hours = (capacity_delta / self.max_charge_watts) + 1  # add one hour as a safety margin
        critical_time = self.target["time"] - datetime.timedelta(minutes=60) - datetime.timedelta(hours=hours)

        if datetime.datetime.now() > critical_time:
            return self.max_charge_watts
        else:
            return meter_info["solar"] - meter_info["house"]
