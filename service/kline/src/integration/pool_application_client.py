from position_metrics_pool_application_support import PositionMetricsPoolApplicationSupport


class PoolApplicationClient:
    def __init__(
        self,
        *,
        base_url: str,
        post,
        in_k8s: bool,
    ):
        self.base_url = base_url
        self.post = post
        self.in_k8s = in_k8s
        self.support = PositionMetricsPoolApplicationSupport(
            running_in_k8s=lambda: self.in_k8s,
        )

    async def get_position_metrics_payload(
        self,
        *,
        pool_application: str,
        owner: dict,
    ) -> dict:
        url = self.support.pool_application_url(
            self.base_url,
            pool_application,
            in_k8s=self.in_k8s,
        )
        payload = await self._post_position_metrics_query(
            url=url,
            query=self.support.build_position_metrics_query(owner),
        )
        if 'errors' not in payload:
            return payload
        if not self.support.graphql_unknown_field(payload, 'totalSupply'):
            raise RuntimeError(str(payload['errors']))
        legacy_payload = await self._post_position_metrics_query(
            url=url,
            query=self.support.build_position_metrics_legacy_query(owner),
        )
        if 'errors' in legacy_payload:
            raise RuntimeError(str(legacy_payload['errors']))
        return legacy_payload

    async def _post_position_metrics_query(
        self,
        *,
        url: str,
        query: dict,
    ) -> dict:
        response = await self.post(
            url=url,
            json=query,
            timeout=(3, 10),
        )
        response.raise_for_status()
        return response.json()
