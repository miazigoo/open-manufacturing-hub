"""Config distribution from a central OMH to branch instances (holding mode).

Center exposes a signed config bundle (all integration configuration, secrets
masked). Branch OMH instances pull it on an interval or on demand and apply it
with the standard config import in upsert mode — updating an integration at the
center rolls out to every branch automatically.
"""
