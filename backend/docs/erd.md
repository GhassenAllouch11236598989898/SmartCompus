# ERD — SmartCampus AI (SA-11)

> Fichier généré par `python -m scripts.gen_docs` à partir des modèles SQLAlchemy. Ne pas éditer à la main.

Légende : `||--o{` = 1..N obligatoire, `|o--o{` = 0..1 vers N (FK nullable), `||--o|` = 1..1 (FK unique).

## SA-12 — Catalogue académique

```mermaid
erDiagram
    institutions {
        bigint id PK
        varchar code UK
        varchar name
        text description
        varchar website
        boolean is_active
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    program_types {
        bigint id PK
        varchar code UK
        varchar label
        text description
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    programs {
        bigint id PK
        bigint institution_id FK
        bigint program_type_id FK
        varchar code UK
        varchar title
        varchar summary
        text description
        integer duration_semesters
        enum_study_mode study_mode
        varchar teaching_language
        varchar diploma_awarded
        enum_program_status status
        timestamp_with_time_zone published_at
        timestamp_with_time_zone archived_at
        tsvector search_vector
        bigint source_document_id FK
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    program_prerequisites {
        bigint id PK
        bigint program_id FK
        enum_prerequisite_kind kind
        varchar label
        text description
        boolean is_mandatory
        integer position
        bigint source_document_id FK
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    admission_conditions {
        bigint id PK
        bigint program_id FK
        varchar academic_year
        enum_admission_condition_kind kind
        text description
        numeric minimum_average
        varchar eligible_bac_sections
        integer position
        bigint source_document_id FK
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    career_outcomes {
        bigint id PK
        bigint program_id FK
        varchar title
        varchar sector
        text description
        bigint source_document_id FK
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    program_pathways {
        bigint id PK
        bigint from_program_id FK
        bigint to_program_id FK
        varchar entry_level
        text conditions
        bigint source_document_id FK
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    tuition_fees {
        bigint id PK
        bigint program_id FK
        varchar academic_year
        enum_fee_type fee_type
        numeric amount
        varchar currency
        text payment_terms
        bigint source_document_id FK
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    admission_campaigns {
        bigint id PK
        bigint institution_id FK
        varchar academic_year
        varchar name
        timestamp_with_time_zone opens_at
        timestamp_with_time_zone closes_at
        enum_campaign_status status
        bigint source_document_id FK
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    source_documents {
        bigint id PK
        bigint institution_id FK
        varchar title
        enum_source_document_type doc_type
        varchar version
        varchar content_hash
        enum_source_document_status status
        varchar uri
        varchar language
        date document_date
        timestamp_with_time_zone last_synced_at
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    institutions ||--o{ programs : "institution_id"
    program_types ||--o{ programs : "program_type_id"
    source_documents ||--o{ programs : "source_document_id"
    programs ||--o{ program_prerequisites : "program_id"
    source_documents ||--o{ program_prerequisites : "source_document_id"
    programs ||--o{ admission_conditions : "program_id"
    source_documents ||--o{ admission_conditions : "source_document_id"
    programs ||--o{ career_outcomes : "program_id"
    source_documents ||--o{ career_outcomes : "source_document_id"
    programs ||--o{ program_pathways : "from_program_id"
    source_documents ||--o{ program_pathways : "source_document_id"
    programs ||--o{ program_pathways : "to_program_id"
    programs ||--o{ tuition_fees : "program_id"
    source_documents ||--o{ tuition_fees : "source_document_id"
    institutions ||--o{ admission_campaigns : "institution_id"
    source_documents ||--o{ admission_campaigns : "source_document_id"
    institutions |o--o{ source_documents : "institution_id"
```

## SA-13 — Utilisateurs et candidatures

