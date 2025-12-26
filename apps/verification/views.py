"""Verification views."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta

from .models import VerificationRequest, VerificationResult, Discrepancy
from .services import VerificationService


@login_required
def dashboard(request):
    """Verification dashboard with statistics."""
    # Get stats
    today = timezone.now().date()
    
    stats = {
        'pending': VerificationRequest.objects.filter(status='pending').count(),
        'review_required': VerificationRequest.objects.filter(status='review_required').count(),
        'completed_today': VerificationRequest.objects.filter(
            status='completed',
            completed_at__date=today
        ).count(),
        'approval_rate': _calculate_approval_rate(),
    }
    
    # Recent requests
    recent_requests = VerificationRequest.objects.select_related(
        'requested_by', 'assigned_to'
    ).order_by('-created_at')[:10]
    
    # My assigned requests (for verification officers)
    my_requests = VerificationRequest.objects.filter(
        assigned_to=request.user,
        status__in=['pending', 'processing', 'review_required']
    ).order_by('priority', '-created_at')[:5]
    
    context = {
        'stats': stats,
        'recent_requests': recent_requests,
        'my_requests': my_requests,
    }
    return render(request, 'verification/dashboard.html', context)


@login_required
def request_list(request):
    """List all verification requests with filtering."""
    queryset = VerificationRequest.objects.select_related(
        'requested_by', 'assigned_to'
    ).order_by('priority', '-created_at')
    
    # Apply filters
    status = request.GET.get('status')
    if status:
        queryset = queryset.filter(status=status)
    
    priority = request.GET.get('priority')
    if priority:
        queryset = queryset.filter(priority=priority)
    
    search = request.GET.get('search')
    if search:
        queryset = queryset.filter(
            Q(customer_id__icontains=search) |
            Q(account_reference__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(queryset, 25)
    page = request.GET.get('page', 1)
    requests_page = paginator.get_page(page)
    
    context = {
        'requests': requests_page,
        'status_choices': VerificationRequest.STATUS_CHOICES,
        'priority_choices': VerificationRequest.PRIORITY_CHOICES,
        'current_filters': {
            'status': status,
            'priority': priority,
            'search': search,
        }
    }
    return render(request, 'verification/request_list.html', context)


@login_required
def request_create(request):
    """Create a new verification request."""
    if request.method == 'POST':
        customer_id = request.POST.get('customer_id')
        account_reference = request.POST.get('account_reference', '')
        priority = int(request.POST.get('priority', 5))
        
        # Build customer data from form
        customer_data = {
            'full_name': request.POST.get('full_name', ''),
            'id_number': request.POST.get('id_number', ''),
            'date_of_birth': request.POST.get('date_of_birth', ''),
            'phone': request.POST.get('phone', ''),
            'email': request.POST.get('email', ''),
            'address': request.POST.get('address', ''),
        }
        
        service = VerificationService(user=request.user)
        verification_request = service.create_request(
            customer_id=customer_id,
            customer_data=customer_data,
            priority=priority,
            account_reference=account_reference
        )
        
        messages.success(
            request,
            f'Verification request {verification_request.reference_number} created successfully.'
        )
        return redirect('verification:request_detail', pk=verification_request.id)
    
    return render(request, 'verification/request_create.html', {
        'priority_choices': VerificationRequest.PRIORITY_CHOICES,
    })


@login_required
def request_detail(request, pk):
    """View verification request details."""
    verification_request = get_object_or_404(
        VerificationRequest.objects.select_related('requested_by', 'assigned_to', 'reviewed_by'),
        pk=pk
    )
    
    results = verification_request.results.all()
    discrepancies = verification_request.discrepancies.all()
    documents = verification_request.documents.all()
    
    context = {
        'request': verification_request,
        'results': results,
        'discrepancies': discrepancies,
        'documents': documents,
    }
    return render(request, 'verification/request_detail.html', context)


@login_required
def request_process(request, pk):
    """Trigger verification processing."""
    verification_request = get_object_or_404(VerificationRequest, pk=pk)
    
    if verification_request.status != 'pending':
        messages.warning(request, 'Request is not in pending status.')
        return redirect('verification:request_detail', pk=pk)
    
    service = VerificationService(user=request.user)
    
    try:
        outcome = service.process_request(verification_request)
        messages.success(
            request,
            f'Verification completed. Score: {outcome.score:.1f}%'
        )
    except Exception as e:
        messages.error(request, f'Verification failed: {str(e)}')
    
    return redirect('verification:request_detail', pk=pk)


@login_required
def request_review(request, pk):
    """Manual review interface."""
    verification_request = get_object_or_404(VerificationRequest, pk=pk)
    
    results = verification_request.results.all()
    discrepancies = verification_request.discrepancies.all()
    documents = verification_request.documents.all()
    
    context = {
        'request': verification_request,
        'results': results,
        'discrepancies': discrepancies,
        'documents': documents,
    }
    return render(request, 'verification/request_review.html', context)


@login_required
def request_approve(request, pk):
    """Approve a verification request."""
    verification_request = get_object_or_404(VerificationRequest, pk=pk)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', 'Manually approved')
        
        service = VerificationService(user=request.user)
        service.approve_request(verification_request, reason, request.user)
        
        messages.success(request, 'Request approved successfully.')
    
    return redirect('verification:request_detail', pk=pk)


@login_required
def request_reject(request, pk):
    """Reject a verification request."""
    verification_request = get_object_or_404(VerificationRequest, pk=pk)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        
        if not reason:
            messages.error(request, 'Rejection reason is required.')
            return redirect('verification:request_review', pk=pk)
        
        service = VerificationService(user=request.user)
        service.reject_request(verification_request, reason, request.user)
        
        messages.success(request, 'Request rejected.')
    
    return redirect('verification:request_detail', pk=pk)


# API Views

@login_required
def api_request_list(request):
    """API endpoint for listing requests."""
    queryset = VerificationRequest.objects.order_by('-created_at')[:100]
    
    data = [{
        'id': str(r.id),
        'reference': r.reference_number,
        'customer_id': r.customer_id,
        'status': r.status,
        'priority': r.priority,
        'score': float(r.overall_score) if r.overall_score else None,
        'is_approved': r.is_approved,
        'created_at': r.created_at.isoformat(),
    } for r in queryset]
    
    return JsonResponse({'requests': data})


@login_required
def api_request_detail(request, pk):
    """API endpoint for request details."""
    verification_request = get_object_or_404(VerificationRequest, pk=pk)
    
    data = {
        'id': str(verification_request.id),
        'reference': verification_request.reference_number,
        'customer_id': verification_request.customer_id,
        'account_reference': verification_request.account_reference,
        'status': verification_request.status,
        'priority': verification_request.priority,
        'customer_data': verification_request.customer_data,
        'score': float(verification_request.overall_score) if verification_request.overall_score else None,
        'is_approved': verification_request.is_approved,
        'decision_reason': verification_request.decision_reason,
        'created_at': verification_request.created_at.isoformat(),
        'results': [r.to_dict() for r in verification_request.results.all()],
        'discrepancies': [d.to_dict() for d in verification_request.discrepancies.all()],
    }
    
    return JsonResponse(data)


# Helper functions

def _calculate_approval_rate():
    """Calculate the approval rate for the last 30 days."""
    thirty_days_ago = timezone.now() - timedelta(days=30)
    completed = VerificationRequest.objects.filter(
        status='completed',
        completed_at__gte=thirty_days_ago
    )
    
    total = completed.count()
    if total == 0:
        return 0.0
    
    approved = completed.filter(is_approved=True).count()
    return round((approved / total) * 100, 1)
