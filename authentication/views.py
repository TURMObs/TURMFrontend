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
