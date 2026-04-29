from registry.decode_dispatch_result import DecodeDispatchResult


class DecoderDispatcher:
    def __init__(self, application_registry, decoder_registry):
        self.application_registry = application_registry
        self.decoder_registry = decoder_registry

    def dispatch(
        self,
        *,
        application_id: str,
        payload_kind: str,
        raw_bytes: bytes,
    ) -> DecodeDispatchResult:
        application = self.application_registry.resolve(application_id)
        if application is None:
            return DecodeDispatchResult(
                status=DecodeDispatchResult.STATUS_UNRESOLVED_APPLICATION,
                application_id=application_id,
                payload_kind=payload_kind,
                decode_error='application_id is not registered',
            )

        app_type = application['app_type']
        decoder = self.decoder_registry.resolve(
            app_type=app_type,
            payload_kind=payload_kind,
        )
        if decoder is None:
            return DecodeDispatchResult(
                status=DecodeDispatchResult.STATUS_UNIMPLEMENTED_DECODER,
                application_id=application_id,
                payload_kind=payload_kind,
                app_type=app_type,
                decode_error=f'no decoder registered for {app_type}:{payload_kind}',
                metadata_json=application.get('metadata_json'),
            )

        try:
            decoded = decoder.decode(
                raw_bytes=raw_bytes,
                application=application,
                payload_kind=payload_kind,
            )
        except Exception as error:
            return DecodeDispatchResult(
                status=DecodeDispatchResult.STATUS_DECODE_FAILED,
                application_id=application_id,
                payload_kind=payload_kind,
                app_type=app_type,
                decode_error=str(error),
                metadata_json=application.get('metadata_json'),
                decoder_version=self._decoder_version(decoder),
            )

        return DecodeDispatchResult(
            status=DecodeDispatchResult.STATUS_DECODED,
            application_id=application_id,
            payload_kind=payload_kind,
            app_type=app_type,
            payload_type=decoded.get('payload_type'),
            decoded_payload_json=decoded.get('decoded_payload_json'),
            metadata_json=application.get('metadata_json'),
            decoder_version=decoded.get('decoder_version') or self._decoder_version(decoder),
        )

    def _decoder_version(self, decoder) -> str | None:
        if hasattr(decoder, 'decoder_version'):
            version = decoder.decoder_version()
            if version is not None:
                return str(version)
        version = getattr(decoder, 'VERSION', None)
        if version is not None:
            return str(version)
        return None
