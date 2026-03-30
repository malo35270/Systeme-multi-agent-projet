from communication.message.Message import Message
from communication.message.MessagePerformative import MessagePerformative


class NoKnowledgeSharing:
    def share(self, robot):
        return None

    def process_messages(self, robot):
        return None


class LocalKnowledgeSharing:
    """Original local sharing: neighbors exchange their full known maps."""

    def share(self, robot):
        current_pos = robot._current_pos()
        neighbors = robot.model.grid.get_neighbors(
            current_pos, moore=False, include_center=True, radius=1
        )
        for other in neighbors:
            if other is robot or not hasattr(other, "knowledge"):
                continue
            robot.knowledge.merge_shared_map(other.knowledge.map)

    def process_messages(self, robot):
        return None


class SmartColorKnowledgeSharing:
    """Smart local communication between nearby robots using message passing."""

    def share(self, robot):
        current_pos = robot._current_pos()
        neighbors = robot.model.grid.get_neighbors(
            current_pos, moore=False, include_center=True, radius=1
        )
        for other in neighbors:
            if other is robot or not hasattr(other, "color") or not hasattr(other, "get_name"):
                continue
            self._send_relevant_knowledge(robot, other)

    def process_messages(self, robot):
        for message in robot.get_new_messages():
            if message.get_performative() != MessagePerformative.INFORM_REF:
                continue

            content = message.get_content()
            if not isinstance(content, dict):
                continue

            if content.get("type") not in {"knowledge_share", "deposit_update"}:
                continue

            shared_map = content.get("map", {})
            if isinstance(shared_map, dict):
                robot.knowledge.merge_shared_map(shared_map)

    def on_deposit(self, robot, updated_percepts):
        if not updated_percepts:
            return

        current_pos = robot._current_pos()
        neighbors = robot.model.grid.get_neighbors(
            current_pos, moore=False, include_center=True, radius=1
        )

        for other in neighbors:
            if other is robot or not hasattr(other, "color") or not hasattr(other, "get_name"):
                continue
            self._send_deposit_update(robot, other, updated_percepts)

    def _send_relevant_knowledge(self, sender, receiver):
        shared_map = {}
        for pos, info in sender.knowledge.map.items():
            wastes = info.get("wastes", [])
            filtered_wastes = [w for w in wastes if w == receiver.color]

            if info.get("disposal") or filtered_wastes:
                shared_map[pos] = {
                    "zone": info["zone"],
                    "wastes": filtered_wastes,
                    "disposal": info["disposal"],
                    "timestamp": info.get("timestamp", -1),
                }

        if not shared_map:
            return

        sender.send_message(
            Message(
                sender.get_name(),
                receiver.get_name(),
                MessagePerformative.INFORM_REF,
                {"type": "knowledge_share", "map": shared_map},
            )
        )

    def _send_deposit_update(self, sender, receiver, updated_percepts):
        shared_map = {}
        for pos, info in updated_percepts.items():
            filtered_wastes = [w for w in info.get("wastes", []) if w == receiver.color]
            if info.get("disposal") or filtered_wastes:
                shared_map[pos] = {
                    "zone": info["zone"],
                    "wastes": filtered_wastes,
                    "disposal": info["disposal"],
                    "timestamp": sender.knowledge.timestep,
                }

        if not shared_map:
            return

        sender.send_message(
            Message(
                sender.get_name(),
                receiver.get_name(),
                MessagePerformative.INFORM_REF,
                {"type": "deposit_update", "map": shared_map},
            )
        )
