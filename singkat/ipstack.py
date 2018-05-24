from django.conf import settings

# IPStack Configuration

# Use it like this:
# GET '%scheck%s' % (IPSTACK_BASE_URL, IPSTACK_APIKEY)
# notice the url param 'check'

IPSTACK_BASE_URL = 'http://api.ipstack.com/'
IPSTACK_APIKEY = '?access_key=%s' % settings.IPSTACK_APIKEY

def get_ipstack_url(ip):
    """Return the ready-to-use ipstack api url."""
    return '%s%s%s' % (IPSTACK_BASE_URL, ip, IPSTACK_APIKEY)
