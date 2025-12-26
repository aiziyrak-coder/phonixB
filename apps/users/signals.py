"""
Signals for users app
Handles post-save actions and notifications
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()


@receiver(post_save, sender=User)
def user_created(sender, instance, created, **kwargs):
    """
    Signal handler for when a user is created
    """
    if created:
        # Welcome notification or email can be sent here
        print(f"New user created: {instance.get_full_name()}")
        
        # Initialize gamification
        if not instance.gamification_badges:
            instance.gamification_badges = ['Yangi foydalanuvchi']
            instance.save(update_fields=['gamification_badges'])
