import json
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from orders.models import Order, OrderItem
import hashlib
from django.shortcuts import render
from django.utils import timezone
from .forms import DishForm
from .models import Dish, Shop


def customer_menu_view(request):
    query = request.GET.get('q', '').strip()

    base_available = Dish.objects.filter(
        is_available=True,
        shop__is_active=True,
        shop__owner__approval_status='APPROVED',
    ).select_related('shop')

    # 1. New Update: newest 3 available dishes across the platform
    new_update_dishes = list(base_available.order_by('-created_at')[:3])

    # 2. Recommended: one consistent dish per day for all users
    recommended_dish = None
    all_for_rec = list(base_available.order_by('id'))
    if all_for_rec:
        today_key = timezone.localdate().isoformat().encode('utf-8')
        digest_int = int(hashlib.sha256(today_key).hexdigest(), 16)
        recommended_dish = all_for_rec[digest_int % len(all_for_rec)]

    # 3. All Available: filter by search query if provided, then randomize order
    all_available_dishes = base_available
    if query:
        all_available_dishes = all_available_dishes.filter(
            name__icontains=query
        ) | all_available_dishes.filter(
            shop__name__icontains=query
        )

    all_available_dishes = all_available_dishes.order_by('?')

    return render(request, 'shops/customer_menu.html', {
        'new_update_dishes': new_update_dishes,
        'recommended_dish': recommended_dish,
        'all_available_dishes': all_available_dishes,
        'query': query,
    })

@login_required
def owner_dashboard_view(request):
    if request.user.role != 'SHOP_OWNER':
        messages.error(request, 'Access restricted to Shop Owners.')
        return redirect('accounts:role_redirect')

    shop = get_object_or_404(Shop, owner=request.user)
    if request.user.approval_status != 'APPROVED':
        return render(request, 'shops/pending_approval.html', {'shop': shop})

    if request.method == 'POST':
        dish_form = DishForm(request.POST, request.FILES)
        if dish_form.is_valid():
            dish = dish_form.save(commit=False)
            dish.shop = shop
            dish.save()
            messages.success(request, f'"{dish.name}" added to your menu.')
            return redirect('shops:owner_dashboard')
    else:
        dish_form = DishForm()

    valid_orders = Order.objects.filter(shop=shop).exclude(status=Order.Status.CANCELLED)
    total_sales = valid_orders.aggregate(total=Sum('subtotal'))['total'] or 0
    plates_sold = (
        OrderItem.objects.filter(order__in=valid_orders).aggregate(qty=Sum('quantity'))['qty'] or 0
    )
    customer_pickups_count = valid_orders.filter(fulfillment_type=Order.FulfillmentType.PICKUP).count()
    dispatch_pickups_count = valid_orders.filter(fulfillment_type=Order.FulfillmentType.DELIVERY).count()

    today = timezone.localdate()
    labels = []
    sales_series = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        day_total = (
            valid_orders.filter(created_at__date=day).aggregate(total=Sum('subtotal'))['total'] or 0
        )
        labels.append(day.strftime('%a'))
        sales_series.append(float(day_total))

    dishes = shop.dishes.order_by('-created_at')

    return render(request, 'shops/owner_dashboard.html', {
        'shop': shop,
        'dish_form': dish_form,
        'dishes': dishes,
        'total_sales': total_sales,
        'plates_sold': plates_sold,
        'customer_pickups_count': customer_pickups_count,
        'dispatch_pickups_count': dispatch_pickups_count,
        'chart_labels_json': json.dumps(labels),
        'chart_sales_json': json.dumps(sales_series),
    })


@login_required
def delete_dish_view(request, dish_id):
    shop = get_object_or_404(Shop, owner=request.user)
    dish = get_object_or_404(Dish, id=dish_id, shop=shop)
    if request.method == 'POST':
        dish.delete()
        messages.success(request, 'Dish removed from menu.')
    return redirect('shops:owner_dashboard')

@login_required
def toggle_dish_availability_view(request, dish_id):
    if request.user.role != 'SHOP_OWNER':
        messages.error(request, 'Access restricted to Shop Owners.')
        return redirect('accounts:role_redirect')

    shop = get_object_or_404(Shop, owner=request.user)
    dish = get_object_or_404(Dish, id=dish_id, shop=shop)
    if request.method == 'POST':
        dish.is_available = not dish.is_available
        dish.save(update_fields=['is_available'])
        state_text = 'Available on the menu' if dish.is_available else 'Unavailable (hidden from menu)'
        messages.success(request, f'"{dish.name}" is now {state_text}.')
    return redirect('shops:owner_dashboard')


@login_required
def edit_dish_view(request, dish_id):
    if request.user.role != 'SHOP_OWNER':
        messages.error(request, 'Access restricted to Shop Owners.')
        return redirect('accounts:role_redirect')

    shop = get_object_or_404(Shop, owner=request.user)
    dish = get_object_or_404(Dish, id=dish_id, shop=shop)

    if request.method == 'POST':
        form = DishForm(request.POST, request.FILES, instance=dish)
        if form.is_valid():
            form.save()
            messages.success(request, f'"{dish.name}" updated successfully.')
            return redirect('shops:owner_dashboard')
    else:
        form = DishForm(instance=dish)

    return render(request, 'shops/edit_dish.html', {
        'shop': shop,
        'dish': dish,
        'form': form,
    })