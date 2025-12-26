"""Compliance views."""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from .models import Policy, ComplianceRule, ComplianceCheck
from .services import ComplianceService
from apps.verification.models import VerificationRequest


@login_required
def policy_list(request):
    """List all active policies."""
    policies = Policy.objects.filter(is_active=True).order_by('category', 'name')
    
    context = {
        'policies': policies,
    }
    return render(request, 'compliance/policy_list.html', context)


@login_required
def policy_detail(request, pk):
    """View policy details."""
    policy = get_object_or_404(Policy, pk=pk)
    rules = policy.rules.filter(is_active=True)
    
    context = {
        'policy': policy,
        'rules': rules,
    }
    return render(request, 'compliance/policy_detail.html', context)


@login_required
def run_compliance_check(request, request_id):
    """Run compliance check on a verification request."""
    verification_request = get_object_or_404(VerificationRequest, pk=request_id)
    
    service = ComplianceService()
    results = service.check_compliance(verification_request)
    
    # Get check results
    checks = ComplianceCheck.objects.filter(
        verification_request=verification_request
    ).order_by('-checked_at')
    
    data = {
        'success': True,
        'checks_run': len(results),
        'checks': [check.to_dict() for check in checks],
    }
    
    return JsonResponse(data)
