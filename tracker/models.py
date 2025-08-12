from django.db import models

class Shelter(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=10)
    county = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    capacity = models.IntegerField(null=True, blank=True)
    is_pet_friendly = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    shelter_type = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name
