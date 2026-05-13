import time


class ObservabilityStatus:
    COMPONENT_SCHEMA = 'schema'
    COMPONENT_REGISTRY = 'registry'
    COMPONENT_STARTUP_CATCH_UP = 'startup_catch_up'
    COMPONENT_LISTENER = 'listener'
    COMPONENT_DEBUG_EXPORT = 'debug_export'
    COMPONENT_DECODE_SCHEDULER = 'decode_scheduler'
    COMPONENT_NORMALIZER = 'normalizer'
    COMPONENT_MARKET_DERIVER = 'market_deriver'

    STATE_DISABLED = 'disabled'
    STATE_STOPPED = 'stopped'
    STATE_STARTING = 'starting'
    STATE_READY = 'ready'
    STATE_DEGRADED = 'degraded'

    def __init__(self, *, configured: bool):
        self.configured = configured
        self.state = self.STATE_STOPPED if configured else self.STATE_DISABLED
        self.last_error = None
        self.last_transition_at = time.time()
        self.runtime_components = (
            self.COMPONENT_SCHEMA,
            self.COMPONENT_REGISTRY,
            self.COMPONENT_STARTUP_CATCH_UP,
            self.COMPONENT_LISTENER,
            self.COMPONENT_DEBUG_EXPORT,
        )
        self.worker_components = (
            self.COMPONENT_DECODE_SCHEDULER,
            self.COMPONENT_NORMALIZER,
            self.COMPONENT_MARKET_DERIVER,
        )
        self.components = {
            self.COMPONENT_SCHEMA: self._build_component_status('idle'),
            self.COMPONENT_REGISTRY: self._build_component_status('idle'),
            self.COMPONENT_STARTUP_CATCH_UP: self._build_component_status('idle'),
            self.COMPONENT_LISTENER: self._build_component_status('idle'),
            self.COMPONENT_DEBUG_EXPORT: self._build_component_status('idle'),
            self.COMPONENT_DECODE_SCHEDULER: self._build_component_status('idle'),
            self.COMPONENT_NORMALIZER: self._build_component_status('idle'),
            self.COMPONENT_MARKET_DERIVER: self._build_component_status('idle'),
        }

    def is_ready(self) -> bool:
        return self.state == self.STATE_READY

    def mark_disabled(self, reason: str | None = None) -> None:
        self.configured = False
        self.state = self.STATE_DISABLED
        self.last_error = reason
        self.last_transition_at = time.time()
        self._reset_runtime_components('disabled')

    def mark_stopped(self) -> None:
        self.state = self.STATE_STOPPED if self.configured else self.STATE_DISABLED
        self.last_error = None
        self.last_transition_at = time.time()
        self._reset_runtime_components('idle')
        self._reset_worker_components()

    def mark_starting(self) -> None:
        self.state = self.STATE_STARTING
        self.last_error = None
        self.last_transition_at = time.time()

    def mark_ready(self) -> None:
        self.state = self.STATE_READY
        self.last_error = None
        self.last_transition_at = time.time()

    def mark_degraded(self, error: Exception | str) -> None:
        self.state = self.STATE_DEGRADED
        self.last_error = str(error)
        self.last_transition_at = time.time()

    def mark_component_ready(self, component: str) -> None:
        self.components[component] = self._build_component_status('ready')

    def mark_component_skipped(self, component: str, reason: str) -> None:
        self.components[component] = self._build_component_status('skipped', reason)

    def mark_component_degraded(self, component: str, error: Exception | str) -> None:
        self.components[component] = self._build_component_status('degraded', str(error))

    def snapshot(self) -> dict[str, object]:
        return {
            'configured': self.configured,
            'state': self.state,
            'ready': self.is_ready(),
            'last_error': self.last_error,
            'last_transition_at': self.last_transition_at,
            'components': dict(self.components),
            'component_groups': {
                'runtime': list(self.runtime_components),
                'workers': list(self.worker_components),
            },
        }

    def _reset_runtime_components(self, status: str) -> None:
        for component in self.runtime_components:
            self.components[component] = self._build_component_status(status)

    def _reset_worker_components(self) -> None:
        self.components[self.COMPONENT_DECODE_SCHEDULER] = self._build_component_status('idle')
        self.components[self.COMPONENT_NORMALIZER] = self._build_component_status('idle')
        self.components[self.COMPONENT_MARKET_DERIVER] = self._build_component_status('idle')

    def _build_component_status(self, status: str, error: str | None = None) -> dict[str, object]:
        return {
            'status': status,
            'last_error': error,
            'updated_at': time.time(),
        }
