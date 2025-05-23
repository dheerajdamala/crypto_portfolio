from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from .models import Profile, Transaction, WatchlistItem
import requests
import locale
from django.http import JsonResponse, HttpResponse
from uuid import uuid4
from django.core.paginator import Paginator
from datetime import datetime
import csv
import xlsxwriter
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# Constants
API_KEY = 'coinranking8948cf17738f206290e9fd47c8c0db0c4485eea46c82b24f'
BASE_URL = 'https://api.coinranking.com/v2'
HEADERS = {'x-access-token': API_KEY}
REQUEST_TIMEOUT = 10  # Adding a timeout value (seconds) for API requests

locale.setlocale(locale.LC_ALL, '')

def format_currency(value):
    try:
        return f"{float(value):,.2f}"
    except:
        return "0.00"

def get_or_create_profile(user):
    profile, created = Profile.objects.get_or_create(user=user, defaults={'balance': 0.0})
    return profile

def dashboard(request):
    try:
        url = f"{BASE_URL}/coins"
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        data = response.json()
        coins = data.get('data', {}).get('coins', [])

        currency = request.session.get('currency', 'USD')
        conversion_rate = 83.5 if currency == 'INR' else 1
        currency_symbol = '₹' if currency == 'INR' else '$'

        for coin in coins:
            try:
                coin['change'] = float(coin.get('change', 0))
                coin['price'] = float(coin.get('price', 0))
                coin['price_converted'] = round(coin['price'] * conversion_rate, 4)
                coin['marketCap'] = format_currency(float(coin.get('marketCap', 0)) * conversion_rate)
                coin['24hVolume'] = format_currency(float(coin.get('24hVolume', 0)) * conversion_rate)
            except:
                coin['change'] = 0.0
                coin['price'] = 0.0
                coin['price_converted'] = 0.0
                coin['marketCap'] = "0.00"
                coin['24hVolume'] = "0.00"

        context = {
            'coins': coins,
            'currency': currency,
            'currency_symbol': currency_symbol,
        }

        if request.user.is_authenticated:
            profile = get_or_create_profile(request.user)
            converted_balance = round(profile.balance * conversion_rate, 2)
            context['profile'] = profile
            context['balance'] = format_currency(converted_balance)
            context['watchlist_uuids'] = [item.uuid for item in WatchlistItem.objects.filter(user=request.user)]

        return render(request, 'tracker/dashboard.html', context)

    except requests.exceptions.Timeout:
        messages.error(request, "API request timed out. Please try again later.")
    except Exception as e:
        messages.error(request, f"Error fetching data: {str(e)}")

    # fallback context for API errors
    currency = request.session.get('currency', 'USD')
    currency_symbol = '₹' if currency == 'INR' else '$'
    context = {
        'coins': [],
        'currency': currency,
        'currency_symbol': currency_symbol,
        'api_error': True
    }

    if request.user.is_authenticated:
        profile = get_or_create_profile(request.user)
        context['profile'] = profile
        context['balance'] = format_currency(round(profile.balance * (83.5 if currency == 'INR' else 1), 2))
        context['watchlist_uuids'] = []

    return render(request, 'tracker/dashboard.html', context)


def toggle_currency(request):
    current_currency = request.session.get('currency', 'USD')
    request.session['currency'] = 'INR' if current_currency == 'USD' else 'USD'
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('register')

        user = User.objects.create_user(username=username, email=email, password=password1)
        Profile.objects.create(user=user, balance=0.0)
        messages.success(request, "Account created successfully! Please log in.")
        return redirect('login')
    return render(request, 'tracker/register.html')

def login_view(request):
    if request.method == 'POST':
        user = authenticate(request, username=request.POST['username'], password=request.POST['password'])
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid credentials.')
            # Add this line to handle failed login attempts
            return render(request, 'tracker/login.html')

    return render(request, 'tracker/login.html')



def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def profile(request):
    profile = get_or_create_profile(request.user)
    currency = request.session.get('currency', 'USD')
    conversion_rate = 83.5 if currency == 'INR' else 1

    context = {
        'profile': profile,
        'currency': currency,
        'currency_symbol': '₹' if currency == 'INR' else '$',
        'balance_converted': format_currency(profile.balance * conversion_rate)
    }
    return render(request, 'tracker/profile.html', context)

