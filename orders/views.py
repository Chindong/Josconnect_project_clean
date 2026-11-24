import json
from datetime import timedelta
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from accounts.forms import StaffCreateForm
from accounts.models import User
from feedback_app.models import Feedback
from shops.models import Dish, Shop
from .models import Order, OrderItem

DEFAULT_DELIVERY_FEE = Decimal('500.00')
DEFAULT_RIDER_FEE = Decimal('400.00')


@login_required
def add_to_cart_view(request, dish_id):
    if not _is_customer(request.user):
        messages.error(request, 'Only Customer accounts can add dishes to a cart or place orders.')
        return redirect('accounts:role_redirect')

    dish = get_object_or_404(Dish, id=dish_id, is_available=True)
    cart = request.session.get('cart', {})
    key = str(dish.id)

    if key in cart:
        cart[key]['quantity'] += 1
    else:
        cart[key] = {
            'dish_id': dish.id,
            'shop_id': dish.shop.id,
            'name': dish.name,
            'shop_name': dish.shop.name,
            'price': str(dish.price),
            'quantity': 1,
        }

    request.session['cart'] = cart
    request.session.modified = True
    messages.success(request, f'Added "{dish.name}" to your cart.')
    return redirect('orders:cart_checkout')

@login_required
def cart_checkout_view(request):
    if not _is_customer(request.user):
        messages.error(request, 'Only Customer accounts can access cart checkout.')
        return redirect('accounts:role_redirect')

    cart = request.session.get('cart', {})
    items = []
    subtotal = Decimal('0.00')

    for item in cart.values():
        price = Decimal(item['price'])
        qty = int(item['quantity'])
        line_total = price * qty
        subtotal += line_total
        items.append({
            'dish_id': item['dish_id'],
            'shop_id': item['shop_id'],
            'name': item['name'],
            'shop_name': item['shop_name'],
            'price': price,
            'quantity': qty,
            'line_total': line_total,
        })

    if request.method == 'POST':
        if not items:
            messages.error(request, 'Your cart is empty.')
            return redirect('shops:customer_menu')

        fulfillment_type = request.POST.get('fulfillment_type', Order.FulfillmentType.DELIVERY)
        delivery_address = request.POST.get('delivery_address', '').strip()

        if fulfillment_type == Order.FulfillmentType.DELIVERY and not delivery_address:
            messages.error(request, 'Please enter a delivery address for Delivery orders.')
            return render(request, 'orders/cart_checkout.html', {
                'items': items,
                'subtotal': subtotal,
                'delivery_fee': DEFAULT_DELIVERY_FEE,
            })

        grouped_by_shop = {}
        for row in items:
            grouped_by_shop.setdefault(row['shop_id'], []).append(row)

        with transaction.atomic():
            for shop_id, shop_items in grouped_by_shop.items():
                shop = get_object_or_404(Shop, id=shop_id)
                shop_subtotal = sum(i['line_total'] for i in shop_items)
                fee = DEFAULT_DELIVERY_FEE if fulfillment_type == Order.FulfillmentType.DELIVERY else Decimal('0.00')
                rider_fee = DEFAULT_RIDER_FEE if fulfillment_type == Order.FulfillmentType.DELIVERY else Decimal('0.00')

                order = Order.objects.create(
                    customer=request.user,
                    shop=shop,
                    fulfillment_type=fulfillment_type,
                    delivery_address=delivery_address if fulfillment_type == Order.FulfillmentType.DELIVERY else 'Shop Pickup',
                    subtotal=shop_subtotal,
                    delivery_fee=fee,
                    rider_earning=rider_fee,
                    total_amount=shop_subtotal + fee,
                )

                for row in shop_items:
                    dish_obj = get_object_or_404(Dish, id=row['dish_id'])
                    OrderItem.objects.create(
                        order=order,
                        dish=dish_obj,
                        quantity=row['quantity'],
                        unit_price=dish_obj.price,
                    )

        request.session['cart'] = {}
        request.session.modified = True
        messages.success(request, 'Order placed successfully!')
        return redirect('orders:my_orders')

    return render(request, 'orders/cart_checkout.html', {
        'items': items,
        'subtotal': subtotal,
        'delivery_fee': DEFAULT_DELIVERY_FEE,
    })

@login_required
def my_orders_view(request):
    if not _is_customer(request.user):
        messages.error(request, 'Only Customer accounts have customer order history.')
        return redirect('accounts:role_redirect')

    orders = Order.objects.filter(customer=request.user).select_related('shop', 'rider').order_by('-created_at')
    return render(request, 'orders/my_orders.html', {'orders': orders})


