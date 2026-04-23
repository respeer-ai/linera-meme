class ApplicationRegistry:
    """Owns persistent application identity lookup and static bootstrap seeding."""

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
                    discovered_from='static_config',
                    metadata_json={
                        'source': 'app_config',
                        'host': getattr(config, 'swap_host', None),
                    },
                )
            )
        return seeded

    def resolve(self, application_id: str) -> dict | None:
        return self.repository.get_application(application_id)

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
        return self._register(
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

    def _register(self, **entry) -> dict:
        self.repository.upsert_application(entry)
        return entry