@login_required
def add_money(request):
    if request.method == 'POST':
        try:
            amount = float(request.POST['amount'])
            profile = get_or_create_profile(request.user)
            profile.balance += amount
            profile.save()

            currency = request.session.get('currency', 'USD')
            symbol = '₹' if currency == 'INR' else '$'
            messages.success(request, f'Added {symbol}{format_currency(amount)} to wallet!')
        except:
            messages.error(request, "Invalid amount.")
        return redirect('profile')
    return render(request, 'tracker/add_money.html')

@login_required
def buy_crypto(request):
    if request.method == 'POST':
        symbol = request.POST['symbol'].upper()
        quantity = float(request.POST['quantity'])
        
        try:
            # Fetch coin data
            response = requests.get(f'{BASE_URL}/coins', headers=HEADERS, timeout=REQUEST_TIMEOUT)
            coins = response.json()['data']['coins']
            coin_data = next((coin for coin in coins if coin['symbol'].upper() == symbol), None)
            
            if not coin_data:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': f"Coin with symbol '{symbol}' not found."})
                messages.error(request, f"Coin with symbol '{symbol}' not found.")
                return redirect('dashboard')
                
            price = float(coin_data['price'])
            total_cost = price * quantity
            uuid = coin_data['uuid']
            
            profile = get_or_create_profile(request.user)
            
            if profile.balance >= total_cost:
                profile.balance -= total_cost
                profile.save()
                
                Transaction.objects.create(
                    user=request.user,
                    symbol=symbol,
                    uuid=uuid,
                    amount=quantity,
                    price=price,
                    type='buy'
                )
                
                currency = request.session.get('currency', 'USD')
                conversion_rate = 83.5 if currency == 'INR' else 1
                symbol_display = '₹' if currency == 'INR' else '$'
                formatted_cost = format_currency(total_cost * conversion_rate)
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    # Return success for AJAX requests - the client will reload the page
                    return JsonResponse({
                        'success': True,
                        'message': f"Bought {quantity} {symbol} for {symbol_display}{formatted_cost}"
                    })
                    
                messages.success(request, f"Bought {quantity} {symbol} for {symbol_display}{formatted_cost}")
                return redirect('portfolio')
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': "Insufficient balance."})
                messages.error(request, "Insufficient balance.")
        except requests.exceptions.Timeout:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': "API request timed out. Please try again."})
            messages.error(request, "API request timed out. Please try again.")
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)})
            messages.error(request, f"Transaction failed. Error: {str(e)}")
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': "Invalid request"})
    return redirect('dashboard')

@login_required
def sell_crypto(request):
    if request.method == 'POST':
        symbol = request.POST.get('symbol')
        
        # Add debugging to check if symbol is being received
        print(f"POST data received: {request.POST}")
        print(f"Symbol received: '{symbol}'")
        
        if not symbol:
            messages.error(request, "Symbol is required")
            return redirect('portfolio')
            
        quantity = float(request.POST.get('quantity', 0))
        
        # Get the user's portfolio data to find the UUID for this symbol
        transactions = Transaction.objects.filter(user=request.user, symbol=symbol)
        
        if not transactions.exists():
            messages.error(request, f"No transactions found for {symbol}")
            return redirect('portfolio')
            
        # Get the UUID from the first transaction (all transactions for this symbol should have the same UUID)
        uuid = transactions.first().uuid
        
        # Calculate available quantity
        buy_transactions = transactions.filter(type='buy')
        sell_transactions = transactions.filter(type='sell')
        
        total_buy_quantity = sum(t.amount for t in buy_transactions)
        total_sell_quantity = sum(t.amount for t in sell_transactions)
        available_quantity = total_buy_quantity - total_sell_quantity
        
        # Check if user has enough of this crypto to sell
        if available_quantity < quantity:
            messages.error(request, f"Not enough {symbol} to sell. You have {available_quantity}.")
            return redirect('portfolio')
        
        # Get current price
        try:
            # Get price by UUID since that's how the API works
            response = requests.get(f'{BASE_URL}/coins?uuids={uuid}', headers=HEADERS, timeout=REQUEST_TIMEOUT)
            coin_data = response.json()['data']['coins'][0]
            current_price = float(coin_data['price'])
            
            # Create a sell transaction
            transaction = Transaction(
                user=request.user,
                type='sell',
                symbol=symbol,
                uuid=uuid,
                amount=quantity,
                price=current_price
            )
            transaction.save()
            
            # Update user balance
            profile = get_or_create_profile(request.user)
            sell_value = quantity * current_price
            profile.balance += sell_value
            profile.save()
            
            messages.success(request, f"Successfully sold {quantity} {symbol} for ${sell_value:.2f}")
        except Exception as e:
            messages.error(request, f"Error selling {symbol}: {str(e)}")
        
        return redirect('portfolio')
    
    return redirect('portfolio')

