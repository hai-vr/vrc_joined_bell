import datetime
import glob
import io
import logging
import os
import psutil
import re
import sys
import time
import wave
import yaml

# disable pygame version log
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

import pygame


def tail(thefile):
    thefile.seek(0, 2)
    offset = thefile.tell()
    while True:
        try:
            line = thefile.readline()
            offset = thefile.tell()
            if not line:
                time.sleep(0.5)
                continue
            if line == "\n" or line == "\r\n":
                continue
            line = line.rstrip("\n")
            yield repr(line)[1:-1]
        except UnicodeDecodeError:
            thefile.seek(offset, 0)
            time.sleep(0.5)


def play(data_path, volume):
    with wave.open(data_path, "rb") as wave_file:
        frame_rate = wave_file.getframerate()
    pygame.mixer.init(frequency=frame_rate)
    player = pygame.mixer.Sound(data_path)
    player.set_volume(volume)
    player.play()


logger = logging.getLogger(__name__)
log_io = io.StringIO()


def process_kill_by_name(name):
    pid = os.getpid()
    for p in psutil.process_iter(attrs=["pid", "name"]):
        if p.info["name"] == name and p.pid != pid:
            p.terminate()


COLUMN_TIME = 0
COLUMN_EVENT_PATTERN = 1
COLUMN_SOUND = 2
COLUMN_MESSAGE = 3


def main():
    logger.setLevel(level=logging.INFO)
    std_handler = logging.StreamHandler(stream=sys.stdout)
    handler = logging.StreamHandler(stream=log_io)
    std_handler.setFormatter(logging.Formatter("%(message)s"))
    handler.setFormatter(logging.Formatter("%(message)s"))

    logger.addHandler(std_handler)
    logger.addHandler(handler)
    process_kill_by_name("vrc_joined_bell.exe")
    with open("notice.yml", "r") as conf:
        config = yaml.load(conf, Loader=yaml.SafeLoader)

    data = {}
    logger.info("events")
    for notice in config["notices"]:
        data[notice["event"]] = ["", re.compile(notice["event"]), notice["sound"]]
        logger.info("  " + notice["event"] + ": " + notice["sound"])
        if "message" in notice:
            data[notice["event"]].append(notice["message"])
            logger.info("        " + notice["message"])

    vrcdir = os.environ["USERPROFILE"] + "\\AppData\\LocalLow\\VRChat\\VRChat\\"
    logfiles = glob.glob(vrcdir + "output_log_*.txt")
    logfiles.sort(key=os.path.getctime, reverse=True)

    with open(logfiles[0], "r", encoding="utf-8") as f:
        logger.info("open logfile : " + logfiles[0])
        loglines = tail(f)

        timereg = re.compile(
            "([0-9]{4}\.[0-9]{2}\.[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}) .*"
        )

        for line in loglines:
            logtime = timereg.match(line)
            if not logtime:
                continue
            for pattern, item in data.items():
                match = item[COLUMN_EVENT_PATTERN].match(line)
                if match and logtime.group(1) != item[COLUMN_TIME]:
                    logger.info(line)
                    item[COLUMN_TIME] = logtime.group(1)
                    group = ""
                    if len(match.groups()) > 0:
                        group = match.group(1)

                    play_volume = 1.0

                    play(item[COLUMN_SOUND], play_volume)
                    break


if __name__ == "__main__":
    main()
