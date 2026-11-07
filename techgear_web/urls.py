"""
URL configuration for techgear_web project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from techgear_web.store.views import (
    admin_dashboard,
    admin_login,
    client_login,
    client_signup,
    confirm_delete_product,
    delete_product,
    edit_product,
    home_view,
    logout_view,
    new_product,
    products_view,
    purchase_product,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home_view, name="home"),
    path("ingresar/", client_login, name="client-login"),
    path("admin-ingresar/", admin_login, name="admin-login"),
    path("registro/", client_signup, name="client-signup"),
    path("salir/", logout_view, name="logout"),
    path("productos/", products_view, name="catalog-products"),
    path(
        "productos/<str:producto_id>/comprar/",
        purchase_product,
        name="purchase-product",
    ),
    path("dashboard/", admin_dashboard, name="admin-dashboard"),
    path(
        "dashboard/productos/<str:producto_id>/eliminar/",
        delete_product,
        name="delete-product",
    ),
    path(
        "dashboard/productos/<str:producto_id>/eliminar/confirmar/",
        confirm_delete_product,
        name="confirm-delete-product",
    ),
    path(
        "dashboard/productos/<str:producto_id>/editar/",
        edit_product,
        name="edit-product",
    ),
    path("dashboard/productos/nuevo/", new_product, name="new-product"),
]
