import numpy as np
import mss
from cv.regions import REGIONS
from config.settings import SCREEN_RESOLUTION


def capture_region(region: tuple) -> np.ndarray:
    x1, y1, x2, y2 = region
    with mss.mss() as sct:
        monitor = {"top": y1, "left": x1, "width": x2 - x1, "height": y2 - y1}
        screenshot = sct.grab(monitor)
        return np.array(screenshot)


def capture_all_enemy_regions() -> list[np.ndarray]:
    res_regions = REGIONS.get(SCREEN_RESOLUTION, REGIONS["1920x1080"])
    return [capture_region(r) for r in res_regions["enemy_names"]]


def capture_map_region() -> np.ndarray:
    res_regions = REGIONS.get(SCREEN_RESOLUTION, REGIONS["1920x1080"])
    return capture_region(res_regions["map_name"])
