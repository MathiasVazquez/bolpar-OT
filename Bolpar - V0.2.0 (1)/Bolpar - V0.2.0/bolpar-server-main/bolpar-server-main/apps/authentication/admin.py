from django.contrib import admin
from .models import CustomUser


class CustomUserAdmin(admin.ModelAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'machineTurn')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', 'machineTurn')

admin.site.register(CustomUser, CustomUserAdmin)