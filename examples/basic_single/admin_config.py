"""Admin registrations for the single-tenant blog example.

Framework models (User, AuditLog, etc.) are registered automatically by
create_admin() with sensible defaults.  Only the app-specific Post model
needs an explicit registration here.
"""
from adminfoundry import ModelAdmin, admin_site, BulkDeleteAction

from examples.basic_single.models import Post


def _word_count(obj: Post) -> int:
    return len((obj.content or "").split())


def _read_time(obj: Post) -> str:
    minutes = max(1, round(_word_count(obj) / 200))
    return f"{minutes} min"


def _excerpt(obj: Post) -> str:
    body = (obj.content or "").strip()
    return body[:100] + ("..." if len(body) > 100 else "")


class PostAdmin(ModelAdmin):
    model           = Post
    label           = "Post"
    label_plural    = "Posts"
    description     = "Blog posts"
    list_display    = ["title", "author", "word_count", "read_time", "published", "created_at"]
    search_fields   = ["title", "content", "author"]
    filter_fields   = ["published"]
    ordering        = ["-created_at"]
    readonly_fields = ["id", "created_at", "updated_at"]
    actions         = [BulkDeleteAction()]
    fieldsets = [
        ("Content",    ["title", "content"]),
        ("Publishing", ["author", "published"]),
    ]
    computed_fields = {
        "word_count": _word_count,
        "read_time":  _read_time,
        "excerpt":    _excerpt,
    }


admin_site.register(PostAdmin())
