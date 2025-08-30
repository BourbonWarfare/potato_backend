from dataclasses import dataclass

from bw.combined_dataclass import SlotCombiner


@dataclass(kw_only=True, slots=True)
class Roles(SlotCombiner):
    can_create_role: bool
    can_create_group: bool
    can_manage_server: bool
