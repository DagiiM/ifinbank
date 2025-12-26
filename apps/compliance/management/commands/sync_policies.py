"""
Management command to sync policies to ChromaDB.

Usage:
    python manage.py sync_policies
    python manage.py sync_policies --category kyc
    python manage.py sync_policies --clean
"""
from django.core.management.base import BaseCommand, CommandError
from apps.compliance.services import get_embedding_service, PolicyEmbeddingService
from apps.compliance.models import Policy


class Command(BaseCommand):
    help = 'Sync policy documents to ChromaDB for semantic search'

    def add_arguments(self, parser):
        parser.add_argument(
            '--category',
            type=str,
            help='Sync only policies of this category (kyc, aml, institutional, regulatory)',
        )
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Remove existing embeddings before syncing',
        )
        parser.add_argument(
            '--policy',
            type=str,
            help='Sync a specific policy by code',
        )

    def handle(self, *args, **options):
        service = get_embedding_service()
        
        self.stdout.write(self.style.NOTICE('Connecting to ChromaDB...'))
        
        # Get collection stats
        stats = service.get_collection_stats()
        if 'error' not in stats:
            self.stdout.write(f"Current documents in collection: {stats['total_documents']}")
        
        # Clean if requested
        if options['clean']:
            self.stdout.write(self.style.WARNING('Cleaning existing embeddings...'))
            policies = Policy.objects.filter(is_active=True)
            for policy in policies:
                service.remove_policy(str(policy.id))
            self.stdout.write(self.style.SUCCESS('Cleaned existing embeddings'))
        
        # Sync specific policy
        if options['policy']:
            try:
                policy = Policy.objects.get(code=options['policy'])
                success = service.index_policy(
                    policy_id=str(policy.id),
                    policy_code=policy.code,
                    content=policy.content,
                    metadata={
                        'category': policy.category,
                        'version': policy.version,
                        'name': policy.name,
                    }
                )
                if success:
                    policy.embedding_id = str(policy.id)
                    policy.save(update_fields=['embedding_id'])
                    self.stdout.write(self.style.SUCCESS(f'Synced policy: {policy.code}'))
                else:
                    self.stdout.write(self.style.ERROR(f'Failed to sync: {policy.code}'))
            except Policy.DoesNotExist:
                raise CommandError(f'Policy not found: {options["policy"]}')
            return
        
        # Sync all or by category
        queryset = Policy.objects.filter(is_active=True)
        if options['category']:
            queryset = queryset.filter(category=options['category'])
        
        total = queryset.count()
        if total == 0:
            self.stdout.write(self.style.WARNING('No policies found to sync'))
            return
        
        self.stdout.write(f'Syncing {total} policies...')
        
        indexed = 0
        failed = 0
        
        for policy in queryset:
            success = service.index_policy(
                policy_id=str(policy.id),
                policy_code=policy.code,
                content=policy.content,
                metadata={
                    'category': policy.category,
                    'version': policy.version,
                    'name': policy.name,
                    'effective_date': str(policy.effective_date),
                }
            )
            
            if success:
                policy.embedding_id = str(policy.id)
                policy.save(update_fields=['embedding_id'])
                indexed += 1
                self.stdout.write(f'  ✓ {policy.code}')
            else:
                failed += 1
                self.stdout.write(self.style.ERROR(f'  ✗ {policy.code}'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Sync complete: {indexed} indexed, {failed} failed'))
        
        # Show final stats
        stats = service.get_collection_stats()
        if 'error' not in stats:
            self.stdout.write(f"Total documents in collection: {stats['total_documents']}")
