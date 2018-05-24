from django.contrib.auth.models import User
from django.db import models

class Singkat(models.Model):
    """
    This class represented 'singkat' model: a URL shortened by name or unique id.

    Fields:
    - target   : original URL
    - keyword : singkat (shortened) URL keyword
    - title    : the title tag value of HTML page
    - owner : the user this singkat belongs to
    - created_at
    """
    keyword = models.CharField(max_length=100, unique=True, blank=False, null=False)
    target = models.URLField(max_length=2000)
    title = models.CharField(max_length=100, blank=True)
    owner = models.ForeignKey(User, related_name='singkats', on_delete=models.CASCADE, null=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    def save(self):
        """Write instance to database."""
        super(Singkat, self).save()

    def __str__(self):
        """Return human readable representation of model instance."""
        return self.keyword

class Clicker(models.Model):
    """
    This class records every IP address that accessed a Singkat URL.

    Fields:
    - ip (ipv4/ipv6)
    - city (e.g Jakarta)
    - country (e.g Indonesia)
    - continent (e.g Asia)
    - latitude
    - longitude
    """
    ip = models.GenericIPAddressField(unique=True)
    city = models.ForeignKey('City', on_delete=models.CASCADE, null=True)
    country = models.ForeignKey('Country', on_delete=models.CASCADE, null=True)
    continent = models.ForeignKey('Continent', on_delete=models.CASCADE, null=True)
    latitude = models.FloatField(default=0)
    longitude = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    def __str__(self):
        """Return human-readable representation of model instance."""
        return '%s' % (self.ip)

class Click(models.Model):
    """
    Intermediate model to facilitate M-N relationship of Singkat and Clicker.
    """
    ip = models.ForeignKey(Clicker, on_delete=models.CASCADE)
    singkat = models.ForeignKey(Singkat, on_delete=models.CASCADE)
    times = models.PositiveIntegerField(default=1)

class ClickDetail(models.Model):
    """
    Clicks from one IP address will be recorded in this class.
    
    Fields:
    - click : related Click instance
    - time  : datetime format
    """
    click = models.ForeignKey(Click, related_name='details', on_delete=models.CASCADE)
    time = models.DateTimeField(auto_now_add=True, editable=False)

    def __str__(self):
        return str(self.time)

class City(models.Model):
    name = models.CharField(max_length=150, unique=True)

    def __str__(self):
        return self.name

class Country(models.Model):
    name = models.CharField(max_length=150, unique=True)

    def __str__(self):
        return self.name

class Continent(models.Model):
    name = models.CharField(max_length=150, unique=True)

    def __str__(self):
        return self.name

class RandomKeywordId(models.Model):
    value = models.BigIntegerField(default=1)

    def __str__(self):
        return str(self.value)

    def get_new_value(self):
        self.value += 1
        super(RandomKeywordId, self).save()
        return self.value - 1
