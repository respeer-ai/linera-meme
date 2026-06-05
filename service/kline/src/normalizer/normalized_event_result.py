class NormalizedEventResult:
    STATUS_OBSERVED = 'observed'
    STATUS_REJECTED = 'rejected'
    STATUS_DECODE_FAILED = 'decode_failed'
    STATUS_DERIVED = 'derived'

    FAMILY_DECODE_UNRESOLVED = 'decode_unresolved'
    FAMILY_DECODE_UNIMPLEMENTED = 'decode_unimplemented'
    FAMILY_DECODE_FAILED = 'decode_failed'
    FAMILY_APPLICATION_OPERATION_OBSERVED = 'application_operation_observed'
    FAMILY_APPLICATION_MESSAGE_OBSERVED = 'application_message_observed'
    FAMILY_APPLICATION_EVENT_OBSERVED = 'application_event_observed'
    FAMILY_APPLICATION_OPERATION_REJECTED = 'application_operation_rejected'
    FAMILY_APPLICATION_MESSAGE_REJECTED = 'application_message_rejected'
    FAMILY_APPLICATION_EVENT_REJECTED = 'application_event_rejected'
    FAMILY_POOL_SWAP_REQUESTED = 'pool_swap_requested'
    FAMILY_POOL_SWAP_MESSAGE_OBSERVED = 'pool_swap_message_observed'
    FAMILY_POOL_SWAP_REJECTED = 'pool_swap_message_rejected'
    FAMILY_POOL_ADD_LIQUIDITY_REQUESTED = 'pool_add_liquidity_requested'
    FAMILY_POOL_ADD_LIQUIDITY_MESSAGE_OBSERVED = 'pool_add_liquidity_message_observed'
    FAMILY_POOL_ADD_LIQUIDITY_REJECTED = 'pool_add_liquidity_message_rejected'
    FAMILY_POOL_REMOVE_LIQUIDITY_REQUESTED = 'pool_remove_liquidity_requested'
    FAMILY_POOL_REMOVE_LIQUIDITY_MESSAGE_OBSERVED = 'pool_remove_liquidity_message_observed'
    FAMILY_POOL_REMOVE_LIQUIDITY_REJECTED = 'pool_remove_liquidity_message_rejected'
    FAMILY_POOL_INITIALIZE_LIQUIDITY_MESSAGE_OBSERVED = 'pool_initialize_liquidity_message_observed'
    FAMILY_POOL_INITIALIZE_LIQUIDITY_REJECTED = 'pool_initialize_liquidity_message_rejected'
    FAMILY_POOL_FUND_REQUEST_RECORDED = 'pool_fund_request_recorded'
    FAMILY_POOL_FUND_RESULT_RECORDED = 'pool_fund_result_recorded'
    FAMILY_POOL_ADD_LIQUIDITY_TRANSFER_RECEIPT_RECORDED = 'pool_add_liquidity_transfer_receipt_recorded'
    FAMILY_POOL_ADD_LIQUIDITY_TRANSFER_RECEIPT_REJECTED = 'pool_add_liquidity_transfer_receipt_rejected'
    FAMILY_POOL_SWAP_TRANSFER_RECEIPT_RECORDED = 'pool_swap_transfer_receipt_recorded'
    FAMILY_POOL_SWAP_TRANSFER_RECEIPT_REJECTED = 'pool_swap_transfer_receipt_rejected'
    FAMILY_POOL_CLAIM_REQUESTED = 'pool_claim_requested'
    FAMILY_POOL_CLAIM_RECORDED = 'pool_claim_recorded'
    FAMILY_POOL_CLAIM_REJECTED = 'pool_claim_rejected'
    FAMILY_POOL_CLAIM_TRANSFER_RECEIPT_RECORDED = 'pool_claim_transfer_receipt_recorded'
    FAMILY_POOL_CLAIM_TRANSFER_RECEIPT_REJECTED = 'pool_claim_transfer_receipt_rejected'
    FAMILY_POOL_NEW_TRANSACTION_RECORDED = 'pool_new_transaction_recorded'
    FAMILY_POOL_SWAP_EXECUTED = 'pool_swap_executed'
    FAMILY_POOL_ADD_LIQUIDITY_EXECUTED = 'pool_add_liquidity_executed'
    FAMILY_POOL_REMOVE_LIQUIDITY_EXECUTED = 'pool_remove_liquidity_executed'
    FAMILY_POOL_SET_FEE_TO_REQUESTED = 'pool_set_fee_to_requested'
    FAMILY_POOL_SET_FEE_TO_MESSAGE_OBSERVED = 'pool_set_fee_to_message_observed'
    FAMILY_POOL_SET_FEE_TO_REJECTED = 'pool_set_fee_to_message_rejected'
    FAMILY_POOL_SET_FEE_TO_SETTER_REQUESTED = 'pool_set_fee_to_setter_requested'
    FAMILY_POOL_SET_FEE_TO_SETTER_MESSAGE_OBSERVED = 'pool_set_fee_to_setter_message_observed'
    FAMILY_POOL_SET_FEE_TO_SETTER_REJECTED = 'pool_set_fee_to_setter_message_rejected'
    FAMILY_SWAP_INITIALIZE_LIQUIDITY_REQUESTED = 'swap_initialize_liquidity_requested'
    FAMILY_SWAP_INITIALIZE_LIQUIDITY_MESSAGE_OBSERVED = 'swap_initialize_liquidity_message_observed'
    FAMILY_SWAP_INITIALIZE_LIQUIDITY_REJECTED = 'swap_initialize_liquidity_message_rejected'
    FAMILY_SWAP_CREATE_POOL_REQUESTED = 'swap_create_pool_requested'
    FAMILY_SWAP_CREATE_POOL_MESSAGE_OBSERVED = 'swap_create_pool_message_observed'
    FAMILY_SWAP_CREATE_POOL_REJECTED = 'swap_create_pool_message_rejected'
    FAMILY_SWAP_POOL_CREATED_RECORDED = 'swap_pool_created_recorded'
    FAMILY_SWAP_CREATE_USER_POOL_RECORDED = 'swap_create_user_pool_recorded'
    FAMILY_SWAP_USER_POOL_CREATED_RECORDED = 'swap_user_pool_created_recorded'
    FAMILY_SWAP_UPDATE_POOL_REQUESTED = 'swap_update_pool_requested'
    FAMILY_SWAP_UPDATE_POOL_MESSAGE_OBSERVED = 'swap_update_pool_message_observed'
    FAMILY_SWAP_UPDATE_POOL_REJECTED = 'swap_update_pool_message_rejected'
    FAMILY_MEME_TRANSFER_REQUESTED = 'meme_transfer_requested'
    FAMILY_MEME_TRANSFER_MESSAGE_OBSERVED = 'meme_transfer_message_observed'
    FAMILY_MEME_TRANSFER_REJECTED = 'meme_transfer_message_rejected'
    FAMILY_MEME_CREATOR_CHAIN_ID_REQUESTED = 'meme_creator_chain_id_requested'
    FAMILY_MEME_TRANSFER_FROM_REQUESTED = 'meme_transfer_from_requested'
    FAMILY_MEME_TRANSFER_FROM_MESSAGE_OBSERVED = 'meme_transfer_from_message_observed'
    FAMILY_MEME_TRANSFER_FROM_REJECTED = 'meme_transfer_from_message_rejected'
    FAMILY_MEME_TRANSFER_FROM_APPLICATION_REQUESTED = 'meme_transfer_from_application_requested'
    FAMILY_MEME_TRANSFER_FROM_APPLICATION_MESSAGE_OBSERVED = 'meme_transfer_from_application_message_observed'
    FAMILY_MEME_TRANSFER_FROM_APPLICATION_REJECTED = 'meme_transfer_from_application_message_rejected'
    FAMILY_MEME_INITIALIZE_LIQUIDITY_REQUESTED = 'meme_initialize_liquidity_requested'
    FAMILY_MEME_INITIALIZE_LIQUIDITY_MESSAGE_OBSERVED = 'meme_initialize_liquidity_message_observed'
    FAMILY_MEME_INITIALIZE_LIQUIDITY_REJECTED = 'meme_initialize_liquidity_message_rejected'
    FAMILY_MEME_APPROVE_REQUESTED = 'meme_approve_requested'
    FAMILY_MEME_APPROVE_MESSAGE_OBSERVED = 'meme_approve_message_observed'
    FAMILY_MEME_APPROVE_REJECTED = 'meme_approve_message_rejected'
    FAMILY_MEME_TRANSFER_OWNERSHIP_REQUESTED = 'meme_transfer_ownership_requested'
    FAMILY_MEME_TRANSFER_OWNERSHIP_MESSAGE_OBSERVED = 'meme_transfer_ownership_message_observed'
    FAMILY_MEME_TRANSFER_OWNERSHIP_REJECTED = 'meme_transfer_ownership_message_rejected'
    FAMILY_MEME_MINE_REQUESTED = 'meme_mine_requested'
    FAMILY_MEME_TRANSFER_TO_CALLER_REQUESTED = 'meme_transfer_to_caller_requested'
    FAMILY_MEME_MINT_REQUESTED = 'meme_mint_requested'
    FAMILY_MEME_MINT_MESSAGE_OBSERVED = 'meme_mint_message_observed'
    FAMILY_MEME_MINT_REJECTED = 'meme_mint_message_rejected'
    FAMILY_MEME_REDEEM_REQUESTED = 'meme_redeem_requested'
    FAMILY_MEME_REDEEM_MESSAGE_OBSERVED = 'meme_redeem_message_observed'
    FAMILY_MEME_REDEEM_REJECTED = 'meme_redeem_message_rejected'
    FAMILY_MEME_LIQUIDITY_FUNDED_RECORDED = 'meme_liquidity_funded_recorded'
    FAMILY_PROXY_PROPOSE_ADD_GENESIS_MINER_REQUESTED = 'proxy_propose_add_genesis_miner_requested'
    FAMILY_PROXY_APPROVE_ADD_GENESIS_MINER_REQUESTED = 'proxy_approve_add_genesis_miner_requested'
    FAMILY_PROXY_PROPOSE_REMOVE_GENESIS_MINER_REQUESTED = 'proxy_propose_remove_genesis_miner_requested'
    FAMILY_PROXY_APPROVE_REMOVE_GENESIS_MINER_REQUESTED = 'proxy_approve_remove_genesis_miner_requested'
    FAMILY_PROXY_REGISTER_MINER_REQUESTED = 'proxy_register_miner_requested'
    FAMILY_PROXY_DEREGISTER_MINER_REQUESTED = 'proxy_deregister_miner_requested'
    FAMILY_PROXY_CREATE_MEME_REQUESTED = 'proxy_create_meme_requested'
    FAMILY_PROXY_PROPOSE_ADD_OPERATOR_REQUESTED = 'proxy_propose_add_operator_requested'
    FAMILY_PROXY_APPROVE_ADD_OPERATOR_REQUESTED = 'proxy_approve_add_operator_requested'
    FAMILY_PROXY_PROPOSE_BAN_OPERATOR_REQUESTED = 'proxy_propose_ban_operator_requested'
    FAMILY_PROXY_APPROVE_BAN_OPERATOR_REQUESTED = 'proxy_approve_ban_operator_requested'
    FAMILY_PROXY_PROPOSE_ADD_GENESIS_MINER_MESSAGE_OBSERVED = 'proxy_propose_add_genesis_miner_message_observed'
    FAMILY_PROXY_PROPOSE_ADD_GENESIS_MINER_REJECTED = 'proxy_propose_add_genesis_miner_message_rejected'
    FAMILY_PROXY_APPROVE_ADD_GENESIS_MINER_MESSAGE_OBSERVED = 'proxy_approve_add_genesis_miner_message_observed'
    FAMILY_PROXY_APPROVE_ADD_GENESIS_MINER_REJECTED = 'proxy_approve_add_genesis_miner_message_rejected'
    FAMILY_PROXY_PROPOSE_REMOVE_GENESIS_MINER_MESSAGE_OBSERVED = 'proxy_propose_remove_genesis_miner_message_observed'
    FAMILY_PROXY_PROPOSE_REMOVE_GENESIS_MINER_REJECTED = 'proxy_propose_remove_genesis_miner_message_rejected'
    FAMILY_PROXY_APPROVE_REMOVE_GENESIS_MINER_MESSAGE_OBSERVED = 'proxy_approve_remove_genesis_miner_message_observed'
    FAMILY_PROXY_APPROVE_REMOVE_GENESIS_MINER_REJECTED = 'proxy_approve_remove_genesis_miner_message_rejected'
    FAMILY_PROXY_REGISTER_MINER_MESSAGE_OBSERVED = 'proxy_register_miner_message_observed'
    FAMILY_PROXY_REGISTER_MINER_REJECTED = 'proxy_register_miner_message_rejected'
    FAMILY_PROXY_DEREGISTER_MINER_MESSAGE_OBSERVED = 'proxy_deregister_miner_message_observed'
    FAMILY_PROXY_DEREGISTER_MINER_REJECTED = 'proxy_deregister_miner_message_rejected'
    FAMILY_PROXY_CREATE_MEME_MESSAGE_OBSERVED = 'proxy_create_meme_message_observed'
    FAMILY_PROXY_CREATE_MEME_REJECTED = 'proxy_create_meme_message_rejected'
    FAMILY_PROXY_CREATE_MEME_EXT_MESSAGE_OBSERVED = 'proxy_create_meme_ext_message_observed'
    FAMILY_PROXY_CREATE_MEME_EXT_REJECTED = 'proxy_create_meme_ext_message_rejected'
    FAMILY_PROXY_MEME_CREATED_RECORDED = 'proxy_meme_created_recorded'
    FAMILY_PROXY_PROPOSE_ADD_OPERATOR_MESSAGE_OBSERVED = 'proxy_propose_add_operator_message_observed'
    FAMILY_PROXY_PROPOSE_ADD_OPERATOR_REJECTED = 'proxy_propose_add_operator_message_rejected'
    FAMILY_PROXY_APPROVE_ADD_OPERATOR_MESSAGE_OBSERVED = 'proxy_approve_add_operator_message_observed'
    FAMILY_PROXY_APPROVE_ADD_OPERATOR_REJECTED = 'proxy_approve_add_operator_message_rejected'
    FAMILY_PROXY_PROPOSE_BAN_OPERATOR_MESSAGE_OBSERVED = 'proxy_propose_ban_operator_message_observed'
    FAMILY_PROXY_PROPOSE_BAN_OPERATOR_REJECTED = 'proxy_propose_ban_operator_message_rejected'
    FAMILY_PROXY_APPROVE_BAN_OPERATOR_MESSAGE_OBSERVED = 'proxy_approve_ban_operator_message_observed'
    FAMILY_PROXY_APPROVE_BAN_OPERATOR_REJECTED = 'proxy_approve_ban_operator_message_rejected'
    FAMILY_AMS_REGISTER_REQUESTED = 'ams_register_requested'
    FAMILY_AMS_REGISTER_RECORDED = 'ams_register_recorded'
    FAMILY_AMS_CLAIM_REQUESTED = 'ams_claim_requested'
    FAMILY_AMS_CLAIM_RECORDED = 'ams_claim_recorded'
    FAMILY_AMS_ADD_APPLICATION_TYPE_REQUESTED = 'ams_add_application_type_requested'
    FAMILY_AMS_ADD_APPLICATION_TYPE_RECORDED = 'ams_add_application_type_recorded'
    FAMILY_AMS_UPDATE_REQUESTED = 'ams_update_requested'
    FAMILY_AMS_UPDATE_RECORDED = 'ams_update_recorded'
    FAMILY_BLOB_GATEWAY_REGISTER_REQUESTED = 'blob_gateway_register_requested'
    FAMILY_BLOB_GATEWAY_REGISTER_RECORDED = 'blob_gateway_register_recorded'

    def __init__(
        self,
        *,
        normalized_event_id: str,
        raw_fact_id: str,
        raw_table: str,
        application_id: str,
        payload_kind: str,
        event_family: str,
        event_type: str,
        correlation_key: str,
        normalization_status: str,
        event_payload_json: dict[str, object] | None = None,
        source_chain_id: str | None = None,
        target_chain_id: str | None = None,
        source_block_hash: str | None = None,
        target_block_hash: str | None = None,
        source_cert_hash: str | None = None,
        transaction_index: int | None = None,
        message_index: int | None = None,
        app_type: str | None = None,
        payload_type: str | None = None,
        decode_status: str | None = None,
        reprocess_reason: str | None = None,
    ):
        self.normalized_event_id = normalized_event_id
        self.raw_fact_id = raw_fact_id
        self.raw_table = raw_table
        self.application_id = application_id
        self.payload_kind = payload_kind
        self.event_family = event_family
        self.event_type = event_type
        self.correlation_key = correlation_key
        self.normalization_status = normalization_status
        self.event_payload_json = event_payload_json or {}
        self.source_chain_id = source_chain_id
        self.target_chain_id = target_chain_id
        self.source_block_hash = source_block_hash
        self.target_block_hash = target_block_hash
        self.source_cert_hash = source_cert_hash
        self.transaction_index = transaction_index
        self.message_index = message_index
        self.app_type = app_type
        self.payload_type = payload_type
        self.decode_status = decode_status
        self.reprocess_reason = reprocess_reason

    def to_dict(self) -> dict[str, object]:
        return {
            'normalized_event_id': self.normalized_event_id,
            'raw_fact_id': self.raw_fact_id,
            'raw_table': self.raw_table,
            'application_id': self.application_id,
            'payload_kind': self.payload_kind,
            'event_family': self.event_family,
            'event_type': self.event_type,
            'correlation_key': self.correlation_key,
            'normalization_status': self.normalization_status,
            'event_payload_json': self.event_payload_json,
            'source_chain_id': self.source_chain_id,
            'target_chain_id': self.target_chain_id,
            'source_block_hash': self.source_block_hash,
            'target_block_hash': self.target_block_hash,
            'source_cert_hash': self.source_cert_hash,
            'transaction_index': self.transaction_index,
            'message_index': self.message_index,
            'app_type': self.app_type,
            'payload_type': self.payload_type,
            'decode_status': self.decode_status,
            'reprocess_reason': self.reprocess_reason,
        }
