from django.urls import path

from . import views

urlpatterns = [
    path(
        "knowledge-bases/",
        views.KnowledgeBaseListView.as_view(),
        name="knowledge-base-list",
    ),
    path(
        "knowledge-bases/<int:id>/",
        views.KnowledgeBaseDetailView.as_view(),
        name="knowledge-base-detail",
    ),
    path(
        "knowledge-bases/<int:kb_id>/data-sources/",
        views.DataSourceListView.as_view(),
        name="data-source-list",
    ),
]
