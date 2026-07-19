__all__ = ["init_language_extraction"]


from flask import g, request

SUPPORTED_LANGUAGES = ["en", "de"]
DEFAULT_LANGUAGE = "en"


def init_language_extraction(app):
    """Extracts preferred language from request and sets g.preferred_language to preferred language or default language"""

    @app.before_request
    def extract_language():
        g.preferred_language = (
            request.accept_languages.best_match(SUPPORTED_LANGUAGES) or DEFAULT_LANGUAGE
        )
