from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.db.models.signals import post_migrate
from django.dispatch import receiver

class User(AbstractUser):
    """
    Custom User model.
    
    The link between User and Groups is inherited from AbstractUser (via PermissionsMixin).
    Field name: 'groups' (ManyToManyField to django.contrib.auth.models.Group)
    """
    
    class Role(models.TextChoices):
        ADMIN = "Admin", "Admin"
        STORE_MANAGER = "Store Manager", "Store Manager"
        CUSTOMER = "Customer", "Customer"

    def is_admin(self):
        return self.groups.filter(name=self.Role.ADMIN).exists()

    def is_store_manager(self):
        return self.groups.filter(name=self.Role.STORE_MANAGER).exists()

    def is_customer(self):
        return self.groups.filter(name=self.Role.CUSTOMER).exists()

    def add_role(self, role_name):
        """
        Helper to add a user to a group (role).
        """
        group, _ = Group.objects.get_or_create(name=role_name)
        self.groups.add(group)

@receiver(post_migrate)
def create_roles(sender, **kwargs):
    if sender.name == 'users':
        for role in User.Role:
            Group.objects.get_or_create(name=role.value)
