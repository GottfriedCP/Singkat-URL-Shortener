import bs4, re, requests
import datetime

from django.db.models import Sum, Count
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect, get_object_or_404
from .models import Singkat, Clicker, Click, ClickDetail, RandomKeywordId, City, Country, Continent
from .ipstack import get_ipstack_url

def home(request):
    request.session['curr_page'] = 'home'
    return render(request, 'singkat/index.html')

@login_required
def client_area(request):
    request.session['curr_page'] = 'client-area'
    # List all current user's Singkats
    singkat_list = Singkat.objects.filter(owner=request.user).order_by('-created_at', 'keyword').annotate(total_clicks=Sum('click__times'))
    paginator = Paginator(singkat_list, 50, orphans=3)

    page = request.GET.get('page')
    singkats = paginator.get_page(page)

    context = {
        'singkats': singkats,
    }
    return render(request, 'singkat/client-area.html', context)

@login_required
def detail(request, keyword):
    # Get a Singkat object by keyword and current user, or 404 instead
    queryset = Singkat.objects.annotate(total_clicks=Sum('click__times'), unique_clicks=Count('click__times'))
    singkat = get_object_or_404(queryset, keyword=keyword, owner=request.user)
    # List the clickers of this Singkat
    clickers_list = Clicker.objects.filter(click__singkat=singkat).annotate(times=Sum('click__times')).order_by('-click__id')
    paginator = Paginator(clickers_list, 50, orphans=5)

    page = request.GET.get('page')
    clickers = paginator.get_page(page)
    
    # Show total clicks by month using chart
    # First, we populate 12 months data..
    month_clicks = []
    for i in range(0,12):
        month_clicks.append(ClickDetail.objects.filter(click__singkat=singkat, time__month=i+1).count())
    context = {
        'singkat': singkat,
        'clickers': clickers,
        'month_clicks': month_clicks,
    }
    return render(request, 'singkat/singkat-detail.html', context)

@login_required
def create_new_singkat(request):
    """
    Handles the creation of new Singkat object by user.
    Check if the keyword is available and target URL is accessible.
    """
    request.session['curr_page'] = 'client-area'
    if request.method == 'POST':
        target_url = request.POST.get('target_url')
        singkat_keyword = remove_invalid_url_char(request.POST.get('singkat_keyword'))
        try:
            if len(singkat_keyword) == 0: raise ValueError('Minimum keyword length is 1')
            # Is the keyword unique and available?
            if Singkat.objects.filter(keyword=singkat_keyword).count() > 0:
                raise ValueError('Singkat keyword already taken.')
            # Is the target URL a valid URL?
            resp = requests.get(target_url)
            resp.raise_for_status()
            # Is the target url NOT a Singkat object created using this app?
            if target_is_singkat(request, target_url): raise ValueError('This is already a Singkat URL.')
            target_html_title = bs4.BeautifulSoup(resp.text, 'html.parser').title.text
            # Create singkat instance, saving it to database
            singkat = Singkat(
                target=target_url, keyword=singkat_keyword, title=target_html_title, 
                owner=request.user
            )
            singkat.save()
            # Write flash message that new item has been created, then go back to client area
            messages.success(request, 'New Singkat URL has been created and ready to share.')
        except Exception as ex:
            messages.error(request, str(ex))
            return redirect('singkat:create-new')
        return redirect('singkat:client-area')

    # GET request, so show 'create new singkat url' form
    return render(request, 'singkat/create-singkat.html')

def create_new_singkat_rand_keyword(request):
    """
    Handles the creation of anonymous Singkat object. Accepts POST only. 
    """
    if request.method == 'POST':
        target_url = request.POST.get('target_url')
        try:
            # Is the target URL a valid URL?
            resp = requests.get(target_url)
            resp.raise_for_status()
            # Is the target url NOT already a Singkat object created using this app?
            if target_is_singkat(request, target_url): raise ValueError('This is already a Singkat URL.')
            # Create new Singkat object
            singkat = Singkat(
                target=target_url,
                keyword=generate_random_keyword(),
                title=bs4.BeautifulSoup(resp.text, 'html.parser').title.text,
                owner=None if request.user.username == '' else request.user
            )
            singkat.save()
            messages.success(request, '%s/%s' % (request.get_host(), singkat.keyword) )
        except Exception as ex:
            messages.error(request, str(ex))
        return redirect('singkat:home')

