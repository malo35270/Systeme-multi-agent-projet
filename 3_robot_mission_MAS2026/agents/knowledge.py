from typing import Any


class RobotKnowledge:
    def __init__(self):
        self.timestep = 0
        self.position = None
        self.last_action = None
        self.map: dict[tuple[int, int], dict[str, Any]] = {}

    def as_dict(self) -> dict[str, Any]:
        return {
            "timestep": self.timestep,
            "position": self.position,
            "last_action": self.last_action,
            "map": self.map,
        }

    def update_from_percepts(self, percepts, action, position):
        self.timestep += 1
        self.position = position
        self.last_action = action
        current_time = self.timestep

        for pos, info in percepts.items():
            old_info = self.map.get(pos)
            new_info = {
                "zone": info["zone"],
                "wastes": list(info["wastes"]),
                "disposal": info["disposal"],
                "timestamp": current_time,
            }
            if old_info is None or old_info.get("timestamp", -1) <= current_time:
                self.map[pos] = new_info

    def merge_shared_map(self, other_map):
        for pos, info in other_map.items():
            other_ts = info.get("timestamp", -1)
            my_info = self.map.get(pos)
            my_ts = my_info.get("timestamp", -1) if my_info else -1

            if my_info is None or other_ts > my_ts:
                self.map[pos] = {
                    "zone": info["zone"],
                    "wastes": list(info["wastes"]),
                    "disposal": info["disposal"],
                    "timestamp": other_ts,
                }
