import async_request

from integration.block_not_available_error import BlockNotAvailableError


class LineraGraphqlChainClient:
    """Fetches confirmed blocks through the public Linera GraphQL service."""

    def __init__(self, base_url: str, timeout=(3, 10), header_batch_limit: int = 50):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.header_batch_limit = int(header_batch_limit)
        self._tip_cache_by_chain_id: dict[str, dict] = {}
        self._header_cache_by_chain_id: dict[str, dict[int, dict]] = {}

    async def fetch_block(self, chain_id: str, height: int) -> dict:
        target_height = int(height)
        cached_header = self._header_cache_by_chain_id.get(chain_id, {}).get(target_height)
        if cached_header is not None:
            return await self._fetch_block_by_hash(
                chain_id=chain_id,
                block_hash=str(cached_header['hash']),
            )

        tip = await self._load_tip(chain_id, target_height)
        if tip is None:
            raise BlockNotAvailableError(f'Chain tip not found for {chain_id}')

        tip_height = int(((tip.get('block') or {}).get('header') or {}).get('height'))
        if target_height > tip_height:
            raise BlockNotAvailableError(
                f'Block not found for {chain_id}@{target_height}: tip height is {tip_height}'
            )

        header_envelope = await self._load_header_for_height(
            chain_id=chain_id,
            target_height=target_height,
            tip=tip,
        )
        if header_envelope is not None:
            return await self._fetch_block_by_hash(
                chain_id=chain_id,
                block_hash=str(header_envelope['hash']),
            )

        raise BlockNotAvailableError(f'Block not found for {chain_id}@{target_height}')

    async def _load_tip(self, chain_id: str, target_height: int) -> dict | None:
        cached_tip = self._tip_cache_by_chain_id.get(chain_id)
        if cached_tip is not None:
            cached_tip_height = int(((cached_tip.get('block') or {}).get('header') or {}).get('height'))
            if target_height <= cached_tip_height:
                return cached_tip
        tip = await self._fetch_tip_header(chain_id)
        if tip is not None:
            self._tip_cache_by_chain_id[chain_id] = tip
            self._remember_header(chain_id, tip)
        return tip

    async def _load_header_for_height(self, *, chain_id: str, target_height: int, tip: dict) -> dict | None:
        cached_header = self._header_cache_by_chain_id.get(chain_id, {}).get(target_height)
        if cached_header is not None:
            return cached_header

        tip_height = int(((tip.get('block') or {}).get('header') or {}).get('height'))
        current_hash = str(tip['hash'])
        while current_hash:
            headers = await self._fetch_block_headers(
                chain_id=chain_id,
                from_hash=current_hash,
                limit=min(self.header_batch_limit, (tip_height - target_height) + 1),
            )
            if not headers:
                break

            for header_envelope in headers:
                self._remember_header(chain_id, header_envelope)
                header = ((header_envelope.get('block') or {}).get('header') or {})
                if int(header.get('height')) == target_height:
                    return header_envelope

            last_header = ((headers[-1].get('block') or {}).get('header') or {})
            last_height = int(last_header.get('height'))
            if last_height <= target_height:
                break
            current_hash = last_header.get('previousBlockHash')
        return self._header_cache_by_chain_id.get(chain_id, {}).get(target_height)

    def _remember_header(self, chain_id: str, header_envelope: dict) -> None:
        header = ((header_envelope.get('block') or {}).get('header') or {})
        if header.get('height') is None or header_envelope.get('hash') is None:
            return
        self._header_cache_by_chain_id.setdefault(chain_id, {})[int(header['height'])] = header_envelope

    async def _fetch_tip_header(self, chain_id: str) -> dict | None:
        data = await self._post_query(
            query=self._tip_header_query(),
            variables={'chainId': chain_id},
        )
        return data.get('block')

    async def _fetch_block_headers(self, *, chain_id: str, from_hash: str, limit: int) -> list[dict]:
        data = await self._post_query(
            query=self._block_headers_query(),
            variables={
                'chainId': chain_id,
                'from': from_hash,
                'limit': int(limit),
            },
        )
        return list(data.get('blocks') or [])

    async def _fetch_block_by_hash(self, *, chain_id: str, block_hash: str) -> dict:
        data = await self._post_query(
            query=self._block_by_hash_query(),
            variables={
                'chainId': chain_id,
                'hash': block_hash,
            },
        )
        block = data.get('block')
        if block is None:
            raise RuntimeError(f'Block not found for {chain_id}@{block_hash}')
        return block

    async def _post_query(self, *, query: str, variables: dict) -> dict:
        response = await async_request.post(
            url=self.base_url,
            json={
                'query': query,
                'variables': variables,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if 'errors' in payload:
            raise RuntimeError(str(payload['errors']))
        return payload.get('data') or {}

    def _tip_header_query(self) -> str:
        return '''
        query TipHeader($chainId: ChainId!) {
          block(chainId: $chainId) {
            hash
            block {
              header {
                height
              }
            }
          }
        }
        '''

    def _block_headers_query(self) -> str:
        return '''
        query BlockHeaders($chainId: ChainId!, $from: CryptoHash!, $limit: Int!) {
          blocks(chainId: $chainId, from: $from, limit: $limit) {
            hash
            block {
              header {
                height
                previousBlockHash
              }
            }
          }
        }
        '''

    def _block_by_hash_query(self) -> str:
        return '''
        query BlockByHash($chainId: ChainId!, $hash: CryptoHash!) {
          block(chainId: $chainId, hash: $hash) {
            status
            hash
            block {
              header {
                chainId
                epoch
                height
                timestamp
                stateHash
                previousBlockHash
                authenticatedSigner
                transactionsHash
                messagesHash
                previousMessageBlocksHash
                previousEventBlocksHash
                oracleResponsesHash
                eventsHash
                blobsHash
                operationResultsHash
              }
              body {
                messages {
                  destination
                  authenticatedSigner
                  grant
                  refundGrantTo
                  kind
                  message
                }
                previousMessageBlocks
                previousEventBlocks
                oracleResponses
                events {
                  streamId {
                    applicationId
                    streamName
                  }
                  index
                  value
                }
                blobs
                operationResults
                transactionMetadata {
                  transactionType
                  incomingBundle {
                    origin
                    bundle {
                      height
                      timestamp
                      certificateHash
                      transactionIndex
                      messages {
                        authenticatedSigner
                        grant
                        refundGrantTo
                        kind
                        index
                        message
                        messageMetadata {
                          messageType
                          applicationId
                          userBytesHex
                          systemMessage {
                            systemMessageType
                            credit {
                              target
                              amount
                              source
                            }
                            withdraw {
                              owner
                              amount
                              recipient
                            }
                          }
                        }
                      }
                    }
                    action
                  }
                  operation {
                    operationType
                    applicationId
                    userBytesHex
                    systemOperation {
                      systemOperationType
                      transfer {
                        owner
                        recipient
                        amount
                      }
                      claim {
                        owner
                        targetId
                        recipient
                        amount
                      }
                      openChain {
                        balance
                        ownership {
                          ownershipJson
                        }
                        applicationPermissions {
                          permissionsJson
                        }
                      }
                      changeOwnership {
                        superOwners
                        owners {
                          owner
                          weight
                        }
                        multiLeaderRounds
                        openMultiLeaderRounds
                        timeoutConfig {
                          fastRoundMs
                          baseTimeoutMs
                          timeoutIncrementMs
                          fallbackDurationMs
                        }
                      }
                      changeApplicationPermissions {
                        permissions {
                          permissionsJson
                        }
                      }
                      admin {
                        adminOperationType
                        epoch
                        blobHash
                      }
                      createApplication {
                        moduleId
                        parametersHex
                        instantiationArgumentHex
                        requiredApplicationIds
                      }
                      publishDataBlob {
                        blobHash
                      }
                      verifyBlob {
                        blobId
                      }
                      publishModule {
                        moduleId
                      }
                    }
                  }
                }
              }
            }
          }
        }
        '''
