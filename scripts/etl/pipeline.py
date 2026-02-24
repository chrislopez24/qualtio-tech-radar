from pathlib import Path
from typing import Optional, List

from etl.config import ETLConfig
from etl.checkpoint import CheckpointStore
from etl.models import SourceTechnology, TechnologySignal, TechnologyClassification


PHASES = ["collect", "classify", "filter", "output"]


class RadarPipeline:
    def __init__(
        self,
        config: Optional[ETLConfig] = None,
        checkpoint_path: Optional[str] = None,
        save_interval: int = 100,
        resume: bool = False,
    ):
        self.config = config if config is not None else ETLConfig()
        self.checkpoint_path = checkpoint_path
        self.save_interval = save_interval
        self.resume = resume

        self.checkpoint: Optional[CheckpointStore] = None
        if checkpoint_path:
            self.checkpoint = CheckpointStore(Path(checkpoint_path))

        self._phase_items_processed = 0

    def run(self):
        start_phase_idx = 0

        if self.resume and self.checkpoint:
            checkpoint_data = self.checkpoint.load()
            if checkpoint_data and "phase" in checkpoint_data:
                start_phase_idx = PHASES.index(checkpoint_data["phase"])
                self._phase_items_processed = checkpoint_data.get("cursor", 0)

        for phase_idx in range(start_phase_idx, len(PHASES)):
            phase = PHASES[phase_idx]
            self._run_phase(phase)

            if self.checkpoint and phase_idx < len(PHASES) - 1:
                next_phase = PHASES[phase_idx + 1]
                self.checkpoint.save({"phase": next_phase, "cursor": 0})

    def _run_phase(self, phase: str):
        if phase == "collect":
            self._phase_collect()
        elif phase == "classify":
            self._phase_classify()
        elif phase == "filter":
            self._phase_filter()
        elif phase == "output":
            self._phase_output()

    def _phase_collect(self):
        pass

    def _phase_classify(self):
        pass

    def _phase_filter(self):
        pass

    def _phase_output(self):
        pass

    def _save_checkpoint(self, phase: str, cursor: int):
        if self.checkpoint and self.save_interval > 0:
            if self._phase_items_processed > 0 and self._phase_items_processed % self.save_interval == 0:
                self.checkpoint.save({"phase": phase, "cursor": cursor})

    def _update_progress(self, items_processed: int = 1):
        self._phase_items_processed += items_processed