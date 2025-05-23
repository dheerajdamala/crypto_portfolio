from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.FloatField(default=0.0)

    def __str__(self):
        return f"{self.user.username}'s Profile"

class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    symbol = models.CharField(max_length=10)
    uuid = models.CharField(max_length=50)
    amount = models.FloatField()
    price = models.FloatField()
    type = models.CharField(max_length=10)  # Changed from choices to simple CharField
    status = models.CharField(max_length=10, default='completed')  # Changed from choices
    timestamp = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.user.username} - {self.type} {self.amount} {self.symbol} at {self.timestamp}"
    
    class Meta:
        ordering = ['-timestamp']

class WatchlistItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    uuid = models.CharField(max_length=50)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'uuid')
        
    def __str__(self):
        return f"{self.user.username}'s watchlist item: {self.uuid}"