def click(request, keyword):
    """
    This function handles every access to Singkat object via valid Singkat URL.
    This will record the clicker details (ip, location) for statistics.
    """
    # Check if keyword is valid
    singkat = get_object_or_404(Singkat, keyword=keyword)
    # Get details on whoever (or whatever) accessed this Singkat URL
    print('Someone clicked a singkat: %s' % str(get_client_ip(request))) # Debug
    resp = requests.get(get_ipstack_url(get_client_ip(request)))
    clicker_data = resp.json()

    ip = clicker_data['ip']
    city = clicker_data.get('city')
    country = clicker_data.get('country_name')
    continent = clicker_data.get('continent_name')
    # Get city, country, and continent from database
    city, country, continent = get_city_country_continent(city, country, continent)
    print('Clicker location: %s, %s, %s' % (city, country, continent)) # Debug
    latitude = 0 if clicker_data.get('latitude') is None else clicker_data.get('latitude')
    longitude = 0 if clicker_data.get('longitude') is None else clicker_data.get('longitude')

    # Check if that IP exists on database, if not, add new Clicker record
    # Else, check if that IP has ever accessed this particular Singkat previously
    if Clicker.objects.filter(ip=ip).count() == 0:
        # Add new clicker to database
        new_clicker = Clicker(
            ip=ip, 
            city=city, country=country, continent=continent,
            latitude=latitude, longitude=longitude
        )
        new_clicker.save()
        # Add new click to database
        new_click = Click(ip=new_clicker, singkat=singkat)
        new_click.save()

        new_click_detail = ClickDetail(click=new_click)
        new_click_detail.save()

        print('This IP is new') # Debug
    else:
        # This clicker already exists
        # Has this clicker accessed this Singkat previously?
        clicker = Clicker.objects.get(ip=ip)
        if Click.objects.filter(ip=clicker, singkat=singkat).count() == 0:
            new_click = Click(ip=clicker, singkat=singkat)
            new_click.save()
            new_click_detail = ClickDetail(click=new_click) # Record current datetime
            new_click_detail.save()
        else:
            click = Click.objects.get(ip=clicker, singkat=singkat)
            # Click count added by one
            click.times += 1
            click.save()
            new_click_detail = ClickDetail(click=click) # Record current datetime
            new_click_detail.save()
        print('This IP already exists') # Debug

    # Debug return
    #return HttpResponse('%s %s %s %s %s %s' % (
    #    ip, city, country_name, continent_name, latitude, longitude)
    #    )
    return redirect(singkat.target)

def click_preview(request, keyword):
    if request.session.get('curr_page') is not None:
        del request.session['curr_page']
    # Check if keyword is valid
    queryset = Singkat.objects.filter(keyword=keyword).annotate(total_clicks=Sum('click__times'))
    singkat = get_object_or_404(queryset)
    #singkat = get_object_or_404(Singkat, keyword=keyword)
    context = {
        'singkat': singkat,
    }
    return render(request, 'singkat/singkat-preview.html', context)


# The view functions below handle REGISTRATION, LOGIN, and LOGOUT

def register(request):
    # Handle the post request first
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        if (password != password2):
            # Show error if passwords don't match
            messages.error(request, "Passwords don't match.")
            return redirect('singkat:register')
        else:
            # Passwords match, so create new user and login
            try:
                validate_password(password) # added password validation
                # Create new user, re-authenticate, then login.
                user = User.objects.create_user(username, email, password)
                user.save()
                user = authenticate(request, username=username, password=password)
                login(request, user)
            except Exception as ex:
                messages.error(request, str(ex))
                return redirect('singkat:register')
        return redirect('singkat:home')

    # GET request, show registration form
    request.session['curr_page'] = 'register'
    return render(request, 'singkat/register.html')

def login_view(request):
    # Prevent user to access this page (they already logged-in)
    if request.user.is_authenticated:
        return redirect('singkat:home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
        else:
            # Show error that user is not found
            messages.error(request, "Username or password doesn't match.")
            return redirect('singkat:login')
        return redirect('singkat:client-area')
    
    # GET request, show login form
    request.session['curr_page'] = 'login'
    return render(request, 'singkat/login.html')

def logout_view(request):
    # Logout and redirect to homepage
    logout(request)
    return redirect('singkat:home')


# Helper functions

def remove_invalid_url_char(kw):
    """
    Ensure valid chars in URL, based on RFC 1738 (without apostrophe and plus).
    Total 71 (63+8) chars allowed.
    """
    kw = re.sub('[^\w\$\-\.\!\*\(\)\,]', '', kw.strip())
    return kw

def target_is_singkat(r, kw):
    """Check whether proposed keyword is already taken."""
    # TODO: this is probably not the best way to check singkat keyword already in database..
    kw = re.sub('http://', '', kw)
    kw = re.sub('https://', '', kw)
    kw = re.sub(str(r.get_host()), '', kw)
    kw = re.sub('\/', '', kw)
    kw = re.sub('\+', '', kw)
    return Singkat.objects.filter(keyword=kw).count() > 0

def get_client_ip(rq):
    """Try to get client's real IP address."""
    x_forwarded_for = rq.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')
        ip = ip[-1]
    else:
        ip = rq.META.get('REMOTE_ADDR')
    return ip

def get_city_country_continent(city, country, continent):
    """Get id of city, country, and continent from database."""
    if city is not None:
        if City.objects.filter(name=city).count() == 0:
            # Create new city object if not already in database
            city = City(name=city)
            city.save()
        else:
            city = City.objects.get(name=city)
    if country is not None:
        if Country.objects.filter(name=country).count() == 0:
            country = Country(name=country)
            country.save()
        else:
            country = Country.objects.get(name=country)
    if continent is not None:
        if Continent.objects.filter(name=continent).count() == 0:
            continent = Continent(name=continent)
            continent.save()
        else:
            continent = Continent.objects.get(name=continent)

    return city, country, continent

def generate_random_keyword():
    rk = RandomKeywordId.objects.get(id=1)
    ALPHABET = (
        '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 
        'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 
        'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z')
    while True:
        n = rk.get_new_value()
        time1 = datetime.datetime.now() # DEBUG
        digits = []
        while n:
            digits.append(int(n%62))
            n //= 62
        digits = digits[::-1]
        #print(digits)
        for idx, val in enumerate(digits):
            digits[idx] = ALPHABET[val]
        keyword = ''.join(digits)
        # Break loop if keyword is available
        time2 = datetime.datetime.now() # DEBUG
        print('KEYWORD BUILD TIME: %s' % ((time2 - time1).total_seconds())) # DEBUG
        if Singkat.objects.filter(keyword=keyword).count() == 0:
            break
    return keyword