@login_required
def portfolio(request):
    currency = request.session.get('currency', 'USD')
    conversion_rate = 83.5 if currency == 'INR' else 1
    currency_symbol = '₹' if currency == 'INR' else '$'
    
    transactions = Transaction.objects.filter(user=request.user)
    portfolio_data = {}
    
    for transaction in transactions:
        if transaction.uuid not in portfolio_data:
            portfolio_data[transaction.uuid] = {
                'symbol': transaction.symbol,
                'uuid': transaction.uuid,
                'quantity': 0,
                'total_buy_price': 0,
                'transactions': [],
            }
        portfolio_data[transaction.uuid]['transactions'].append(transaction)
    
    for item in portfolio_data.values():
        buy_transactions = [t for t in item['transactions'] if t.type == 'buy']
        sell_transactions = [t for t in item['transactions'] if t.type == 'sell']
        
        total_buy_quantity = sum(t.amount for t in buy_transactions)
        total_sell_quantity = sum(t.amount for t in sell_transactions)
        item['quantity'] = round(total_buy_quantity - total_sell_quantity, 2)
        
        if item['quantity'] > 0:
            item['total_buy_price'] = round(sum(t.amount * t.price for t in buy_transactions), 2)
            item['avg_buy_price'] = round(item['total_buy_price'] / total_buy_quantity, 2)
        else:
            item['avg_buy_price'] = 0
    
    portfolio = []
    for uuid, item in portfolio_data.items():
        if item['quantity'] > 0:
            try:
                response = requests.get(f'{BASE_URL}/coins?uuids={uuid}', headers=HEADERS, timeout=REQUEST_TIMEOUT)
                coin_data = response.json()['data']['coins'][0]
                
                # Create a coin object structure to match the template expectations
                item['coin'] = {
                    'name': coin_data['name'],
                    'symbol': item['symbol'],  # Use the symbol from the transaction
                    'image_url': coin_data.get('iconUrl')
                }
                
                item['current_price'] = round(float(coin_data['price']), 2)
                item['profit_loss'] = round((item['current_price'] - item['avg_buy_price']) * item['quantity'], 2)
                item['profit_loss_percent'] = round((item['profit_loss'] / item['total_buy_price']) * 100 if item['total_buy_price'] else 0, 2)
                item['is_profit'] = item['profit_loss'] > 0
                portfolio.append(item)
            except Exception as e:
                # Add logging for debugging
                print(f"Error fetching coin data: {str(e)}")
                pass
    
    total_value = round(sum(item['current_price'] * item['quantity'] for item in portfolio), 2)
    total_profit_loss = round(sum(item['profit_loss'] for item in portfolio), 2)
    total_buy_value = round(sum(item['total_buy_price'] for item in portfolio), 2)
    total_profit_loss_percent = round((total_profit_loss / total_buy_value) * 100 if total_buy_value else 0, 2)
    is_total_profit = total_profit_loss > 0
    
    profile = get_or_create_profile(request.user)
    balance = round(profile.balance * conversion_rate, 2)
    
    context = {
        'portfolio': portfolio,
        'currency': currency,
        'currency_symbol': currency_symbol,
        'total_value': format_currency(total_value),
        'total_profit_loss': format_currency(total_profit_loss),
        'total_profit_loss_percent': format_currency(total_profit_loss_percent),
        'is_total_profit': is_total_profit,
        'balance': format_currency(balance),
    }
    
    return render(request, 'tracker/portfolio.html', context)
