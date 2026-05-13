class RealtimeDiagnosticRecorder:
    def __init__(self, db=None):
        self.db = db

    def record(self, **kwargs) -> None:
        if self.db is None:
            return None
        try:
            self.db.record_realtime_diagnostic(**kwargs)
        except Exception as exc:
            print(f'Realtime diagnostic write skipped: {exc}')
