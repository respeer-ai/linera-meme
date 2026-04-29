from normalizer.normalized_event_result import NormalizedEventResult


class ApplicationEventFamilyResolver:
    def resolve(self, item: dict) -> str:
        decode_status = item['decode_result']['status']
        if decode_status == 'unresolved_application':
            return NormalizedEventResult.FAMILY_DECODE_UNRESOLVED
        if decode_status == 'unimplemented_decoder':
            return NormalizedEventResult.FAMILY_DECODE_UNIMPLEMENTED
        if decode_status == 'decode_failed':
            return NormalizedEventResult.FAMILY_DECODE_FAILED
        app_type = item['decode_result'].get('app_type')
        if app_type == 'pool':
            family = self._resolve_pool_family(item)
            if family is not None:
                return family
        if app_type == 'swap':
            family = self._resolve_swap_family(item)
            if family is not None:
                return family
        if app_type == 'meme':
            family = self._resolve_meme_family(item)
            if family is not None:
                return family
        if self._is_rejected(item):
            return {
                'operation': NormalizedEventResult.FAMILY_APPLICATION_OPERATION_REJECTED,
                'message': NormalizedEventResult.FAMILY_APPLICATION_MESSAGE_REJECTED,
                'event': NormalizedEventResult.FAMILY_APPLICATION_EVENT_REJECTED,
            }[item['payload_kind']]
        return {
            'operation': NormalizedEventResult.FAMILY_APPLICATION_OPERATION_OBSERVED,
            'message': NormalizedEventResult.FAMILY_APPLICATION_MESSAGE_OBSERVED,
            'event': NormalizedEventResult.FAMILY_APPLICATION_EVENT_OBSERVED,
        }[item['payload_kind']]

    def _resolve_pool_family(self, item: dict) -> str | None:
        payload_kind = item['payload_kind']
        payload_type = item['decode_result'].get('payload_type')
        rejected = self._is_rejected(item)
        if payload_kind == 'operation':
            return {
                'swap': NormalizedEventResult.FAMILY_POOL_SWAP_REQUESTED,
                'add_liquidity': NormalizedEventResult.FAMILY_POOL_ADD_LIQUIDITY_REQUESTED,
                'remove_liquidity': NormalizedEventResult.FAMILY_POOL_REMOVE_LIQUIDITY_REQUESTED,
                'set_fee_to': NormalizedEventResult.FAMILY_POOL_SET_FEE_TO_REQUESTED,
                'set_fee_to_setter': NormalizedEventResult.FAMILY_POOL_SET_FEE_TO_SETTER_REQUESTED,
            }.get(payload_type)
        if payload_kind == 'message':
            if payload_type == 'request_fund':
                return NormalizedEventResult.FAMILY_POOL_FUND_REQUEST_RECORDED
            if payload_type == 'fund_success':
                return NormalizedEventResult.FAMILY_POOL_FUND_SUCCESS_RECORDED
            if payload_type == 'fund_fail':
                return NormalizedEventResult.FAMILY_POOL_FUND_FAIL_RECORDED
            if payload_type == 'new_transaction':
                return NormalizedEventResult.FAMILY_POOL_TRANSACTION_RECORDED
            if payload_type == 'swap':
                return (
                    NormalizedEventResult.FAMILY_POOL_SWAP_REJECTED
                    if rejected
                    else NormalizedEventResult.FAMILY_POOL_SWAP_MESSAGE_OBSERVED
                )
            if payload_type == 'add_liquidity':
                return (
                    NormalizedEventResult.FAMILY_POOL_ADD_LIQUIDITY_REJECTED
                    if rejected
                    else NormalizedEventResult.FAMILY_POOL_ADD_LIQUIDITY_MESSAGE_OBSERVED
                )
            if payload_type == 'remove_liquidity':
                return (
                    NormalizedEventResult.FAMILY_POOL_REMOVE_LIQUIDITY_REJECTED
                    if rejected
                    else NormalizedEventResult.FAMILY_POOL_REMOVE_LIQUIDITY_MESSAGE_OBSERVED
                )
            if payload_type == 'set_fee_to':
                return (
                    NormalizedEventResult.FAMILY_POOL_SET_FEE_TO_REJECTED
                    if rejected
                    else NormalizedEventResult.FAMILY_POOL_SET_FEE_TO_MESSAGE_OBSERVED
                )
            if payload_type == 'set_fee_to_setter':
                return (
                    NormalizedEventResult.FAMILY_POOL_SET_FEE_TO_SETTER_REJECTED
                    if rejected
                    else NormalizedEventResult.FAMILY_POOL_SET_FEE_TO_SETTER_MESSAGE_OBSERVED
                )
        return None

    def _resolve_swap_family(self, item: dict) -> str | None:
        payload_kind = item['payload_kind']
        payload_type = item['decode_result'].get('payload_type')
        rejected = self._is_rejected(item)
        if payload_kind == 'operation':
            return {
                'initialize_liquidity': NormalizedEventResult.FAMILY_SWAP_INITIALIZE_LIQUIDITY_REQUESTED,
                'create_pool': NormalizedEventResult.FAMILY_SWAP_CREATE_POOL_REQUESTED,
                'update_pool': NormalizedEventResult.FAMILY_SWAP_UPDATE_POOL_REQUESTED,
            }.get(payload_type)
        if payload_kind == 'message':
            if payload_type == 'pool_created':
                return NormalizedEventResult.FAMILY_SWAP_POOL_CREATED_RECORDED
            if payload_type == 'create_user_pool':
                return NormalizedEventResult.FAMILY_SWAP_CREATE_USER_POOL_RECORDED
            if payload_type == 'user_pool_created':
                return NormalizedEventResult.FAMILY_SWAP_USER_POOL_CREATED_RECORDED
            if payload_type == 'initialize_liquidity':
                return (
                    NormalizedEventResult.FAMILY_SWAP_INITIALIZE_LIQUIDITY_REJECTED
                    if rejected
                    else NormalizedEventResult.FAMILY_SWAP_INITIALIZE_LIQUIDITY_MESSAGE_OBSERVED
                )
            if payload_type == 'create_pool':
                return (
                    NormalizedEventResult.FAMILY_SWAP_CREATE_POOL_REJECTED
                    if rejected
                    else NormalizedEventResult.FAMILY_SWAP_CREATE_POOL_MESSAGE_OBSERVED
                )
            if payload_type == 'update_pool':
                return (
                    NormalizedEventResult.FAMILY_SWAP_UPDATE_POOL_REJECTED
                    if rejected
                    else NormalizedEventResult.FAMILY_SWAP_UPDATE_POOL_MESSAGE_OBSERVED
                )
        return None

    def _resolve_meme_family(self, item: dict) -> str | None:
        payload_kind = item['payload_kind']
        payload_type = item['decode_result'].get('payload_type')
        rejected = self._is_rejected(item)
        if payload_kind == 'operation':
            return {
                'transfer': NormalizedEventResult.FAMILY_MEME_TRANSFER_REQUESTED,
                'transfer_from': NormalizedEventResult.FAMILY_MEME_TRANSFER_FROM_REQUESTED,
                'transfer_from_application': NormalizedEventResult.FAMILY_MEME_TRANSFER_FROM_APPLICATION_REQUESTED,
                'initialize_liquidity': NormalizedEventResult.FAMILY_MEME_INITIALIZE_LIQUIDITY_REQUESTED,
                'approve': NormalizedEventResult.FAMILY_MEME_APPROVE_REQUESTED,
                'transfer_ownership': NormalizedEventResult.FAMILY_MEME_TRANSFER_OWNERSHIP_REQUESTED,
                'mine': NormalizedEventResult.FAMILY_MEME_MINE_REQUESTED,
                'transfer_to_caller': NormalizedEventResult.FAMILY_MEME_TRANSFER_TO_CALLER_REQUESTED,
                'mint': NormalizedEventResult.FAMILY_MEME_MINT_REQUESTED,
                'redeem': NormalizedEventResult.FAMILY_MEME_REDEEM_REQUESTED,
            }.get(payload_type)
        if payload_kind == 'message':
            if payload_type == 'liquidity_funded':
                return NormalizedEventResult.FAMILY_MEME_LIQUIDITY_FUNDED_RECORDED
            if payload_type == 'transfer':
                return (
                    NormalizedEventResult.FAMILY_MEME_TRANSFER_REJECTED
                    if rejected
                    else NormalizedEventResult.FAMILY_MEME_TRANSFER_MESSAGE_OBSERVED
                )
            if payload_type == 'transfer_from':
                return (
                    NormalizedEventResult.FAMILY_MEME_TRANSFER_FROM_REJECTED
                    if rejected
                    else NormalizedEventResult.FAMILY_MEME_TRANSFER_FROM_MESSAGE_OBSERVED
                )
            if payload_type == 'transfer_from_application':
                return (
                    NormalizedEventResult.FAMILY_MEME_TRANSFER_FROM_APPLICATION_REJECTED
                    if rejected
                    else NormalizedEventResult.FAMILY_MEME_TRANSFER_FROM_APPLICATION_MESSAGE_OBSERVED
                )
            if payload_type == 'initialize_liquidity':
                return (
                    NormalizedEventResult.FAMILY_MEME_INITIALIZE_LIQUIDITY_REJECTED
                    if rejected
                    else NormalizedEventResult.FAMILY_MEME_INITIALIZE_LIQUIDITY_MESSAGE_OBSERVED
                )
            if payload_type == 'approve':
                return (
                    NormalizedEventResult.FAMILY_MEME_APPROVE_REJECTED
                    if rejected
                    else NormalizedEventResult.FAMILY_MEME_APPROVE_MESSAGE_OBSERVED
                )
            if payload_type == 'transfer_ownership':
                return (
                    NormalizedEventResult.FAMILY_MEME_TRANSFER_OWNERSHIP_REJECTED
                    if rejected
                    else NormalizedEventResult.FAMILY_MEME_TRANSFER_OWNERSHIP_MESSAGE_OBSERVED
                )
            if payload_type == 'mint':
                return (
                    NormalizedEventResult.FAMILY_MEME_MINT_REJECTED
                    if rejected
                    else NormalizedEventResult.FAMILY_MEME_MINT_MESSAGE_OBSERVED
                )
            if payload_type == 'redeem':
                return (
                    NormalizedEventResult.FAMILY_MEME_REDEEM_REJECTED
                    if rejected
                    else NormalizedEventResult.FAMILY_MEME_REDEEM_MESSAGE_OBSERVED
                )
        return None

    def _is_rejected(self, item: dict) -> bool:
        if item.get('rejected') is True:
            return True
        status = item.get('execution_status')
        if isinstance(status, str) and status.lower() == 'rejected':
            return True
        return bool(item.get('reject_reason'))
