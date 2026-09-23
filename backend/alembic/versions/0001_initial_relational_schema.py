"""0001_initial_relational_schema

Revision ID: 0001_initial
Revises: None
Create Date: 2026-09-15 12:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. departments
    op.create_table(
        'departments',
        sa.Column('department_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('code', sa.String(length=32), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('default_sla_hours', sa.Integer(), nullable=True),
        sa.Column('escalation_contact', sa.String(length=256), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('department_id'),
        sa.UniqueConstraint('code'),
        sa.UniqueConstraint('name')
    )
    op.create_index('ix_departments_code', 'departments', ['code'])
    op.create_index('ix_departments_department_id', 'departments', ['department_id'])
    op.create_index('ix_departments_name', 'departments', ['name'])

    # 2. categories
    op.create_table(
        'categories',
        sa.Column('category_id', sa.String(length=64), nullable=False),
        sa.Column('department_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('typical_sla_hours', sa.Integer(), nullable=True),
        sa.Column('subcategories', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['department_id'], ['departments.department_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('category_id')
    )
    op.create_index('ix_categories_category_id', 'categories', ['category_id'])
    op.create_index('ix_categories_department_id', 'categories', ['department_id'])
    op.create_index('ix_categories_name', 'categories', ['name'])

    # 3. raw_complaints
    op.create_table(
        'raw_complaints',
        sa.Column('complaint_id', sa.String(length=64), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('channel', sa.String(length=64), nullable=True),
        sa.Column('text', sa.Text(), nullable=True),
        sa.Column('audio_path', sa.String(length=512), nullable=True),
        sa.Column('image_path', sa.String(length=512), nullable=True),
        sa.Column('image_caption', sa.Text(), nullable=True),
        sa.Column('source_location', sa.String(length=256), nullable=True),
        sa.Column('department_label', sa.String(length=64), nullable=True),
        sa.Column('category_label', sa.String(length=64), nullable=True),
        sa.Column('urgency_label', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('complaint_id')
    )
    op.create_index('ix_raw_complaints_channel', 'raw_complaints', ['channel'])
    op.create_index('ix_raw_complaints_complaint_id', 'raw_complaints', ['complaint_id'])

    # 4. duplicate_clusters
    op.create_table(
        'duplicate_clusters',
        sa.Column('cluster_id', sa.String(length=64), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('detection_method', sa.String(length=64), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('cluster_id')
    )
    op.create_index('ix_duplicate_clusters_cluster_id', 'duplicate_clusters', ['cluster_id'])

    # 5. cluster_members
    op.create_table(
        'cluster_members',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('cluster_id', sa.String(length=64), nullable=False),
        sa.Column('complaint_id', sa.String(length=64), nullable=False),
        sa.Column('similarity_score', sa.Float(), nullable=True),
        sa.Column('added_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['cluster_id'], ['duplicate_clusters.cluster_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['complaint_id'], ['raw_complaints.complaint_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cluster_id', 'complaint_id', name='uq_cluster_complaint')
    )
    op.create_index('ix_cluster_members_cluster_id', 'cluster_members', ['cluster_id'])
    op.create_index('ix_cluster_members_complaint_id', 'cluster_members', ['complaint_id'])

    # 6. acknowledgements
    op.create_table(
        'acknowledgements',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('complaint_id', sa.String(length=64), nullable=False),
        sa.Column('draft_text', sa.Text(), nullable=False),
        sa.Column('language', sa.String(length=16), nullable=False, server_default='en'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='draft'),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('edited_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_by', sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(['complaint_id'], ['raw_complaints.complaint_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('draft', 'edited', 'approved')", name='chk_acknowledgement_status')
    )
    op.create_index('ix_acknowledgements_complaint_id', 'acknowledgements', ['complaint_id'])
    op.create_index('ix_acknowledgements_status', 'acknowledgements', ['status'])

    # 7. triaged_complaints
    op.create_table(
        'triaged_complaints',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('complaint_id', sa.String(length=64), nullable=False),
        sa.Column('language', sa.String(length=16), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('department', sa.String(length=64), nullable=True),
        sa.Column('category', sa.String(length=64), nullable=True),
        sa.Column('subcategory', sa.String(length=128), nullable=True),
        sa.Column('urgency', sa.String(length=32), nullable=True),
        sa.Column('urgency_score', sa.Float(), nullable=True),
        sa.Column('urgency_reason', sa.Text(), nullable=True),
        sa.Column('normalized_locality', sa.String(length=256), nullable=True),
        sa.Column('ward', sa.String(length=64), nullable=True),
        sa.Column('zone', sa.String(length=64), nullable=True),
        sa.Column('duplicate_cluster_id', sa.String(length=64), nullable=True),
        sa.Column('duplicate_confidence', sa.Float(), nullable=True),
        sa.Column('routing_evidence', sa.Text(), nullable=True),
        sa.Column('routing_confidence', sa.Float(), nullable=True),
        sa.Column('acknowledgement_id', sa.Integer(), nullable=True),
        sa.Column('processing_status', sa.String(length=64), nullable=False, server_default='OPERATOR_REVIEW_PENDING'),
        sa.Column('model_version', sa.String(length=64), nullable=True),
        sa.Column('prompt_version', sa.String(length=64), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['acknowledgement_id'], ['acknowledgements.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['category'], ['categories.category_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['complaint_id'], ['raw_complaints.complaint_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['department'], ['departments.department_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['duplicate_cluster_id'], ['duplicate_clusters.cluster_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('complaint_id')
    )
    op.create_index('ix_triaged_complaints_category', 'triaged_complaints', ['category'])
    op.create_index('ix_triaged_complaints_complaint_id', 'triaged_complaints', ['complaint_id'])
    op.create_index('ix_triaged_complaints_department', 'triaged_complaints', ['department'])
    op.create_index('ix_triaged_complaints_duplicate_cluster_id', 'triaged_complaints', ['duplicate_cluster_id'])
    op.create_index('ix_triaged_complaints_normalized_locality', 'triaged_complaints', ['normalized_locality'])
    op.create_index('ix_triaged_complaints_processing_status', 'triaged_complaints', ['processing_status'])
    op.create_index('ix_triaged_complaints_urgency', 'triaged_complaints', ['urgency'])
    op.create_index('ix_triaged_complaints_ward', 'triaged_complaints', ['ward'])
    op.create_index('ix_triaged_complaints_zone', 'triaged_complaints', ['zone'])

    # 8. status_history
    op.create_table(
        'status_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('complaint_id', sa.String(length=64), nullable=False),
        sa.Column('old_status', sa.String(length=64), nullable=True),
        sa.Column('new_status', sa.String(length=64), nullable=False),
        sa.Column('changed_by', sa.String(length=128), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['complaint_id'], ['raw_complaints.complaint_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_status_history_complaint_id', 'status_history', ['complaint_id'])
    op.create_index('ix_status_history_new_status', 'status_history', ['new_status'])

    # 9. locality_gazetteer
    op.create_table(
        'locality_gazetteer',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('canonical_locality', sa.String(length=128), nullable=False),
        sa.Column('ward', sa.String(length=64), nullable=False),
        sa.Column('zone', sa.String(length=64), nullable=False),
        sa.Column('aliases', sa.JSON(), nullable=True),
        sa.Column('landmarks', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('canonical_locality')
    )
    op.create_index('ix_locality_gazetteer_canonical_locality', 'locality_gazetteer', ['canonical_locality'])
    op.create_index('ix_locality_gazetteer_ward', 'locality_gazetteer', ['ward'])
    op.create_index('ix_locality_gazetteer_zone', 'locality_gazetteer', ['zone'])

    # 10. locality_aliases
    op.create_table(
        'locality_aliases',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('alias_normalized', sa.String(length=128), nullable=False),
        sa.Column('gazetteer_id', sa.Integer(), nullable=False),
        sa.Column('canonical_locality', sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(['gazetteer_id'], ['locality_gazetteer.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('alias_normalized')
    )
    op.create_index('ix_locality_aliases_alias_normalized', 'locality_aliases', ['alias_normalized'])
    op.create_index('ix_locality_aliases_canonical_locality', 'locality_aliases', ['canonical_locality'])
    op.create_index('ix_locality_aliases_gazetteer_id', 'locality_aliases', ['gazetteer_id'])

    # 11. evaluation_results
    op.create_table(
        'evaluation_results',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('test_set_version', sa.String(length=64), nullable=False),
        sa.Column('total_samples', sa.Integer(), nullable=False),
        sa.Column('department_accuracy', sa.Float(), nullable=False),
        sa.Column('category_accuracy', sa.Float(), nullable=False),
        sa.Column('urgency_accuracy', sa.Float(), nullable=False),
        sa.Column('locality_normalization_accuracy', sa.Float(), nullable=False),
        sa.Column('duplicate_reduction', sa.Float(), nullable=False),
        sa.Column('confusion_matrix', sa.JSON(), nullable=True),
        sa.Column('per_class_metrics', sa.JSON(), nullable=True),
        sa.Column('is_synthetic_benchmark', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_evaluation_results_test_set_version', 'evaluation_results', ['test_set_version'])

    # 12. weekly_reports
    op.create_table(
        'weekly_reports',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('report_period_start', sa.Date(), nullable=False),
        sa.Column('report_period_end', sa.Date(), nullable=False),
        sa.Column('department', sa.String(length=128), nullable=False),
        sa.Column('complaints_received', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('complaints_resolved', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('complaints_pending', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('median_resolution_time', sa.Float(), nullable=True),
        sa.Column('repeat_complaints', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('top_categories', sa.JSON(), nullable=True),
        sa.Column('major_clusters', sa.JSON(), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_weekly_reports_department', 'weekly_reports', ['department'])
    op.create_index('ix_weekly_reports_report_period_end', 'weekly_reports', ['report_period_end'])
    op.create_index('ix_weekly_reports_report_period_start', 'weekly_reports', ['report_period_start'])


def downgrade() -> None:
    op.drop_table('weekly_reports')
    op.drop_table('evaluation_results')
    op.drop_table('locality_aliases')
    op.drop_table('locality_gazetteer')
    op.drop_table('status_history')
    op.drop_table('triaged_complaints')
    op.drop_table('acknowledgements')
    op.drop_table('cluster_members')
    op.drop_table('duplicate_clusters')
    op.drop_table('raw_complaints')
    op.drop_table('categories')
    op.drop_table('departments')
