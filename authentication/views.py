from django.shortcuts import render
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect

def index(request):
    # The user clicked on login
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('index')
        else:
            return render(request, 'authentication/index.html', {'error': 'Invalid username or password'})
    else:
        return render(request, 'authentication/index.html')

def generate_invitation_link(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        link = generate_url(email)
        return render(request, 'authentication/generate_invitation_link.html', {'link': link})
    return render(request, 'authentication/generate_invitation_link.html')

def generate_url(email):
    return f"https://example.com/invitation/{email}"
