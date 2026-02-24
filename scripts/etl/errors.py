class ETLError(Exception):
    pass


class SourceError(ETLError):
    pass


class ClassificationError(ETLError):
    pass


class PipelineError(ETLError):
    pass