class ApplicationRegistry:
    """Owns persistent application identity lookup and static bootstrap seeding."""

    SOURCE_STATIC_CONFIG = 'static_config'
    SOURCE_SWAP_SERVICE = 'swap_service'
    SOURCE_PROXY_SERVICE = 'proxy_service'
    SOURCE_CHAIN_EVENT = 'chain_event'
    SOURCE_MANUAL = 'manual'

    STATUS_ACTIVE = 'active'
    STATUS_UNKNOWN = 'unknown'
    STATUS_DEPRECATED = 'deprecated'

    def __init__(self, repository):
        self.repository = repository

    def seed_from_config(self, config) -> list[dict]:
        seeded = []
        if getattr(config, 'swap_application_id', None):
            seeded.append(
                self._register(
                    application_id=str(config.swap_application_id),
                    app_type='swap',
                    chain_id=getattr(config, 'swap_chain_id', None),
                    creator_chain_id=getattr(config, 'swap_chain_id', None),
                    discovered_from=self.SOURCE_STATIC_CONFIG,
                    metadata_json={
                        'source': 'app_config',
                        'host': getattr(config, 'swap_host', None),
                    },
                )
            )
        if getattr(config, 'proxy_application_id', None):
            seeded.append(
                self._register(
                    application_id=str(config.proxy_application_id),
                    app_type='proxy',
                    chain_id=getattr(config, 'proxy_chain_id', None),
                    creator_chain_id=getattr(config, 'proxy_chain_id', None),
                    discovered_from=self.SOURCE_STATIC_CONFIG,
                    metadata_json={
                        'source': 'app_config',
                        'host': getattr(config, 'proxy_host', None),
                    },
                )
            )
        return seeded

    def resolve(self, application_id: str) -> dict | None:
        return self.repository.get_application(
            self._normalize_application_id(application_id)
        )

    def list_known_applications(
        self,
        *,
        app_type: str | None = None,
        limit: int = 200,
    ) -> list[dict]:
        return self.repository.list_applications(app_type=app_type, limit=limit)

    def register_known_application(
        self,
        *,
        application_id: str,
        app_type: str,
        chain_id: str | None = None,
        creator_chain_id: str | None = None,
        owner: str | None = None,
        parent_application_id: str | None = None,
        abi_version: str | None = None,
        discovered_from: str = 'manual',
        status: str = 'active',
        metadata_json: dict | None = None,
    ) -> dict:
        return self.discover_application(
            application_id=application_id,
            app_type=app_type,
            chain_id=chain_id,
            creator_chain_id=creator_chain_id,
            owner=owner,
            parent_application_id=parent_application_id,
            abi_version=abi_version,
            discovered_from=discovered_from,
            status=status,
            metadata_json=metadata_json,
        )

    def discover_application(
        self,
        *,
        application_id: str,
        app_type: str,
        chain_id: str | None = None,
        creator_chain_id: str | None = None,
        owner: str | None = None,
        parent_application_id: str | None = None,
        abi_version: str | None = None,
        discovered_from: str,
        status: str = STATUS_ACTIVE,
        metadata_json: dict | None = None,
    ) -> dict:
        self._validate_application_id(application_id)
        self._validate_app_type(app_type)
        self._validate_discovered_from(discovered_from)
        self._validate_status(status)
        return self._register(
            application_id=self._normalize_application_id(application_id),
            app_type=str(app_type),
            chain_id=chain_id,
            creator_chain_id=creator_chain_id,
            owner=owner,
            parent_application_id=parent_application_id,
            abi_version=abi_version,
            discovered_from=discovered_from,
            status=status,
            metadata_json=metadata_json,
        )

    def _register(self, **entry) -> dict:
        self.repository.upsert_application(entry)
        return entry

    def _validate_application_id(self, application_id: str) -> None:
        if not str(application_id).strip():
            raise ValueError('application_id must be non-empty')

    def _normalize_application_id(self, application_id: str) -> str:
        value = str(application_id).strip()
        if value.startswith('0x') or value.startswith('0X'):
            trimmed = value[2:]
            if trimmed:
                return trimmed
        return value

    def _validate_app_type(self, app_type: str) -> None:
        if not str(app_type).strip():
            raise ValueError('app_type must be non-empty')

    def _validate_discovered_from(self, discovered_from: str) -> None:
        allowed = {
            self.SOURCE_STATIC_CONFIG,
            self.SOURCE_SWAP_SERVICE,
            self.SOURCE_PROXY_SERVICE,
            self.SOURCE_CHAIN_EVENT,
            self.SOURCE_MANUAL,
        }
        if discovered_from not in allowed:
            raise ValueError(f'unsupported discovered_from: {discovered_from}')

    def _validate_status(self, status: str) -> None:
        allowed = {
            self.STATUS_ACTIVE,
            self.STATUS_UNKNOWN,
            self.STATUS_DEPRECATED,
        }
        if status not in allowed:
            raise ValueError(f'unsupported status: {status}')