```mermaid
erDiagram
    users {
        bigint id PK
        varchar email UK
        varchar password_hash
        varchar full_name
        boolean is_active
        boolean is_service_account
        timestamp_with_time_zone last_login_at
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    roles {
        bigint id PK
        enum_role_code code UK
        varchar label
        bigint institution_id FK
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
    }
    user_roles {
        bigint user_id PK
        bigint role_id PK
        timestamp_with_time_zone granted_at
        bigint granted_by FK
    }
    candidates {
        bigint id PK
        bigint user_id FK
        varchar first_name
        varchar last_name
        varchar phone
        smallint birth_year
        varchar governorate
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    candidate_profiles {
        bigint id PK
        bigint candidate_id FK
        enum_education_level education_level
        varchar bac_section
        smallint bac_year
        numeric bac_average
        varchar current_program
        varchar interests
        varchar preferred_subjects
        text goals
        text constraints
        enum_message_language preferred_language
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    conversations {
        bigint id PK
        bigint candidate_id FK
        varchar session_token_hash UK
        enum_conversation_status status
        timestamp_with_time_zone started_at
        timestamp_with_time_zone last_message_at
        timestamp_with_time_zone attached_at
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    messages {
        bigint id PK
        bigint conversation_id FK
        integer sequence
        enum_message_sender sender
        enum_message_channel channel
        text content
        enum_message_language detected_language
        numeric language_confidence
        varchar audio_uri
        integer audio_duration_ms
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    recommendations {
        bigint id PK
        bigint candidate_id FK
        bigint conversation_id FK
        bigint program_id FK
        smallint rank
        numeric compatibility_score
        text justification
        jsonb cited_sources
        varchar model_name
        enum_review_status review_status
        bigint reviewed_by FK
        timestamp_with_time_zone reviewed_at
        text review_comment
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    consents {
        bigint id PK
        bigint user_id FK
        bigint conversation_id FK
        enum_consent_type consent_type
        varchar policy_version
        boolean granted
        timestamp_with_time_zone granted_at
        timestamp_with_time_zone revoked_at
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    dossiers {
        bigint id PK
        bigint candidate_id FK
        bigint campaign_id FK
        enum_dossier_status status
        text ai_summary
        timestamp_with_time_zone ai_summary_updated_at
        timestamp_with_time_zone closed_at
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    preinscriptions {
        bigint id PK
        bigint dossier_id FK
        bigint program_id FK
        enum_preinscription_status status
        smallint choice_rank
        timestamp_with_time_zone submitted_at
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    equivalence_requests {
        bigint id PK
        bigint dossier_id FK
        bigint target_program_id FK
        varchar origin_diploma
        varchar origin_program
        varchar origin_institution
        varchar origin_country
        enum_education_level origin_level
        varchar requested_entry_level
        enum_equivalence_status status
        timestamp_with_time_zone submitted_at
        bigint reviewed_by FK
        timestamp_with_time_zone reviewed_at
        text review_comment
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    equivalence_documents {
        bigint id PK
        bigint equivalence_request_id FK
        enum_equivalence_document_type document_type
        varchar file_name
        varchar storage_key UK
        varchar mime_type
        bigint size_bytes
        varchar sha256
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    qcm {
        bigint id PK
        bigint dossier_id FK
        bigint program_id FK
        varchar title
        enum_qcm_generated_by generated_by
        varchar template_code
        varchar model_name
        enum_qcm_status status
        numeric score
        numeric max_score
        text summary_for_interviewer
        timestamp_with_time_zone started_at
        timestamp_with_time_zone completed_at
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    qcm_questions {
        bigint id PK
        bigint qcm_id FK
        smallint position
        varchar topic
        text question_text
        jsonb choices
        smallint correct_choice_index
        numeric points
        text explanation
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    qcm_answers {
        bigint id PK
        bigint question_id FK
        smallint selected_choice_index
        boolean is_correct
        numeric points_awarded
        timestamp_with_time_zone answered_at
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    appointments {
        bigint id PK
        bigint dossier_id FK
        bigint organizer_id FK
        timestamp_with_time_zone scheduled_at
        smallint duration_minutes
        enum_appointment_mode mode
        varchar location
        varchar meeting_url
        enum_appointment_status status
        text cancellation_reason
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    interview_results {
        bigint id PK
        bigint appointment_id FK
        bigint interviewer_id FK
        text observations
        numeric score
        enum_interview_opinion opinion
        timestamp_with_time_zone recorded_at
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    decisions {
        bigint id PK
        bigint dossier_id FK
        bigint program_id FK
        enum_decision_value decision
        text observations
        bigint responsible_id FK
        timestamp_with_time_zone decided_at
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    notifications {
        bigint id PK
        bigint user_id FK
        bigint dossier_id FK
        enum_notification_kind kind
        enum_notification_channel channel
        varchar template_code
        varchar subject
        timestamp_with_time_zone scheduled_for
        enum_notification_status status
        smallint attempts
        timestamp_with_time_zone sent_at
        text last_error
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    audit_log {
        bigint id PK
        timestamp_with_time_zone occurred_at
        enum_actor_type actor_type
        bigint actor_user_id FK
        varchar action
        varchar entity_type
        bigint entity_id
        jsonb details
        varchar request_id
    }
    status_history {
        bigint id PK
        varchar entity_type
        bigint entity_id
        varchar old_status
        varchar new_status
        bigint changed_by
        timestamp_with_time_zone changed_at
    }
    institutions |o--o{ roles : "institution_id"
    users |o--o{ user_roles : "granted_by"
    roles ||--o{ user_roles : "role_id"
    users ||--o{ user_roles : "user_id"
    users ||--o| candidates : "user_id"
    candidates ||--o| candidate_profiles : "candidate_id"
    candidates |o--o{ conversations : "candidate_id"
    conversations ||--o{ messages : "conversation_id"
    candidates |o--o{ recommendations : "candidate_id"
    conversations |o--o{ recommendations : "conversation_id"
    programs ||--o{ recommendations : "program_id"
    users |o--o{ recommendations : "reviewed_by"
    conversations |o--o{ consents : "conversation_id"
    users |o--o{ consents : "user_id"
    admission_campaigns ||--o{ dossiers : "campaign_id"
    candidates ||--o{ dossiers : "candidate_id"
    dossiers ||--o{ preinscriptions : "dossier_id"
    programs ||--o{ preinscriptions : "program_id"
    dossiers ||--o{ equivalence_requests : "dossier_id"
    users |o--o{ equivalence_requests : "reviewed_by"
    programs ||--o{ equivalence_requests : "target_program_id"
    equivalence_requests ||--o{ equivalence_documents : "equivalence_request_id"
    dossiers ||--o{ qcm : "dossier_id"
    programs |o--o{ qcm : "program_id"
    qcm ||--o{ qcm_questions : "qcm_id"
    qcm_questions ||--o| qcm_answers : "question_id"
    dossiers ||--o{ appointments : "dossier_id"
    users ||--o{ appointments : "organizer_id"
    appointments ||--o| interview_results : "appointment_id"
    users ||--o{ interview_results : "interviewer_id"
    dossiers ||--o{ decisions : "dossier_id"
    programs |o--o{ decisions : "program_id"
    users ||--o{ decisions : "responsible_id"
    dossiers |o--o{ notifications : "dossier_id"
    users ||--o{ notifications : "user_id"
    users |o--o{ audit_log : "actor_user_id"
```

