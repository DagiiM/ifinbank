"""Documents views."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, FileResponse
from django.views.decorators.http import require_POST

from .models import Document, DocumentExtraction
from .services import ExtractionService
from apps.verification.models import VerificationRequest


@login_required
@require_POST
def document_upload(request):
    """Handle document upload."""
    verification_request_id = request.POST.get('verification_request')
    document_type = request.POST.get('document_type')
    file = request.FILES.get('file')
    
    if not all([verification_request_id, document_type, file]):
        return JsonResponse({
            'success': False,
            'error': 'Missing required fields'
        }, status=400)
    
    try:
        verification_request = VerificationRequest.objects.get(id=verification_request_id)
    except VerificationRequest.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Verification request not found'
        }, status=404)
    
    # Create document
    document = Document.objects.create(
        verification_request=verification_request,
        document_type=document_type,
        file=file,
        original_filename=file.name,
        file_size=file.size,
    )
    
    # Optionally auto-process
    auto_process = request.POST.get('auto_process', 'false').lower() == 'true'
    if auto_process:
        try:
            service = ExtractionService()
            service.process_document(document)
        except Exception as e:
            # Document created but processing failed
            pass
    
    return JsonResponse({
        'success': True,
        'document': {
            'id': str(document.id),
            'type': document.document_type,
            'filename': document.original_filename,
            'is_processed': document.is_processed,
        }
    })


@login_required
def document_detail(request, pk):
    """View document details."""
    document = get_object_or_404(Document, pk=pk)
    extraction = document.extractions.first()
    
    context = {
        'document': document,
        'extraction': extraction,
    }
    return render(request, 'documents/detail.html', context)


@login_required
@require_POST
def document_process(request, pk):
    """Trigger document OCR processing."""
    document = get_object_or_404(Document, pk=pk)
    
    if document.is_processed:
        return JsonResponse({
            'success': False,
            'error': 'Document already processed'
        }, status=400)
    
    try:
        service = ExtractionService()
        extraction = service.process_document(document)
        
        return JsonResponse({
            'success': True,
            'extraction': extraction.to_dict()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def document_view(request, pk):
    """View/download the actual document file."""
    document = get_object_or_404(Document, pk=pk)
    
    return FileResponse(
        document.file.open('rb'),
        as_attachment=False,
        filename=document.original_filename
    )


@login_required
def document_extraction(request, pk):
    """Get document extraction data as JSON."""
    document = get_object_or_404(Document, pk=pk)
    extraction = document.extractions.first()
    
    if not extraction:
        return JsonResponse({
            'success': False,
            'error': 'No extraction data available'
        }, status=404)
    
    return JsonResponse({
        'success': True,
        'extraction': extraction.to_dict()
    })
