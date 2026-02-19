from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = UserAdmin.list_display + ('is_admin', 'is_store_manager', 'is_customer')
    
    def is_admin(self, obj):
        return obj.is_admin()
    is_admin.boolean = True
    
    def is_store_manager(self, obj):
        return obj.is_store_manager()
    is_store_manager.boolean = True
    
    def is_customer(self, obj):
        return obj.is_customer()
    is_customer.boolean = True
