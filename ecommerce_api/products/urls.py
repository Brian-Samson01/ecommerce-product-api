from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, CategoryViewSet
from .views import OrderViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'orders', OrderViewSet)


urlpatterns = router.urls