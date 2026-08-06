"""Configurable inbound data endpoints (TSD and other devices).

An operator defines a template: which fields a device may send (required and
optional), what to do when a required field is missing, whether records are
stored and for how long, and what the endpoint answers. The endpoint then
accepts device payloads without any programming.
"""
