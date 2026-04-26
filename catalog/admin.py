from django.contrib import admin
from .models import Category, Product, ProductAgeVariant, ProductImage, ProductSpecification


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    fields = ('image', 'alt_text', 'is_primary', 'sort_order')


class ProductSpecificationInline(admin.TabularInline):
    model = ProductSpecification
    extra = 3
    fields = ('label', 'value', 'icon', 'sort_order')


class ProductAgeVariantInline(admin.TabularInline):
    model = ProductAgeVariant
    extra = 2
    fields = ('age_years', 'price', 'stock')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent', 'is_active', 'sort_order', 'get_products_count')
    list_editable = ('is_active', 'sort_order')
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('is_active', 'parent')
    search_fields = ('name',)

    def get_products_count(self, obj):
        return obj.get_products_count()
    get_products_count.short_description = 'Товаров'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'old_price', 'is_active', 'is_featured', 'stock', 'rating')
    list_editable = ('is_active', 'is_featured', 'stock')
    list_filter = ('is_active', 'is_featured', 'category')
    search_fields = ('name', 'sku')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, ProductSpecificationInline, ProductAgeVariantInline]
    readonly_fields = ('created_at', 'updated_at', 'rating', 'rating_count')
    fieldsets = (
        ('Основное', {
            'fields': ('name', 'slug', 'category', 'sku', 'unit', 'tags')
        }),
        ('Описание', {
            'fields': ('description', 'care_tips')
        }),
        ('Цена и наличие', {
            'fields': ('price', 'old_price', 'stock')
        }),
        ('Изображение', {
            'fields': ('image', 'cart_image')
        }),
        ('Настройки', {
            'fields': ('is_active', 'is_featured')
        }),
        ('Статистика', {
            'fields': ('rating', 'rating_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
