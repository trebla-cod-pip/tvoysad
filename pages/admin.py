from django.contrib import admin
from .models import Page, ContactMessage, SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Контакты', {
            'fields': ('phone', 'phone_delivery', 'email', 'schedule', 'address'),
        }),
        ('Доставка', {
            'fields': ('courier_price',),
        }),
        ('Изображения', {
            'fields': ('hero_image',),
        }),
        ('Telegram-уведомления', {
            'fields': ('tg_bot_token', 'tg_admin_chat_id'),
            'description': (
                'Укажите токен бота и Chat ID администратора, '
                'чтобы получать уведомления о новых заказах в Telegram.'
            ),
        }),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_published')
    prepopulated_fields = {'slug': ('title',)}


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact', 'is_read', 'created_at')
    list_editable = ('is_read',)
    list_filter = ('is_read',)
    readonly_fields = ('created_at',)
