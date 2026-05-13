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
        if app_type == 'proxy':
            family = self._resolve_proxy_family(item)
            if family is not None:
                return family
        if app_type == 'ams':
            family = self._resolve_ams_family(item)
            if family is not None:
                return family
        if app_type == 'blob-gateway':
            family = self._resolve_blob_gateway_family(item)
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
                return NormalizedEventResult.FAMILY_POOL_NEW_TRANSACTION_RECORDED
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
        if payload_kind == 'event':
            return {
                'swap_executed': NormalizedEventResult.FAMILY_POOL_SWAP_EXECUTED,
                'add_liquidity_executed': NormalizedEventResult.FAMILY_POOL_ADD_LIQUIDITY_EXECUTED,
                'remove_liquidity_executed': NormalizedEventResult.FAMILY_POOL_REMOVE_LIQUIDITY_EXECUTED,
            }.get(payload_type)
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
                'creator_chain_id': NormalizedEventResult.FAMILY_MEME_CREATOR_CHAIN_ID_REQUESTED,
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

    def _resolve_proxy_family(self, item: dict) -> str | None:
        payload_kind = item['payload_kind']
        payload_type = item['decode_result'].get('payload_type')
        rejected = self._is_rejected(item)
        if payload_kind == 'operation':
            return {
                'propose_add_genesis_miner': NormalizedEventResult.FAMILY_PROXY_PROPOSE_ADD_GENESIS_MINER_REQUESTED,
                'approve_add_genesis_miner': NormalizedEventResult.FAMILY_PROXY_APPROVE_ADD_GENESIS_MINER_REQUESTED,
                'propose_remove_genesis_miner': NormalizedEventResult.FAMILY_PROXY_PROPOSE_REMOVE_GENESIS_MINER_REQUESTED,
                'approve_remove_genesis_miner': NormalizedEventResult.FAMILY_PROXY_APPROVE_REMOVE_GENESIS_MINER_REQUESTED,
                'register_miner': NormalizedEventResult.FAMILY_PROXY_REGISTER_MINER_REQUESTED,
                'deregister_miner': NormalizedEventResult.FAMILY_PROXY_DEREGISTER_MINER_REQUESTED,
                'create_meme': NormalizedEventResult.FAMILY_PROXY_CREATE_MEME_REQUESTED,
                'propose_add_operator': NormalizedEventResult.FAMILY_PROXY_PROPOSE_ADD_OPERATOR_REQUESTED,
                'approve_add_operator': NormalizedEventResult.FAMILY_PROXY_APPROVE_ADD_OPERATOR_REQUESTED,
                'propose_ban_operator': NormalizedEventResult.FAMILY_PROXY_PROPOSE_BAN_OPERATOR_REQUESTED,
                'approve_ban_operator': NormalizedEventResult.FAMILY_PROXY_APPROVE_BAN_OPERATOR_REQUESTED,
            }.get(payload_type)
        if payload_kind == 'message':
            if payload_type == 'meme_created':
                return NormalizedEventResult.FAMILY_PROXY_MEME_CREATED_RECORDED
            message_family_map = {
                'propose_add_genesis_miner': (
                    NormalizedEventResult.FAMILY_PROXY_PROPOSE_ADD_GENESIS_MINER_MESSAGE_OBSERVED,
                    NormalizedEventResult.FAMILY_PROXY_PROPOSE_ADD_GENESIS_MINER_REJECTED,
                ),
                'approve_add_genesis_miner': (
                    NormalizedEventResult.FAMILY_PROXY_APPROVE_ADD_GENESIS_MINER_MESSAGE_OBSERVED,
                    NormalizedEventResult.FAMILY_PROXY_APPROVE_ADD_GENESIS_MINER_REJECTED,
                ),
                'propose_remove_genesis_miner': (
                    NormalizedEventResult.FAMILY_PROXY_PROPOSE_REMOVE_GENESIS_MINER_MESSAGE_OBSERVED,
                    NormalizedEventResult.FAMILY_PROXY_PROPOSE_REMOVE_GENESIS_MINER_REJECTED,
                ),
                'approve_remove_genesis_miner': (
                    NormalizedEventResult.FAMILY_PROXY_APPROVE_REMOVE_GENESIS_MINER_MESSAGE_OBSERVED,
                    NormalizedEventResult.FAMILY_PROXY_APPROVE_REMOVE_GENESIS_MINER_REJECTED,
                ),
                'register_miner': (
                    NormalizedEventResult.FAMILY_PROXY_REGISTER_MINER_MESSAGE_OBSERVED,
                    NormalizedEventResult.FAMILY_PROXY_REGISTER_MINER_REJECTED,
                ),
                'deregister_miner': (
                    NormalizedEventResult.FAMILY_PROXY_DEREGISTER_MINER_MESSAGE_OBSERVED,
                    NormalizedEventResult.FAMILY_PROXY_DEREGISTER_MINER_REJECTED,
                ),
                'create_meme': (
                    NormalizedEventResult.FAMILY_PROXY_CREATE_MEME_MESSAGE_OBSERVED,
                    NormalizedEventResult.FAMILY_PROXY_CREATE_MEME_REJECTED,
                ),
                'create_meme_ext': (
                    NormalizedEventResult.FAMILY_PROXY_CREATE_MEME_EXT_MESSAGE_OBSERVED,
                    NormalizedEventResult.FAMILY_PROXY_CREATE_MEME_EXT_REJECTED,
                ),
                'propose_add_operator': (
                    NormalizedEventResult.FAMILY_PROXY_PROPOSE_ADD_OPERATOR_MESSAGE_OBSERVED,
                    NormalizedEventResult.FAMILY_PROXY_PROPOSE_ADD_OPERATOR_REJECTED,
                ),
                'approve_add_operator': (
                    NormalizedEventResult.FAMILY_PROXY_APPROVE_ADD_OPERATOR_MESSAGE_OBSERVED,
                    NormalizedEventResult.FAMILY_PROXY_APPROVE_ADD_OPERATOR_REJECTED,
                ),
                'propose_ban_operator': (
                    NormalizedEventResult.FAMILY_PROXY_PROPOSE_BAN_OPERATOR_MESSAGE_OBSERVED,
                    NormalizedEventResult.FAMILY_PROXY_PROPOSE_BAN_OPERATOR_REJECTED,
                ),
                'approve_ban_operator': (
                    NormalizedEventResult.FAMILY_PROXY_APPROVE_BAN_OPERATOR_MESSAGE_OBSERVED,
                    NormalizedEventResult.FAMILY_PROXY_APPROVE_BAN_OPERATOR_REJECTED,
                ),
            }
            family_pair = message_family_map.get(payload_type)
            if family_pair is not None:
                return family_pair[1] if rejected else family_pair[0]
        return None

    def _resolve_ams_family(self, item: dict) -> str | None:
        payload_kind = item['payload_kind']
        payload_type = item['decode_result'].get('payload_type')
        if payload_kind == 'operation':
            return {
                'register': NormalizedEventResult.FAMILY_AMS_REGISTER_REQUESTED,
                'claim': NormalizedEventResult.FAMILY_AMS_CLAIM_REQUESTED,
                'add_application_type': NormalizedEventResult.FAMILY_AMS_ADD_APPLICATION_TYPE_REQUESTED,
                'update': NormalizedEventResult.FAMILY_AMS_UPDATE_REQUESTED,
            }.get(payload_type)
        if payload_kind == 'message':
            return {
                'register': NormalizedEventResult.FAMILY_AMS_REGISTER_RECORDED,
                'claim': NormalizedEventResult.FAMILY_AMS_CLAIM_RECORDED,
                'add_application_type': NormalizedEventResult.FAMILY_AMS_ADD_APPLICATION_TYPE_RECORDED,
                'update': NormalizedEventResult.FAMILY_AMS_UPDATE_RECORDED,
            }.get(payload_type)
        return None

    def _resolve_blob_gateway_family(self, item: dict) -> str | None:
        payload_kind = item['payload_kind']
        payload_type = item['decode_result'].get('payload_type')
        if payload_type != 'blob_gateway_register':
            return None
        if payload_kind == 'operation':
            return NormalizedEventResult.FAMILY_BLOB_GATEWAY_REGISTER_REQUESTED
        if payload_kind == 'message':
            return NormalizedEventResult.FAMILY_BLOB_GATEWAY_REGISTER_RECORDED
        return None

    def _is_rejected(self, item: dict) -> bool:
        if item.get('rejected') is True:
            return True
        status = item.get('execution_status')
        if isinstance(status, str) and status.lower() == 'rejected':
            return True
        return bool(item.get('reject_reason'))
