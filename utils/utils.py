import json
import logging
import logging.handlers
import pathlib
import os


def init_logging(name, level=logging.INFO) -> logging.Logger:
    logdir = (get_root_dir() / "logs").resolve()
    logdir.mkdir(exist_ok=True, parents=False)
    fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(fmt)
    logging.basicConfig(format=fmt, level=logging.INFO)

    logger = logging.getLogger("flow." + name)
    logger.setLevel(level)
    fh = logging.handlers.RotatingFileHandler(str(logdir / f"{name}.log"), maxBytes=1000000, backupCount=5)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger


def get_root_dir() -> pathlib.Path:
    return pathlib.Path(__file__).parent.parent


def get_cache_dir() -> pathlib.Path:
    cache = get_root_dir() / "cache"
    cache.mkdir(exist_ok=True, parents=False)
    return cache


def get_site_map(app):
    overview = "<h1>Flow API overview</h1>"
    overview += "<table><tr><th>url</th><th>methods</th><th>description</th></tr>"
    interesting_methods = ["GET", "POST", "PUT"]
    for rule in app.url_map.iter_rules():
        methods = [m for m in rule.methods if m in interesting_methods]
        overview += f"<tr><td>{rule}</td><td>{','.join(methods)}</td><td>{rule.endpoint}</td></tr>"
    overview += "</table>"

    return overview


def reboot_server():
    os.system('sudo shutdown -r now')


def get_config():
    with open(str(get_root_dir() / "config.json"), "r") as fp:
        config = json.load(fp)
    return config
