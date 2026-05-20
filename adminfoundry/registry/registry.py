from adminfoundry.registry.admin import ModelAdmin
from adminfoundry.security.validation import validate_resource_name


class AdminRegistry:
    def __init__(self) -> None:
        self._registry: dict[str, ModelAdmin] = {}

    def register(self, admin: ModelAdmin | type[ModelAdmin]) -> None:
        if isinstance(admin, type):
            admin = admin()
        key = validate_resource_name(admin.model_name)
        self._registry[key] = admin

    def is_registered(self, model) -> bool:
        return getattr(model, "__tablename__", None) in self._registry

    def get(self, model_name: str) -> ModelAdmin | None:
        return self._registry.get(model_name)

    def all(self) -> list[ModelAdmin]:
        return list(self._registry.values())

    def model_names(self) -> list[str]:
        return list(self._registry.keys())

    def metadata(self) -> list[dict]:
        return [
            {
                "model": admin.model_name,
                "list_display": admin.list_display,
                "search_fields": admin.search_fields,
                "ordering": admin.ordering,
                "readonly_fields": admin.readonly_fields,
            }
            for admin in self._registry.values()
        ]
