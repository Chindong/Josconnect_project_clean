from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from .models import Feedback


@login_required
def submit_feedback_view(request):
    if request.method == 'POST':
        msg = request.POST.get('message', '').strip()
        if msg:
            Feedback.objects.create(user=request.user, message=msg)
            messages.success(request, 'Feedback submitted.')
        else:
            messages.error(request, 'Please enter your feedback message.')
        return redirect('feedback_app:submit_feedback')
    recent = Feedback.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'feedback_app/feedback.html', {'recent': recent})