## SA-14 — Documents et synchronisation

```mermaid
erDiagram
    source_documents {
        bigint id PK
        bigint institution_id FK
        varchar title
        enum_source_document_type doc_type
        varchar version
        varchar content_hash
        enum_source_document_status status
        varchar uri
        varchar language
        date document_date
        timestamp_with_time_zone last_synced_at
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    document_chunks {
        bigint id PK
        bigint source_document_id FK
        bigint program_id FK
        integer chunk_index
        text content
        varchar section_title
        integer page_number
        integer token_count
        vector embedding
        varchar embedding_model
        jsonb metadata
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
        boolean is_demo
    }
    sync_jobs {
        bigint id PK
        bigint source_document_id FK
        enum_sync_job_type job_type
        enum_sync_status status
        bigint triggered_by FK
        timestamp_with_time_zone started_at
        timestamp_with_time_zone finished_at
        integer processed_count
        integer error_count
        text last_error
        timestamp_with_time_zone created_at
        timestamp_with_time_zone updated_at
    }
    sync_logs {
        bigint id PK
        bigint sync_job_id FK
        enum_sync_log_level level
        text message
        jsonb details
        timestamp_with_time_zone created_at
    }
    institutions |o--o{ source_documents : "institution_id"
    programs |o--o{ document_chunks : "program_id"
    source_documents ||--o{ document_chunks : "source_document_id"
    source_documents |o--o{ sync_jobs : "source_document_id"
    users |o--o{ sync_jobs : "triggered_by"
    sync_jobs ||--o{ sync_logs : "sync_job_id"
```

