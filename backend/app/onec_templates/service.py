from app.onec_templates.examples import FAILURE_RESPONSE, HTTP_ENDPOINTS, PSEUDO_CODE, REQUEST_ENVELOPE, SUCCESS_RESPONSE


def http_service_template() -> dict:
    return {
        "endpoints": HTTP_ENDPOINTS,
        "request_envelope": REQUEST_ENVELOPE,
        "success_response": SUCCESS_RESPONSE,
        "failure_response": FAILURE_RESPONSE,
        "pseudo_code": PSEUDO_CODE,
    }
