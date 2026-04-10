from dataclasses import dataclass

from bw.combined_dataclass import SlotCombiner


@dataclass(kw_only=True, slots=True)
class Roles(SlotCombiner):
    can_create_role: bool = False
    can_create_group: bool = False
    can_manage_server: bool = False
    can_publish_realtime_events: bool = False
