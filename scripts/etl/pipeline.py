from etl.config import ETLConfig
from etl.models import SourceTechnology, TechnologySignal, TechnologyClassification


class RadarPipeline:
    def __init__(self, config: ETLConfig):
        self.config = config

    def run(self):
        pass