import json

import urllib3

from flask import Flask, send_from_directory, render_template

from .api.manager import Manager
from .api.connected_drive_cache import ConnectedDriveCache
from .api.audi_cache import AudiCache
from .api.keba_rest import KebaP30
from .api.billing import Billing
from .utils import init_logging, get_site_map, reboot_server, get_config

LOGGER = init_logging("flow_server")
LOGGER.info("Flow server is starting...")
urllib3.disable_warnings()
LOGGER.critical("Disabled urllib3 warnings!")


config = get_config()
LOGGER.info(json.dumps(config, indent=4))


app = Flask(__name__)

connected_drive_cache = ConnectedDriveCache(config["modules"]["connected_drive_cache"], config["vehicles"],
                                            init_logging("connected_drive_cache"))
manager = Manager(config["modules"]["manager"], app, init_logging("manager"))

keba_api = KebaP30(config["modules"]["keba_rest"], config["vehicles"], init_logging("keba_rest"))

audi_cache = AudiCache({}, config["vehicles"], init_logging("audi_cache"))

billing = Billing(config["modules"]["billing"], config["vehicles"], app, init_logging("billing"))

connected_drive_cache.attach_endpoints(app)
audi_cache.attach_endpoints(app)
keba_api.attach_endpoints(app)
manager.attach_endpoints(app)
billing.attach_endpoints(app)


@app.route('/sitemap')
def handle_sitemap():
    LOGGER.info("Generating sitemap.")
    return get_site_map(app)


@app.route('/dev/restart')
def handle_restart():
    LOGGER.info("Received reboot request.")
    reboot_server()
    return None


@app.route('/dynamic')
def handle_dynamic():
    LOGGER.info("Received dynamic request.")

    return render_template("index.html", vehicles=config["vehicles"])


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def handle_default(path):
    LOGGER.info(path)
    if path == "":
        LOGGER.info("sent default static file")
        return render_template("index.html", vehicles=config["vehicles"])
    else:
        return app.send_static_file(path)