@login_required
def rider_dashboard_view(request):
    if request.user.role != 'RIDER':
        messages.error(request, 'Access restricted to Dispatch Riders.')
        return redirect('accounts:role_redirect')

    if request.user.approval_status != 'APPROVED':
        return render(request, 'orders/rider_pending.html')

    available_orders = Order.objects.filter(
        fulfillment_type=Order.FulfillmentType.DELIVERY,
        rider__isnull=True,
        status__in=[Order.Status.PENDING, Order.Status.ACCEPTED, Order.Status.READY],
    ).select_related('shop', 'customer').order_by('-created_at')

    my_deliveries = Order.objects.filter(rider=request.user).select_related('shop', 'customer').order_by('-created_at')
    completed_deliveries = my_deliveries.filter(status=Order.Status.COMPLETED)

    total_deliveries_count = completed_deliveries.count()
    total_earnings = completed_deliveries.aggregate(total=Sum('rider_earning'))['total'] or 0

    today = timezone.localdate()
    labels = []
    progress_series = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        day_count = completed_deliveries.filter(created_at__date=day).count()
        labels.append(day.strftime('%a'))
        progress_series.append(day_count)

    return render(request, 'orders/rider_dashboard.html', {
        'available_orders': available_orders,
        'my_deliveries': my_deliveries,
        'total_deliveries_count': total_deliveries_count,
        'total_earnings': total_earnings,
        'chart_labels_json': json.dumps(labels),
        'chart_progress_json': json.dumps(progress_series),
    })


@login_required
def rider_update_order_view(request, order_id, action):
    if request.user.role != 'RIDER' or request.user.approval_status != 'APPROVED':
        return redirect('accounts:role_redirect')

    order = get_object_or_404(Order, id=order_id, fulfillment_type=Order.FulfillmentType.DELIVERY)
    if request.method == 'POST':
        if action == 'claim' and order.rider is None:
            order.rider = request.user
            order.status = Order.Status.DISPATCHED
            order.save()
            messages.success(request, f'Picked up Order #{order.id} for delivery.')
        elif action == 'complete' and order.rider == request.user:
            order.status = Order.Status.COMPLETED
            order.save()
            messages.success(request, f'Order #{order.id} marked as Completed.')
    return redirect('orders:rider_dashboard')


@login_required
def admin_dashboard_view(request):
    if not request.user.has_management_access:
        messages.error(request, 'Access restricted to management staff.')
        return redirect('accounts:role_redirect')

    staff_form = StaffCreateForm()
    if request.method == 'POST' and 'create_staff' in request.POST:
        if not request.user.is_project_owner:
            messages.error(request, 'Only the Project Owner can create staff accounts.')
            return redirect('orders:admin_dashboard')
        staff_form = StaffCreateForm(request.POST)
        if staff_form.is_valid():
            staff_user = staff_form.save()
            messages.success(request, f'Employed staff account created for "{staff_user.username}".')
            return redirect('orders:admin_dashboard')

    today = timezone.localdate()
    daily_requests = Order.objects.filter(created_at__date=today).count()
    daily_dispatches = Order.objects.filter(
        created_at__date=today,
        fulfillment_type=Order.FulfillmentType.DELIVERY,
    ).exclude(status=Order.Status.CANCELLED).count()
    total_revenue = (
        Order.objects.exclude(status=Order.Status.CANCELLED).aggregate(total=Sum('total_amount'))['total'] or 0
    )

    pending_registrations = User.objects.filter(
        role__in=[User.Role.SHOP_OWNER, User.Role.RIDER],
        approval_status=User.ApprovalStatus.PENDING,
    ).order_by('-date_joined')

    all_dishes = Dish.objects.select_related('shop', 'shop__owner').order_by('-created_at')
    all_feedback = Feedback.objects.select_related('user').order_by('-created_at')
    managed_users = User.objects.exclude(id=request.user.id).order_by('-date_joined')
    employed_staff = User.objects.filter(role=User.Role.MODERATOR).order_by('-date_joined')

    return render(request, 'orders/admin_dashboard.html', {
        'daily_requests': daily_requests,
        'daily_dispatches': daily_dispatches,
        'total_revenue': total_revenue,
        'pending_registrations': pending_registrations,
        'all_dishes': all_dishes,
        'all_feedback': all_feedback,
        'managed_users': managed_users,
        'employed_staff': employed_staff,
        'staff_form': staff_form,
        'is_project_owner': request.user.is_project_owner,
    })


