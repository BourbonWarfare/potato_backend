from dataclasses import dataclass

from bw.combined_dataclass import SlotCombiner


@dataclass(kw_only=True, slots=True)
class Permissions(SlotCombiner):
    can_upload_mission: bool
    can_test_mission: bool
