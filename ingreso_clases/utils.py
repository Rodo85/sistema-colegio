from dataclasses import dataclass
from typing import Optional


@dataclass
class WhatsAppConfig:
    phone_from: Optional[str]
    token: Optional[str]
    from_id: Optional[str]


def send_whatsapp_message(cfg: WhatsAppConfig, to_phone_e164: str, text: str) -> bool:
    """Placeholder para integración WhatsApp.
    Retorna True si "aparenta" éxito. Aquí se puede integrar Twilio/Meta API.
    """
    if not (cfg and cfg.token and (cfg.from_id or cfg.phone_from)):
        return False
    # Aquí integrar:
    # - Meta Cloud API: POST https://graph.facebook.com/v19.0/{from_id}/messages
    # - Twilio API: client.messages.create(from=cfg.phone_from, to=to_phone_e164, body=text)
    # Por ahora devolvemos True para no bloquear el flujo.
    return True































