from abc import ABC
from typing import Optional, cast

from communication.agent.CommunicatingAgent import CommunicatingAgent

from .policy import build_behavior
from .knowledge import RobotKnowledge


class Robot(CommunicatingAgent, ABC):
    _name_counter = 0

    def __init__(
        self,
        model,
        color,
        allowed_waste_types,
        home_zone,
        deposit_zone,
        can_deposit,
        split_result,
        max_carry,
        version: Optional[str] = "v0.0.1",
    ):
        agent_name = f"{color}_robot_{Robot._name_counter}"
        Robot._name_counter += 1

        super().__init__(model, agent_name)
        self.carrying = []
        self.knowledge = RobotKnowledge()
        self.color = color
        self.allowed_waste_types = allowed_waste_types
        self.home_zone = home_zone
        self.max_zone = home_zone
        self.deposit_zone = deposit_zone
        self.can_deposit = can_deposit
        self.split_result = split_result
        self.max_carry = max_carry
        self.behavior = build_behavior(version or "v0.0.1")

    def deliberate(self) -> dict | None:
        return self.behavior.deliberate(self)

    def _current_pos(self):
        return cast(tuple[int, int], self.pos)

    def step_agent(self):
        current_pos = self._current_pos()
        percepts = self.model.get_local_percepts(current_pos)
        self.knowledge.update_from_percepts(percepts, None, current_pos)
        self.behavior.communication.process_messages(self)

        action = self.deliberate()
        new_percepts = self.model.do(self, action)
        self.knowledge.update_from_percepts(new_percepts, action, self._current_pos())

        if action and action.get("name") == "deposit" and hasattr(self.behavior.communication, "on_deposit"):
            self.behavior.communication.on_deposit(self, new_percepts)

        for pos, info in new_percepts.items():
            self.knowledge.map[pos]["wastes"] = info["wastes"]

    def step(self):
        self.step_agent()

    @property
    def knowledge_dict(self):
        return self.knowledge.as_dict()

    def known_allowed_wastes(self):
        return [
            pos
            for pos, info in self.knowledge.map.items()
            if self.model.can_enter(self, pos)
            and any(w in self.allowed_waste_types for w in info["wastes"])
        ]

    def closest_allowed_waste(self):
        current_pos = self._current_pos()
        return min(
            self.known_allowed_wastes(),
            key=lambda pos: self.manhattan_distance(pos, current_pos),
            default=None,
        )

    def manhattan_distance(self, pos1, pos2):
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def closest_known_deposit_cell(self):
        current_pos = self._current_pos()
        if self.deposit_zone == 1:
            candidates = [pos for pos, info in self.knowledge.map.items() if info.get("disposal")]
        else:
            candidates = [
                pos
                for pos, info in self.knowledge.map.items()
                if info.get("zone") == self.deposit_zone
            ]
        if not candidates:
            return None
        return min(candidates, key=lambda pos: self.manhattan_distance(pos, current_pos))


class greenAgent(Robot):
    def __init__(self, model, version: Optional[str] = "v0.0.1"):
        super().__init__(model, "green", ["green"], 1, 1, True, False, 2, version=version)


class yellowAgent(Robot):
    def __init__(self, model, version: Optional[str] = "v0.0.1"):
        super().__init__(model, "yellow", ["yellow"], 2, 1, False, "green", 2, version=version)


class redAgent(Robot):
    def __init__(self, model, version: Optional[str] = "v0.0.1"):
        super().__init__(model, "red", ["red"], 3, 2, False, "yellow", 2, version=version)
