from rest_framework import serializers
from .models import Product, Category
from .models import Order, OrderItem
from django.db import transaction
from rest_framework import serializers

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source="category.name")

    class Meta:
        model = Product
        fields = "__all__"

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source="product.name")
    product_price = serializers.ReadOnlyField(source="product.price")
    total_price = serializers.ReadOnlyField()

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "product_price",
            "quantity",
            "total_price",
        ]

 class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    total_price = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = [
            "id",
            "user",
            "created_at",
            "is_completed",
            "items",
            "total_price",
        ]
        read_only_fields = ["user"]

    def create(self, validated_data):
        items_data = validated_data.pop("items")

    with transaction.atomic():
        order = Order.objects.create(**validated_data)

        for item_data in items_data:
            product = item_data["product"]
            quantity = item_data["quantity"]

            # ✅ Check stock availability
            if product.stock_quantity < quantity:
                raise serializers.ValidationError(
                    f"Not enough stock for {product.name}"
                )

            # ✅ Reduce stock
            product.stock_quantity -= quantity
            product.save()

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
            )

        return order    