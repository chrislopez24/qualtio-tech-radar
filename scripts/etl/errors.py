# TODO: These exceptions are defined but not yet used in the pipeline.
# They should replace bare Exception raises throughout the codebase.


class ETLError(Exception):
    pass


class SourceError(ETLError):
    pass


class ClassificationError(ETLError):
    pass


class PipelineError(ETLError):
    pass