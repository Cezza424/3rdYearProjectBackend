from django.apps import AppConfig


class ClaimsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'claims'
    
    def ready(self):
        """Import signals when the app is ready"""
        import claims.signals