@login_required
def watchlist(request):
    items = WatchlistItem.objects.filter(user=request.user)
    coins = []

    currency = request.session.get('currency', 'USD')
    conversion_rate = 83.5 if currency == 'INR' else 1
    currency_symbol = '₹' if currency == 'INR' else '$'
    
    api_error = False

    for item in items:
        try:
            response = requests.get(f'{BASE_URL}/coin/{item.uuid}', headers=HEADERS, timeout=REQUEST_TIMEOUT)
            coin = response.json()['data']['coin']
            coin['price'] = float(coin['price']) * conversion_rate
            coin['marketCap'] = format_currency(float(coin.get('marketCap', 0)) * conversion_rate)
            coin['24hVolume'] = format_currency(float(coin.get('24hVolume', 0)) * conversion_rate)
            coins.append(coin)
        except requests.exceptions.Timeout:
            api_error = True
        except Exception as e:
            print(f"Error fetching watchlist item {item.uuid}: {str(e)}")
            continue

    if api_error:
        messages.warning(request, "Some coins could not be loaded due to API timeout.")

    return render(request, 'tracker/watchlist.html', {
        'coins': coins,
        'profile': get_or_create_profile(request.user),
        'watchlist_uuids': [item.uuid for item in items],
        'currency': currency,
        'currency_symbol': currency_symbol,
        'api_error': api_error
    })

@login_required
def transaction_history(request):
    # Fetch all transactions for the logged-in user
    transactions = Transaction.objects.filter(user=request.user).order_by('-timestamp')

    # Apply filters if present in query params
    type_filter = request.GET.get('type')
    status_filter = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    search_query = request.GET.get('search')

    if type_filter and type_filter != 'all':
        transactions = transactions.filter(type=type_filter)
    if status_filter and status_filter != 'all':
        transactions = transactions.filter(status=status_filter)
    if date_from:
        transactions = transactions.filter(timestamp__gte=date_from)
    if date_to:
        transactions = transactions.filter(timestamp__lte=date_to)
    if search_query:
        transactions = transactions.filter(
            Q(symbol__icontains=search_query) | 
            Q(type__icontains=search_query)
        )

    # Pagination setup
    paginator = Paginator(transactions, 10)  # Show 10 transactions per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Summary calculations
    total_transactions = transactions.count()
    total_buy_amount = sum(txn.amount for txn in transactions if txn.type == 'buy')
    total_sell_amount = sum(txn.amount for txn in transactions if txn.type == 'sell')
    total_deposits = sum(txn.amount for txn in transactions if txn.type == 'deposit')

    # Currency conversion rate (assuming session-based currency toggle)
    currency = request.session.get('currency', 'USD')
    conversion_rate = 83.5 if currency == 'INR' else 1
    currency_symbol = '₹' if currency == 'INR' else '$'

    context = {
        'transactions': page_obj,
        'total_transactions': total_transactions,
        'total_buy_amount': total_buy_amount * conversion_rate,
        'total_sell_amount': total_sell_amount * conversion_rate,
        'total_deposits': total_deposits * conversion_rate,
        'balance': get_or_create_profile(request.user).balance * conversion_rate,
        'currency': currency,
        'currency_symbol': currency_symbol,
        'messages': messages.get_messages(request),
    }

    return render(request, 'tracker/transaction_history.html', context)
    
@login_required
def add_to_watchlist(request, uuid):
    if not WatchlistItem.objects.filter(user=request.user, uuid=uuid).exists():
        WatchlistItem.objects.create(user=request.user, uuid=uuid)
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))


@login_required
def remove_from_watchlist(request, uuid):
    WatchlistItem.objects.filter(user=request.user, uuid=uuid).delete()
    messages.success(request, "Removed from watchlist.")
    return redirect('watchlist')