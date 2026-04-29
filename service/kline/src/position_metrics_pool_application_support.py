class PositionMetricsPoolApplicationSupport:
    def __init__(
        self,
        *,
        running_in_k8s,
    ):
        self.running_in_k8s = running_in_k8s

    def parse_account(self, account: str) -> dict:
        chain_id, owner = account.split(':', 1)
        return {
            'chain_id': chain_id,
            'owner': owner,
        }

    def pool_application_url(
        self,
        base_url: str,
        pool_application: str,
        *,
        in_k8s: bool | None = None,
    ) -> str:
        chain_id, application_id = pool_application.split(':', 1)
        prefix = '' if (self.running_in_k8s() if in_k8s is None else in_k8s) else '/query'
        short_application_id = application_id[2:] if application_id.startswith('0x') else application_id
        return f'{base_url}{prefix}/chains/{chain_id}/applications/{short_application_id}'

    def build_position_metrics_query(self, owner: dict) -> dict:
        return {
            'query': '''
                query PositionMetrics($owner: Account!) {
                  pool
                  totalSupply
                  virtualInitialLiquidity
                  liquidity(owner: $owner) {
                    liquidity
                    amount0
                    amount1
                  }
                  latestTransactions(startId: 0)
                }
            ''',
            'variables': {
                'owner': owner,
            },
        }

    def build_position_metrics_legacy_query(self, owner: dict) -> dict:
        return {
            'query': '''
                query PositionMetricsLegacy($owner: Account!) {
                  pool
                  virtualInitialLiquidity
                  liquidity(owner: $owner) {
                    liquidity
                    amount0
                    amount1
                  }
                  latestTransactions(startId: 0)
                }
            ''',
            'variables': {
                'owner': owner,
            },
        }

    def graphql_unknown_field(self, payload: dict, field_name: str) -> bool:
        for error in payload.get('errors') or []:
            message = str(error.get('message') or '')
            if f'Unknown field "{field_name}"' in message:
                return True
        return False