@login_required
def admin_approve_user_view(request, user_id, decision):
    if not request.user.has_management_access:
        return redirect('accounts:role_redirect')

    target_user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        if decision == 'accept':
            target_user.approval_status = User.ApprovalStatus.APPROVED
            target_user.save()
            messages.success(request, f'{target_user.username} has been approved.')
        elif decision == 'reject':
            target_user.approval_status = User.ApprovalStatus.REJECTED
            target_user.save()
            messages.warning(request, f'{target_user.username} registration was rejected.')
    return redirect('orders:admin_dashboard')


@login_required
def admin_delete_user_view(request, user_id):
    if not request.user.is_project_owner:
        messages.error(request, 'Only the Project Owner can delete user or staff profiles.')
        return redirect('orders:admin_dashboard')

    target_user = get_object_or_404(User, id=user_id)
    if request.method == 'POST' and target_user.id != request.user.id:
        username = target_user.username
        target_user.delete()
        messages.success(request, f'Profile "{username}" has been deleted.')
    return redirect('orders:admin_dashboard')

def _is_customer(user):
    return user.is_authenticated and not user.is_superuser and user.role == User.Role.CUSTOMER


@login_required
def track_order_view(request, order_id):
    order = get_object_or_404(Order.objects.select_related('shop', 'customer', 'rider'), id=order_id)

    is_order_customer = (order.customer_id == request.user.id)
    is_order_rider = (order.rider_id == request.user.id)
    is_manager = getattr(request.user, 'has_management_access', False)

    if not (is_order_customer or is_order_rider or is_manager):
        messages.error(request, 'You do not have permission to view tracking for this order.')
        return redirect('accounts:role_redirect')

    return render(request, 'orders/track_order.html', {
        'order': order,
        'is_order_rider': is_order_rider,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
    })


@login_required
def update_rider_location_view(request, order_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    order = get_object_or_404(Order, id=order_id, rider=request.user)
    try:
        data = json.loads(request.body.decode('utf-8'))
        lat = float(data.get('lat'))
        lng = float(data.get('lng'))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({'error': 'Invalid coordinates'}, status=400)

    order.rider_lat = lat
    order.rider_lng = lng
    order.rider_location_updated_at = timezone.now()
    order.save(update_fields=['rider_lat', 'rider_lng', 'rider_location_updated_at'])

    return JsonResponse({
        'status': 'ok',
        'lat': order.rider_lat,
        'lng': order.rider_lng,
        'updated_at': order.rider_location_updated_at.strftime('%H:%M:%S'),
    })


@login_required
def get_order_location_json_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    is_allowed = (
        order.customer_id == request.user.id
        or order.rider_id == request.user.id
        or getattr(request.user, 'has_management_access', False)
    )
    if not is_allowed:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    return JsonResponse({
        'status': order.status,
        'status_display': order.get_status_display(),
        'rider_name': order.rider.username if order.rider else None,
        'rider_lat': order.rider_lat,
        'rider_lng': order.rider_lng,
        'updated_at': order.rider_location_updated_at.strftime('%H:%M:%S') if order.rider_location_updated_at else None,
    })


@login_required
def active_deliveries_json_view(request):
    if not getattr(request.user, 'has_management_access', False):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    active_orders = (
        Order.objects.filter(
            fulfillment_type=Order.FulfillmentType.DELIVERY,
            status__in=[Order.Status.ACCEPTED, Order.Status.READY, Order.Status.DISPATCHED],
        )
        .select_related('shop', 'rider', 'customer')
        .order_by('-created_at')
    )

    payload = []
    for order in active_orders:
        payload.append({
            'id': order.id,
            'shop_name': order.shop.name,
            'shop_lat': order.shop.latitude,
            'shop_lng': order.shop.longitude,
            'dropoff_lat': order.dropoff_lat,
            'dropoff_lng': order.dropoff_lng,
            'rider_name': order.rider.username if order.rider else 'Unassigned',
            'rider_lat': order.rider_lat,
            'rider_lng': order.rider_lng,
            'status': order.get_status_display(),
            'updated_at': (
                order.rider_location_updated_at.strftime('%H:%M:%S')
                if order.rider_location_updated_at
                else None
            ),
            'track_url': f'/orders/track/{order.id}/',
        })

    return JsonResponse({'deliveries': payload})