# Dictionnaire de données — SmartCampus AI

> Généré par `python -m scripts.gen_docs` depuis les modèles. La justification de la
> normalisation et les règles transverses sont dans [normalisation.md](normalisation.md).

Colonnes communes : `id` — Clé primaire technique (BIGINT identity).; `created_at` — Date de création (UTC, défaut now()).; `updated_at` — Date de dernière modification (trigger set_updated_at).; `is_demo` — true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md).; `source_document_id` — Document source officiel de l'information (traçabilité obligatoire).

## SA-12 — Catalogue académique

### `institutions`

Base class used for declarative class definitions. The :class:`_orm.DeclarativeBase` allows for the creation of new declarative bases in such a way that is compatible with type checkers:: from sqlalchemy.orm import DeclarativeBase class Base(DeclarativeBase): pass The above ``Base`` class is now usable as the base for new declarative mappings. The superclass makes use of the ``__init_subclass__()`` method to set up new classes and metaclasses aren't used. When first used, the :class:`_orm.DeclarativeBase` class instantiates a new :class:`_orm.registry` to be used with the base, assuming one was not provided explicitly. The :class:`_orm.DeclarativeBase` class supports class-level attributes which act as parameters for the construction of this registry; such as to indicate a specific :class:`_schema.MetaData` collection as well as a specific value for :paramref:`_orm.registry.type_annotation_map`:: from typing_extensions import Annotated from sqlalchemy import BigInteger from sqlalchemy import MetaData from sqlalchemy import String from sqlalchemy.orm import DeclarativeBase bigint = Annotated[int, "bigint"] my_metadata = MetaData() class Base(DeclarativeBase): metadata = my_metadata type_annotation_map = { str: String().with_variant(String(255), "mysql", "mariadb"), bigint: BigInteger(), } Class-level attributes which may be specified include: :param metadata: optional :class:`_schema.MetaData` collection. If a :class:`_orm.registry` is constructed automatically, this :class:`_schema.MetaData` collection will be used to construct it. Otherwise, the local :class:`_schema.MetaData` collection will supersede that used by an existing :class:`_orm.registry` passed using the :paramref:`_orm.DeclarativeBase.registry` parameter. :param type_annotation_map: optional type annotation map that will be passed to the :class:`_orm.registry` as :paramref:`_orm.registry.type_annotation_map`. :param registry: supply a pre-existing :class:`_orm.registry` directly. .. versionadded:: 2.0 Added :class:`.DeclarativeBase`, so that declarative base classes may be constructed in such a way that is also recognized by :pep:`484` type checkers. As a result, :class:`.DeclarativeBase` and other subclassing-oriented APIs should be seen as superseding previous "class returned by a function" APIs, namely :func:`_orm.declarative_base` and :meth:`_orm.registry.generate_base`, where the base class returned cannot be recognized by type checkers without using plugins. **__init__ behavior** In a plain Python class, the base-most ``__init__()`` method in the class hierarchy is ``object.__init__()``, which accepts no arguments. However, when the :class:`_orm.DeclarativeBase` subclass is first declared, the class is given an ``__init__()`` method that links to the :paramref:`_orm.registry.constructor` constructor function, if no ``__init__()`` method is already present; this is the usual declarative constructor that will assign keyword arguments as attributes on the instance, assuming those attributes are established at the class level (i.e. are mapped, or are linked to a descriptor). This constructor is **never accessed by a mapped class without being called explicitly via super()**, as mapped classes are themselves given an ``__init__()`` method directly which calls :paramref:`_orm.registry.constructor`, so in the default case works independently of what the base-most ``__init__()`` method does. .. versionchanged:: 2.0.1 :class:`_orm.DeclarativeBase` has a default constructor that links to :paramref:`_orm.registry.constructor` by default, so that calls to ``super().__init__()`` can access this constructor. Previously, due to an implementation mistake, this default constructor was missing, and calling ``super().__init__()`` would invoke ``object.__init__()``. The :class:`_orm.DeclarativeBase` subclass may also declare an explicit ``__init__()`` method which will replace the use of the :paramref:`_orm.registry.constructor` function at this level:: class Base(DeclarativeBase): def __init__(self, id=None): self.id = id Mapped classes still will not invoke this constructor implicitly; it remains only accessible by calling ``super().__init__()``:: class MyClass(Base): def __init__(self, id=None, name=None): self.name = name super().__init__(id=id) Note that this is a different behavior from what functions like the legacy :func:`_orm.declarative_base` would do; the base created by those functions would always install :paramref:`_orm.registry.constructor` for ``__init__()``.

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `code` | VARCHAR(20) | non |  | UNIQUE |  |
| `name` | VARCHAR(255) | non |  |  |  |
| `description` | TEXT | oui |  |  |  |
| `website` | VARCHAR(255) | oui |  |  |  |
| `is_active` | BOOLEAN | non | true |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- CHECK `ck_institutions_code_format` : `code ~ '^[A-Z0-9_]{2,20}$'`

### `program_types`

Type de parcours : Licence, Préparatoire, Ingénierie, Master…

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `code` | VARCHAR(30) | non |  | UNIQUE |  |
| `label` | VARCHAR(100) | non |  |  |  |
| `description` | TEXT | oui |  |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- CHECK `ck_program_types_code_format` : `code ~ '^[A-Z0-9_]{2,30}$'`

### `programs`

Formation / programme proposé par un établissement.

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `institution_id` | BIGINT | non |  | FK → institutions.id |  |
| `program_type_id` | BIGINT | non |  | FK → program_types.id |  |
| `code` | VARCHAR(40) | non |  | UNIQUE |  |
| `title` | VARCHAR(255) | non |  |  |  |
| `summary` | VARCHAR(500) | oui |  |  |  |
| `description` | TEXT | oui |  |  | Contenu de la formation. |
| `duration_semesters` | INTEGER | non |  |  | Durée en semestres (1–12). |
| `study_mode` | ENUM study_mode | non | on_site |  |  |
| `teaching_language` | VARCHAR(50) | non | fr |  |  |
| `diploma_awarded` | VARCHAR(255) | oui |  |  |  |
| `status` | ENUM program_status | non | draft |  | draft / published / archived. Seules les formations published sont publiques. |
| `published_at` | TIMESTAMP WITH TIME ZONE | oui |  |  |  |
| `archived_at` | TIMESTAMP WITH TIME ZONE | oui |  |  |  |
| `search_vector` | TSVECTOR | oui | GENERATED |  | tsvector français généré (titre + résumé + description), index GIN. |
| `source_document_id` | BIGINT | non |  | FK → source_documents.id | Document source officiel de l'information (traçabilité obligatoire). |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- CHECK `ck_programs_code_format` : `code ~ '^[A-Z0-9_-]{2,40}$'`
- CHECK `ck_programs_duration_range` : `duration_semesters BETWEEN 1 AND 12`
- CHECK `ck_programs_published_has_date` : `(status <> 'published') OR (published_at IS NOT NULL)`
- INDEX `ix_programs_institution_id` (institution_id)
- INDEX `ix_programs_institution_status` (institution_id, status)
- INDEX `ix_programs_program_type_id` (program_type_id)
- INDEX `ix_programs_search_vector` (search_vector) USING gin
- INDEX `ix_programs_source_document_id` (source_document_id)
- INDEX `ix_programs_status` (status)

### `program_prerequisites`

Lien obligatoire vers le document source de l'information.

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `program_id` | BIGINT | non |  | FK → programs.id |  |
| `kind` | ENUM prerequisite_kind | non |  |  |  |
| `label` | VARCHAR(255) | non |  |  |  |
| `description` | TEXT | oui |  |  |  |
| `is_mandatory` | BOOLEAN | non | true |  |  |
| `position` | INTEGER | non | 0 |  |  |
| `source_document_id` | BIGINT | non |  | FK → source_documents.id | Document source officiel de l'information (traçabilité obligatoire). |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- UNIQUE `uq_program_prerequisites_program_id_label` (program_id, label)
- INDEX `ix_program_prerequisites_program_id` (program_id)
- INDEX `ix_program_prerequisites_source_document_id` (source_document_id)

### `admission_conditions`

Lien obligatoire vers le document source de l'information.

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `program_id` | BIGINT | non |  | FK → programs.id |  |
| `academic_year` | VARCHAR(9) | oui |  |  | NULL = valable pour toutes les années. |
| `kind` | ENUM admission_condition_kind | non |  |  |  |
| `description` | TEXT | non |  |  |  |
| `minimum_average` | NUMERIC(4, 2) | oui |  |  | Moyenne minimale sur 20. |
| `eligible_bac_sections` | VARCHAR(50)[] | oui |  |  |  |
| `position` | INTEGER | non | 0 |  |  |
| `source_document_id` | BIGINT | non |  | FK → source_documents.id | Document source officiel de l'information (traçabilité obligatoire). |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- CHECK `ck_admission_conditions_academic_year_format` : `academic_year IS NULL OR academic_year ~ '^[0-9]{4}-[0-9]{4}$'`
- CHECK `ck_admission_conditions_average_range` : `minimum_average IS NULL OR minimum_average BETWEEN 0 AND 20`
- UNIQUE `uq_admission_conditions_program_id_academic_year_position` (program_id, academic_year, position)
- INDEX `ix_admission_conditions_program_id` (program_id)
- INDEX `ix_admission_conditions_source_document_id` (source_document_id)

### `career_outcomes`

Débouchés professionnels.

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `program_id` | BIGINT | non |  | FK → programs.id |  |
| `title` | VARCHAR(255) | non |  |  |  |
| `sector` | VARCHAR(100) | oui |  |  |  |
| `description` | TEXT | oui |  |  |  |
| `source_document_id` | BIGINT | non |  | FK → source_documents.id | Document source officiel de l'information (traçabilité obligatoire). |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- UNIQUE `uq_career_outcomes_program_id_title` (program_id, title)
- INDEX `ix_career_outcomes_program_id` (program_id)
- INDEX `ix_career_outcomes_source_document_id` (source_document_id)

### `program_pathways`

Passerelle d'un parcours vers un autre (ex. Prépa -> Ingénierie).

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `from_program_id` | BIGINT | non |  | FK → programs.id |  |
| `to_program_id` | BIGINT | non |  | FK → programs.id |  |
| `entry_level` | VARCHAR(100) | oui |  |  |  |
| `conditions` | TEXT | oui |  |  |  |
| `source_document_id` | BIGINT | non |  | FK → source_documents.id | Document source officiel de l'information (traçabilité obligatoire). |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- CHECK `ck_program_pathways_distinct_programs` : `from_program_id <> to_program_id`
- UNIQUE `uq_program_pathways_from_program_id_to_program_id` (from_program_id, to_program_id)
- INDEX `ix_program_pathways_from_program_id` (from_program_id)
- INDEX `ix_program_pathways_source_document_id` (source_document_id)
- INDEX `ix_program_pathways_to_program_id` (to_program_id)

### `tuition_fees`

Lien obligatoire vers le document source de l'information.

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `program_id` | BIGINT | non |  | FK → programs.id |  |
| `academic_year` | VARCHAR(9) | non |  |  |  |
| `fee_type` | ENUM fee_type | non |  |  |  |
| `amount` | NUMERIC(12, 3) | non |  |  | Montant (NUMERIC 12,3 : le dinar compte 3 décimales). |
| `currency` | VARCHAR(3) | non | TND |  | Code ISO 4217 (TND par défaut). |
| `payment_terms` | TEXT | oui |  |  |  |
| `source_document_id` | BIGINT | non |  | FK → source_documents.id | Document source officiel de l'information (traçabilité obligatoire). |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- CHECK `ck_tuition_fees_academic_year_format` : `academic_year ~ '^[0-9]{4}-[0-9]{4}$'`
- CHECK `ck_tuition_fees_amount_positive` : `amount >= 0`
- CHECK `ck_tuition_fees_currency_iso4217` : `currency ~ '^[A-Z]{3}$'`
- UNIQUE `uq_tuition_fees_program_id_academic_year_fee_type` (program_id, academic_year, fee_type)
- INDEX `ix_tuition_fees_program_year` (program_id, academic_year)
- INDEX `ix_tuition_fees_source_document_id` (source_document_id)

### `admission_campaigns`

Lien obligatoire vers le document source de l'information.

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `institution_id` | BIGINT | non |  | FK → institutions.id |  |
| `academic_year` | VARCHAR(9) | non |  |  |  |
| `name` | VARCHAR(255) | non |  |  |  |
| `opens_at` | TIMESTAMP WITH TIME ZONE | non |  |  |  |
| `closes_at` | TIMESTAMP WITH TIME ZONE | non |  |  |  |
| `status` | ENUM campaign_status | non | planned |  |  |
| `source_document_id` | BIGINT | non |  | FK → source_documents.id | Document source officiel de l'information (traçabilité obligatoire). |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- CHECK `ck_admission_campaigns_academic_year_format` : `academic_year ~ '^[0-9]{4}-[0-9]{4}$'`
- CHECK `ck_admission_campaigns_dates_order` : `closes_at > opens_at`
- UNIQUE `uq_admission_campaigns_institution_id_academic_year_name` (institution_id, academic_year, name)
- INDEX `ix_admission_campaigns_institution_id` (institution_id)
- INDEX `ix_admission_campaigns_source_document_id` (source_document_id)

### `source_documents`

Document officiel (brochure, FAQ, procédure, programme). Ancre de traçabilité + RAG (SA-14).

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `institution_id` | BIGINT | oui |  | FK → institutions.id |  |
| `title` | VARCHAR(255) | non |  |  |  |
| `doc_type` | ENUM source_document_type | non |  |  |  |
| `version` | VARCHAR(50) | non |  |  |  |
| `content_hash` | VARCHAR(64) | non |  |  |  |
| `status` | ENUM source_document_status | non | draft |  |  |
| `uri` | VARCHAR(1024) | oui |  |  |  |
| `language` | VARCHAR(10) | non | fr |  |  |
| `document_date` | DATE | oui |  |  |  |
| `last_synced_at` | TIMESTAMP WITH TIME ZONE | oui |  |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- CHECK `ck_source_documents_content_hash_sha256` : `content_hash ~ '^[0-9a-f]{64}$'`
- UNIQUE `uq_source_documents_title_version` (title, version)
- INDEX `ix_source_documents_institution_id` (institution_id)

## SA-13 — Utilisateurs et candidatures

### `users`

Base class used for declarative class definitions. The :class:`_orm.DeclarativeBase` allows for the creation of new declarative bases in such a way that is compatible with type checkers:: from sqlalchemy.orm import DeclarativeBase class Base(DeclarativeBase): pass The above ``Base`` class is now usable as the base for new declarative mappings. The superclass makes use of the ``__init_subclass__()`` method to set up new classes and metaclasses aren't used. When first used, the :class:`_orm.DeclarativeBase` class instantiates a new :class:`_orm.registry` to be used with the base, assuming one was not provided explicitly. The :class:`_orm.DeclarativeBase` class supports class-level attributes which act as parameters for the construction of this registry; such as to indicate a specific :class:`_schema.MetaData` collection as well as a specific value for :paramref:`_orm.registry.type_annotation_map`:: from typing_extensions import Annotated from sqlalchemy import BigInteger from sqlalchemy import MetaData from sqlalchemy import String from sqlalchemy.orm import DeclarativeBase bigint = Annotated[int, "bigint"] my_metadata = MetaData() class Base(DeclarativeBase): metadata = my_metadata type_annotation_map = { str: String().with_variant(String(255), "mysql", "mariadb"), bigint: BigInteger(), } Class-level attributes which may be specified include: :param metadata: optional :class:`_schema.MetaData` collection. If a :class:`_orm.registry` is constructed automatically, this :class:`_schema.MetaData` collection will be used to construct it. Otherwise, the local :class:`_schema.MetaData` collection will supersede that used by an existing :class:`_orm.registry` passed using the :paramref:`_orm.DeclarativeBase.registry` parameter. :param type_annotation_map: optional type annotation map that will be passed to the :class:`_orm.registry` as :paramref:`_orm.registry.type_annotation_map`. :param registry: supply a pre-existing :class:`_orm.registry` directly. .. versionadded:: 2.0 Added :class:`.DeclarativeBase`, so that declarative base classes may be constructed in such a way that is also recognized by :pep:`484` type checkers. As a result, :class:`.DeclarativeBase` and other subclassing-oriented APIs should be seen as superseding previous "class returned by a function" APIs, namely :func:`_orm.declarative_base` and :meth:`_orm.registry.generate_base`, where the base class returned cannot be recognized by type checkers without using plugins. **__init__ behavior** In a plain Python class, the base-most ``__init__()`` method in the class hierarchy is ``object.__init__()``, which accepts no arguments. However, when the :class:`_orm.DeclarativeBase` subclass is first declared, the class is given an ``__init__()`` method that links to the :paramref:`_orm.registry.constructor` constructor function, if no ``__init__()`` method is already present; this is the usual declarative constructor that will assign keyword arguments as attributes on the instance, assuming those attributes are established at the class level (i.e. are mapped, or are linked to a descriptor). This constructor is **never accessed by a mapped class without being called explicitly via super()**, as mapped classes are themselves given an ``__init__()`` method directly which calls :paramref:`_orm.registry.constructor`, so in the default case works independently of what the base-most ``__init__()`` method does. .. versionchanged:: 2.0.1 :class:`_orm.DeclarativeBase` has a default constructor that links to :paramref:`_orm.registry.constructor` by default, so that calls to ``super().__init__()`` can access this constructor. Previously, due to an implementation mistake, this default constructor was missing, and calling ``super().__init__()`` would invoke ``object.__init__()``. The :class:`_orm.DeclarativeBase` subclass may also declare an explicit ``__init__()`` method which will replace the use of the :paramref:`_orm.registry.constructor` function at this level:: class Base(DeclarativeBase): def __init__(self, id=None): self.id = id Mapped classes still will not invoke this constructor implicitly; it remains only accessible by calling ``super().__init__()``:: class MyClass(Base): def __init__(self, id=None, name=None): self.name = name super().__init__(id=id) Note that this is a different behavior from what functions like the legacy :func:`_orm.declarative_base` would do; the base created by those functions would always install :paramref:`_orm.registry.constructor` for ``__init__()``.

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `email` | VARCHAR(255) | non |  | UNIQUE |  |
| `password_hash` | VARCHAR(255) | oui |  |  | Hash bcrypt/argon2 uniquement (CHECK). NULL pour un compte technique. |
| `full_name` | VARCHAR(255) | non |  |  |  |
| `is_active` | BOOLEAN | non | true |  |  |
| `is_service_account` | BOOLEAN | non | false |  | Compte technique (agent IA) : interdit de décision. |
| `last_login_at` | TIMESTAMP WITH TIME ZONE | oui |  |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- CHECK `ck_users_email_format` : `position('@' in email) > 1`
- CHECK `ck_users_email_lowercase` : `email = lower(email)`
- CHECK `ck_users_password_hashed` : `password_hash IS NULL OR password_hash ~ '^\$(2[aby]|argon2id?)\$'`
- CHECK `ck_users_service_account_no_password` : `NOT is_service_account OR password_hash IS NULL`

### `roles`

Base class used for declarative class definitions. The :class:`_orm.DeclarativeBase` allows for the creation of new declarative bases in such a way that is compatible with type checkers:: from sqlalchemy.orm import DeclarativeBase class Base(DeclarativeBase): pass The above ``Base`` class is now usable as the base for new declarative mappings. The superclass makes use of the ``__init_subclass__()`` method to set up new classes and metaclasses aren't used. When first used, the :class:`_orm.DeclarativeBase` class instantiates a new :class:`_orm.registry` to be used with the base, assuming one was not provided explicitly. The :class:`_orm.DeclarativeBase` class supports class-level attributes which act as parameters for the construction of this registry; such as to indicate a specific :class:`_schema.MetaData` collection as well as a specific value for :paramref:`_orm.registry.type_annotation_map`:: from typing_extensions import Annotated from sqlalchemy import BigInteger from sqlalchemy import MetaData from sqlalchemy import String from sqlalchemy.orm import DeclarativeBase bigint = Annotated[int, "bigint"] my_metadata = MetaData() class Base(DeclarativeBase): metadata = my_metadata type_annotation_map = { str: String().with_variant(String(255), "mysql", "mariadb"), bigint: BigInteger(), } Class-level attributes which may be specified include: :param metadata: optional :class:`_schema.MetaData` collection. If a :class:`_orm.registry` is constructed automatically, this :class:`_schema.MetaData` collection will be used to construct it. Otherwise, the local :class:`_schema.MetaData` collection will supersede that used by an existing :class:`_orm.registry` passed using the :paramref:`_orm.DeclarativeBase.registry` parameter. :param type_annotation_map: optional type annotation map that will be passed to the :class:`_orm.registry` as :paramref:`_orm.registry.type_annotation_map`. :param registry: supply a pre-existing :class:`_orm.registry` directly. .. versionadded:: 2.0 Added :class:`.DeclarativeBase`, so that declarative base classes may be constructed in such a way that is also recognized by :pep:`484` type checkers. As a result, :class:`.DeclarativeBase` and other subclassing-oriented APIs should be seen as superseding previous "class returned by a function" APIs, namely :func:`_orm.declarative_base` and :meth:`_orm.registry.generate_base`, where the base class returned cannot be recognized by type checkers without using plugins. **__init__ behavior** In a plain Python class, the base-most ``__init__()`` method in the class hierarchy is ``object.__init__()``, which accepts no arguments. However, when the :class:`_orm.DeclarativeBase` subclass is first declared, the class is given an ``__init__()`` method that links to the :paramref:`_orm.registry.constructor` constructor function, if no ``__init__()`` method is already present; this is the usual declarative constructor that will assign keyword arguments as attributes on the instance, assuming those attributes are established at the class level (i.e. are mapped, or are linked to a descriptor). This constructor is **never accessed by a mapped class without being called explicitly via super()**, as mapped classes are themselves given an ``__init__()`` method directly which calls :paramref:`_orm.registry.constructor`, so in the default case works independently of what the base-most ``__init__()`` method does. .. versionchanged:: 2.0.1 :class:`_orm.DeclarativeBase` has a default constructor that links to :paramref:`_orm.registry.constructor` by default, so that calls to ``super().__init__()`` can access this constructor. Previously, due to an implementation mistake, this default constructor was missing, and calling ``super().__init__()`` would invoke ``object.__init__()``. The :class:`_orm.DeclarativeBase` subclass may also declare an explicit ``__init__()`` method which will replace the use of the :paramref:`_orm.registry.constructor` function at this level:: class Base(DeclarativeBase): def __init__(self, id=None): self.id = id Mapped classes still will not invoke this constructor implicitly; it remains only accessible by calling ``super().__init__()``:: class MyClass(Base): def __init__(self, id=None, name=None): self.name = name super().__init__(id=id) Note that this is a different behavior from what functions like the legacy :func:`_orm.declarative_base` would do; the base created by those functions would always install :paramref:`_orm.registry.constructor` for ``__init__()``.

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `code` | ENUM role_code | non |  | UNIQUE |  |
| `label` | VARCHAR(100) | non |  |  |  |
| `institution_id` | BIGINT | oui |  | FK → institutions.id | Périmètre du rôle (IIT/ISB) ; NULL = transverse. |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |

### `user_roles`

Base class used for declarative class definitions. The :class:`_orm.DeclarativeBase` allows for the creation of new declarative bases in such a way that is compatible with type checkers:: from sqlalchemy.orm import DeclarativeBase class Base(DeclarativeBase): pass The above ``Base`` class is now usable as the base for new declarative mappings. The superclass makes use of the ``__init_subclass__()`` method to set up new classes and metaclasses aren't used. When first used, the :class:`_orm.DeclarativeBase` class instantiates a new :class:`_orm.registry` to be used with the base, assuming one was not provided explicitly. The :class:`_orm.DeclarativeBase` class supports class-level attributes which act as parameters for the construction of this registry; such as to indicate a specific :class:`_schema.MetaData` collection as well as a specific value for :paramref:`_orm.registry.type_annotation_map`:: from typing_extensions import Annotated from sqlalchemy import BigInteger from sqlalchemy import MetaData from sqlalchemy import String from sqlalchemy.orm import DeclarativeBase bigint = Annotated[int, "bigint"] my_metadata = MetaData() class Base(DeclarativeBase): metadata = my_metadata type_annotation_map = { str: String().with_variant(String(255), "mysql", "mariadb"), bigint: BigInteger(), } Class-level attributes which may be specified include: :param metadata: optional :class:`_schema.MetaData` collection. If a :class:`_orm.registry` is constructed automatically, this :class:`_schema.MetaData` collection will be used to construct it. Otherwise, the local :class:`_schema.MetaData` collection will supersede that used by an existing :class:`_orm.registry` passed using the :paramref:`_orm.DeclarativeBase.registry` parameter. :param type_annotation_map: optional type annotation map that will be passed to the :class:`_orm.registry` as :paramref:`_orm.registry.type_annotation_map`. :param registry: supply a pre-existing :class:`_orm.registry` directly. .. versionadded:: 2.0 Added :class:`.DeclarativeBase`, so that declarative base classes may be constructed in such a way that is also recognized by :pep:`484` type checkers. As a result, :class:`.DeclarativeBase` and other subclassing-oriented APIs should be seen as superseding previous "class returned by a function" APIs, namely :func:`_orm.declarative_base` and :meth:`_orm.registry.generate_base`, where the base class returned cannot be recognized by type checkers without using plugins. **__init__ behavior** In a plain Python class, the base-most ``__init__()`` method in the class hierarchy is ``object.__init__()``, which accepts no arguments. However, when the :class:`_orm.DeclarativeBase` subclass is first declared, the class is given an ``__init__()`` method that links to the :paramref:`_orm.registry.constructor` constructor function, if no ``__init__()`` method is already present; this is the usual declarative constructor that will assign keyword arguments as attributes on the instance, assuming those attributes are established at the class level (i.e. are mapped, or are linked to a descriptor). This constructor is **never accessed by a mapped class without being called explicitly via super()**, as mapped classes are themselves given an ``__init__()`` method directly which calls :paramref:`_orm.registry.constructor`, so in the default case works independently of what the base-most ``__init__()`` method does. .. versionchanged:: 2.0.1 :class:`_orm.DeclarativeBase` has a default constructor that links to :paramref:`_orm.registry.constructor` by default, so that calls to ``super().__init__()`` can access this constructor. Previously, due to an implementation mistake, this default constructor was missing, and calling ``super().__init__()`` would invoke ``object.__init__()``. The :class:`_orm.DeclarativeBase` subclass may also declare an explicit ``__init__()`` method which will replace the use of the :paramref:`_orm.registry.constructor` function at this level:: class Base(DeclarativeBase): def __init__(self, id=None): self.id = id Mapped classes still will not invoke this constructor implicitly; it remains only accessible by calling ``super().__init__()``:: class MyClass(Base): def __init__(self, id=None, name=None): self.name = name super().__init__(id=id) Note that this is a different behavior from what functions like the legacy :func:`_orm.declarative_base` would do; the base created by those functions would always install :paramref:`_orm.registry.constructor` for ``__init__()``.

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `user_id` | BIGINT | non |  | PK, FK → users.id |  |
| `role_id` | BIGINT | non |  | PK, FK → roles.id |  |
| `granted_at` | TIMESTAMP WITH TIME ZONE | non | now() |  |  |
| `granted_by` | BIGINT | oui |  | FK → users.id |  |

Contraintes et index :

- INDEX `ix_user_roles_role_id` (role_id)

### `candidates`

Identité minimale du candidat (minimisation des données personnelles).

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `user_id` | BIGINT | non |  | FK → users.id, UNIQUE |  |
| `first_name` | VARCHAR(100) | non |  |  |  |
| `last_name` | VARCHAR(100) | non |  |  |  |
| `phone` | VARCHAR(20) | oui |  |  |  |
| `birth_year` | SMALLINT | oui |  |  | Année de naissance seule (minimisation). |
| `governorate` | VARCHAR(100) | oui |  |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- CHECK `ck_candidates_birth_year_range` : `birth_year IS NULL OR birth_year BETWEEN 1950 AND 2020`
- CHECK `ck_candidates_phone_format` : `phone IS NULL OR phone ~ '^\+?[0-9 ]{8,20}$'`

### `candidate_profiles`

Base class used for declarative class definitions. The :class:`_orm.DeclarativeBase` allows for the creation of new declarative bases in such a way that is compatible with type checkers:: from sqlalchemy.orm import DeclarativeBase class Base(DeclarativeBase): pass The above ``Base`` class is now usable as the base for new declarative mappings. The superclass makes use of the ``__init_subclass__()`` method to set up new classes and metaclasses aren't used. When first used, the :class:`_orm.DeclarativeBase` class instantiates a new :class:`_orm.registry` to be used with the base, assuming one was not provided explicitly. The :class:`_orm.DeclarativeBase` class supports class-level attributes which act as parameters for the construction of this registry; such as to indicate a specific :class:`_schema.MetaData` collection as well as a specific value for :paramref:`_orm.registry.type_annotation_map`:: from typing_extensions import Annotated from sqlalchemy import BigInteger from sqlalchemy import MetaData from sqlalchemy import String from sqlalchemy.orm import DeclarativeBase bigint = Annotated[int, "bigint"] my_metadata = MetaData() class Base(DeclarativeBase): metadata = my_metadata type_annotation_map = { str: String().with_variant(String(255), "mysql", "mariadb"), bigint: BigInteger(), } Class-level attributes which may be specified include: :param metadata: optional :class:`_schema.MetaData` collection. If a :class:`_orm.registry` is constructed automatically, this :class:`_schema.MetaData` collection will be used to construct it. Otherwise, the local :class:`_schema.MetaData` collection will supersede that used by an existing :class:`_orm.registry` passed using the :paramref:`_orm.DeclarativeBase.registry` parameter. :param type_annotation_map: optional type annotation map that will be passed to the :class:`_orm.registry` as :paramref:`_orm.registry.type_annotation_map`. :param registry: supply a pre-existing :class:`_orm.registry` directly. .. versionadded:: 2.0 Added :class:`.DeclarativeBase`, so that declarative base classes may be constructed in such a way that is also recognized by :pep:`484` type checkers. As a result, :class:`.DeclarativeBase` and other subclassing-oriented APIs should be seen as superseding previous "class returned by a function" APIs, namely :func:`_orm.declarative_base` and :meth:`_orm.registry.generate_base`, where the base class returned cannot be recognized by type checkers without using plugins. **__init__ behavior** In a plain Python class, the base-most ``__init__()`` method in the class hierarchy is ``object.__init__()``, which accepts no arguments. However, when the :class:`_orm.DeclarativeBase` subclass is first declared, the class is given an ``__init__()`` method that links to the :paramref:`_orm.registry.constructor` constructor function, if no ``__init__()`` method is already present; this is the usual declarative constructor that will assign keyword arguments as attributes on the instance, assuming those attributes are established at the class level (i.e. are mapped, or are linked to a descriptor). This constructor is **never accessed by a mapped class without being called explicitly via super()**, as mapped classes are themselves given an ``__init__()`` method directly which calls :paramref:`_orm.registry.constructor`, so in the default case works independently of what the base-most ``__init__()`` method does. .. versionchanged:: 2.0.1 :class:`_orm.DeclarativeBase` has a default constructor that links to :paramref:`_orm.registry.constructor` by default, so that calls to ``super().__init__()`` can access this constructor. Previously, due to an implementation mistake, this default constructor was missing, and calling ``super().__init__()`` would invoke ``object.__init__()``. The :class:`_orm.DeclarativeBase` subclass may also declare an explicit ``__init__()`` method which will replace the use of the :paramref:`_orm.registry.constructor` function at this level:: class Base(DeclarativeBase): def __init__(self, id=None): self.id = id Mapped classes still will not invoke this constructor implicitly; it remains only accessible by calling ``super().__init__()``:: class MyClass(Base): def __init__(self, id=None, name=None): self.name = name super().__init__(id=id) Note that this is a different behavior from what functions like the legacy :func:`_orm.declarative_base` would do; the base created by those functions would always install :paramref:`_orm.registry.constructor` for ``__init__()``.

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `candidate_id` | BIGINT | non |  | FK → candidates.id, UNIQUE |  |
| `education_level` | ENUM education_level | oui |  |  |  |
| `bac_section` | VARCHAR(50) | oui |  |  |  |
| `bac_year` | SMALLINT | oui |  |  |  |
| `bac_average` | NUMERIC(4, 2) | oui |  |  |  |
| `current_program` | VARCHAR(255) | oui |  |  |  |
| `interests` | VARCHAR(100)[] | non | {} |  |  |
| `preferred_subjects` | VARCHAR(100)[] | non | {} |  |  |
| `goals` | TEXT | oui |  |  |  |
| `constraints` | TEXT | oui |  |  |  |
| `preferred_language` | ENUM message_language | oui |  |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- CHECK `ck_candidate_profiles_bac_average_range` : `bac_average IS NULL OR bac_average BETWEEN 0 AND 20`
- CHECK `ck_candidate_profiles_bac_year_range` : `bac_year IS NULL OR bac_year BETWEEN 1980 AND 2100`

### `conversations`

Conversation chatbot. Visiteur anonyme : candidate_id NULL, identifié par session_token_hash. À la création du compte, candidate_id est renseigné (attached_at).

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `candidate_id` | BIGINT | oui |  | FK → candidates.id | NULL pour un visiteur anonyme ; renseigné à la création du compte. |
| `session_token_hash` | VARCHAR(64) | non |  | UNIQUE | SHA-256 du jeton de session (jamais le jeton brut). |
| `status` | ENUM conversation_status | non | active |  |  |
| `started_at` | TIMESTAMP WITH TIME ZONE | non | now() |  |  |
| `last_message_at` | TIMESTAMP WITH TIME ZONE | oui |  |  |  |
| `attached_at` | TIMESTAMP WITH TIME ZONE | oui |  |  |  |
| `memory` | JSONB | non | '{}'::jsonb |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- CHECK `ck_conversations_attached_has_date` : `candidate_id IS NULL OR attached_at IS NOT NULL`
- CHECK `ck_conversations_memory_is_object` : `jsonb_typeof(memory) = 'object'`
- CHECK `ck_conversations_session_token_sha256` : `session_token_hash ~ '^[0-9a-f]{64}$'`
- INDEX `ix_conversations_candidate_id` (candidate_id)

### `messages`

Base class used for declarative class definitions. The :class:`_orm.DeclarativeBase` allows for the creation of new declarative bases in such a way that is compatible with type checkers:: from sqlalchemy.orm import DeclarativeBase class Base(DeclarativeBase): pass The above ``Base`` class is now usable as the base for new declarative mappings. The superclass makes use of the ``__init_subclass__()`` method to set up new classes and metaclasses aren't used. When first used, the :class:`_orm.DeclarativeBase` class instantiates a new :class:`_orm.registry` to be used with the base, assuming one was not provided explicitly. The :class:`_orm.DeclarativeBase` class supports class-level attributes which act as parameters for the construction of this registry; such as to indicate a specific :class:`_schema.MetaData` collection as well as a specific value for :paramref:`_orm.registry.type_annotation_map`:: from typing_extensions import Annotated from sqlalchemy import BigInteger from sqlalchemy import MetaData from sqlalchemy import String from sqlalchemy.orm import DeclarativeBase bigint = Annotated[int, "bigint"] my_metadata = MetaData() class Base(DeclarativeBase): metadata = my_metadata type_annotation_map = { str: String().with_variant(String(255), "mysql", "mariadb"), bigint: BigInteger(), } Class-level attributes which may be specified include: :param metadata: optional :class:`_schema.MetaData` collection. If a :class:`_orm.registry` is constructed automatically, this :class:`_schema.MetaData` collection will be used to construct it. Otherwise, the local :class:`_schema.MetaData` collection will supersede that used by an existing :class:`_orm.registry` passed using the :paramref:`_orm.DeclarativeBase.registry` parameter. :param type_annotation_map: optional type annotation map that will be passed to the :class:`_orm.registry` as :paramref:`_orm.registry.type_annotation_map`. :param registry: supply a pre-existing :class:`_orm.registry` directly. .. versionadded:: 2.0 Added :class:`.DeclarativeBase`, so that declarative base classes may be constructed in such a way that is also recognized by :pep:`484` type checkers. As a result, :class:`.DeclarativeBase` and other subclassing-oriented APIs should be seen as superseding previous "class returned by a function" APIs, namely :func:`_orm.declarative_base` and :meth:`_orm.registry.generate_base`, where the base class returned cannot be recognized by type checkers without using plugins. **__init__ behavior** In a plain Python class, the base-most ``__init__()`` method in the class hierarchy is ``object.__init__()``, which accepts no arguments. However, when the :class:`_orm.DeclarativeBase` subclass is first declared, the class is given an ``__init__()`` method that links to the :paramref:`_orm.registry.constructor` constructor function, if no ``__init__()`` method is already present; this is the usual declarative constructor that will assign keyword arguments as attributes on the instance, assuming those attributes are established at the class level (i.e. are mapped, or are linked to a descriptor). This constructor is **never accessed by a mapped class without being called explicitly via super()**, as mapped classes are themselves given an ``__init__()`` method directly which calls :paramref:`_orm.registry.constructor`, so in the default case works independently of what the base-most ``__init__()`` method does. .. versionchanged:: 2.0.1 :class:`_orm.DeclarativeBase` has a default constructor that links to :paramref:`_orm.registry.constructor` by default, so that calls to ``super().__init__()`` can access this constructor. Previously, due to an implementation mistake, this default constructor was missing, and calling ``super().__init__()`` would invoke ``object.__init__()``. The :class:`_orm.DeclarativeBase` subclass may also declare an explicit ``__init__()`` method which will replace the use of the :paramref:`_orm.registry.constructor` function at this level:: class Base(DeclarativeBase): def __init__(self, id=None): self.id = id Mapped classes still will not invoke this constructor implicitly; it remains only accessible by calling ``super().__init__()``:: class MyClass(Base): def __init__(self, id=None, name=None): self.name = name super().__init__(id=id) Note that this is a different behavior from what functions like the legacy :func:`_orm.declarative_base` would do; the base created by those functions would always install :paramref:`_orm.registry.constructor` for ``__init__()``.

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `conversation_id` | BIGINT | non |  | FK → conversations.id |  |
| `sequence` | INTEGER | non |  |  |  |
| `sender` | ENUM message_sender | non |  |  |  |
| `channel` | ENUM message_channel | non | text |  |  |
| `content` | TEXT | non |  |  | Texte saisi ou transcription Whisper. |
| `detected_language` | ENUM message_language | non | unknown |  | fr, ar, tn_darija, arabizi, en, mixed, unknown. |
| `language_confidence` | NUMERIC(3, 2) | oui |  |  |  |
| `audio_uri` | VARCHAR(1024) | oui |  |  |  |
| `audio_duration_ms` | INTEGER | oui |  |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- CHECK `ck_messages_audio_has_uri` : `channel <> 'audio' OR audio_uri IS NOT NULL`
- CHECK `ck_messages_confidence_range` : `language_confidence IS NULL OR language_confidence BETWEEN 0 AND 1`
- CHECK `ck_messages_sequence_positive` : `sequence >= 1`
- UNIQUE `uq_messages_conversation_id_sequence` (conversation_id, sequence)

### `recommendations`

Recommandation de formation produite par l'agent IA, à valider par un responsable.

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `candidate_id` | BIGINT | oui |  | FK → candidates.id |  |
| `conversation_id` | BIGINT | oui |  | FK → conversations.id |  |
| `program_id` | BIGINT | non |  | FK → programs.id |  |
| `rank` | SMALLINT | non |  |  |  |
| `compatibility_score` | NUMERIC(5, 2) | non |  |  |  |
| `justification` | TEXT | non |  |  |  |
| `cited_sources` | JSONB | oui |  |  |  |
| `model_name` | VARCHAR(100) | oui |  |  |  |
| `review_status` | ENUM review_status | non | pending |  | pending / confirmed / adjusted (revue humaine obligatoire). |
| `reviewed_by` | BIGINT | oui |  | FK → users.id | Responsable humain (trigger assert_human_responsable). |
| `reviewed_at` | TIMESTAMP WITH TIME ZONE | oui |  |  |  |
| `review_comment` | TEXT | oui |  |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- CHECK `ck_recommendations_adjusted_has_comment` : `review_status <> 'adjusted' OR review_comment IS NOT NULL`
- CHECK `ck_recommendations_has_subject` : `candidate_id IS NOT NULL OR conversation_id IS NOT NULL`
- CHECK `ck_recommendations_rank_range` : `rank BETWEEN 1 AND 3`
- CHECK `ck_recommendations_review_consistency` : `(review_status = 'pending' AND reviewed_by IS NULL AND reviewed_at IS NULL) OR (review_status <> 'pending' AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)`
- CHECK `ck_recommendations_score_range` : `compatibility_score BETWEEN 0 AND 100`
- INDEX `ix_recommendations_candidate_id` (candidate_id)
- INDEX `ix_recommendations_conversation_id` (conversation_id)
- INDEX `ix_recommendations_program_id` (program_id)
- INDEX `ix_recommendations_review_status` (review_status)

### `consents`

Base class used for declarative class definitions. The :class:`_orm.DeclarativeBase` allows for the creation of new declarative bases in such a way that is compatible with type checkers:: from sqlalchemy.orm import DeclarativeBase class Base(DeclarativeBase): pass The above ``Base`` class is now usable as the base for new declarative mappings. The superclass makes use of the ``__init_subclass__()`` method to set up new classes and metaclasses aren't used. When first used, the :class:`_orm.DeclarativeBase` class instantiates a new :class:`_orm.registry` to be used with the base, assuming one was not provided explicitly. The :class:`_orm.DeclarativeBase` class supports class-level attributes which act as parameters for the construction of this registry; such as to indicate a specific :class:`_schema.MetaData` collection as well as a specific value for :paramref:`_orm.registry.type_annotation_map`:: from typing_extensions import Annotated from sqlalchemy import BigInteger from sqlalchemy import MetaData from sqlalchemy import String from sqlalchemy.orm import DeclarativeBase bigint = Annotated[int, "bigint"] my_metadata = MetaData() class Base(DeclarativeBase): metadata = my_metadata type_annotation_map = { str: String().with_variant(String(255), "mysql", "mariadb"), bigint: BigInteger(), } Class-level attributes which may be specified include: :param metadata: optional :class:`_schema.MetaData` collection. If a :class:`_orm.registry` is constructed automatically, this :class:`_schema.MetaData` collection will be used to construct it. Otherwise, the local :class:`_schema.MetaData` collection will supersede that used by an existing :class:`_orm.registry` passed using the :paramref:`_orm.DeclarativeBase.registry` parameter. :param type_annotation_map: optional type annotation map that will be passed to the :class:`_orm.registry` as :paramref:`_orm.registry.type_annotation_map`. :param registry: supply a pre-existing :class:`_orm.registry` directly. .. versionadded:: 2.0 Added :class:`.DeclarativeBase`, so that declarative base classes may be constructed in such a way that is also recognized by :pep:`484` type checkers. As a result, :class:`.DeclarativeBase` and other subclassing-oriented APIs should be seen as superseding previous "class returned by a function" APIs, namely :func:`_orm.declarative_base` and :meth:`_orm.registry.generate_base`, where the base class returned cannot be recognized by type checkers without using plugins. **__init__ behavior** In a plain Python class, the base-most ``__init__()`` method in the class hierarchy is ``object.__init__()``, which accepts no arguments. However, when the :class:`_orm.DeclarativeBase` subclass is first declared, the class is given an ``__init__()`` method that links to the :paramref:`_orm.registry.constructor` constructor function, if no ``__init__()`` method is already present; this is the usual declarative constructor that will assign keyword arguments as attributes on the instance, assuming those attributes are established at the class level (i.e. are mapped, or are linked to a descriptor). This constructor is **never accessed by a mapped class without being called explicitly via super()**, as mapped classes are themselves given an ``__init__()`` method directly which calls :paramref:`_orm.registry.constructor`, so in the default case works independently of what the base-most ``__init__()`` method does. .. versionchanged:: 2.0.1 :class:`_orm.DeclarativeBase` has a default constructor that links to :paramref:`_orm.registry.constructor` by default, so that calls to ``super().__init__()`` can access this constructor. Previously, due to an implementation mistake, this default constructor was missing, and calling ``super().__init__()`` would invoke ``object.__init__()``. The :class:`_orm.DeclarativeBase` subclass may also declare an explicit ``__init__()`` method which will replace the use of the :paramref:`_orm.registry.constructor` function at this level:: class Base(DeclarativeBase): def __init__(self, id=None): self.id = id Mapped classes still will not invoke this constructor implicitly; it remains only accessible by calling ``super().__init__()``:: class MyClass(Base): def __init__(self, id=None, name=None): self.name = name super().__init__(id=id) Note that this is a different behavior from what functions like the legacy :func:`_orm.declarative_base` would do; the base created by those functions would always install :paramref:`_orm.registry.constructor` for ``__init__()``.

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `user_id` | BIGINT | oui |  | FK → users.id |  |
| `conversation_id` | BIGINT | oui |  | FK → conversations.id |  |
| `consent_type` | ENUM consent_type | non |  |  |  |
| `policy_version` | VARCHAR(20) | non |  |  |  |
| `granted` | BOOLEAN | non |  |  |  |
| `granted_at` | TIMESTAMP WITH TIME ZONE | non | now() |  |  |
| `revoked_at` | TIMESTAMP WITH TIME ZONE | oui |  |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- CHECK `ck_consents_has_subject` : `user_id IS NOT NULL OR conversation_id IS NOT NULL`
- CHECK `ck_consents_revocation_after_grant` : `revoked_at IS NULL OR revoked_at >= granted_at`
- INDEX `ix_consents_conversation_id` (conversation_id)
- INDEX `ix_consents_user_type` (user_id, consent_type)

### `dossiers`

Dossier de candidature : regroupe préinscriptions, équivalences, QCM, rendez-vous, décisions. Le périmètre établissement se déduit de la campagne (admission_campaigns.institution_id).

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `candidate_id` | BIGINT | non |  | FK → candidates.id |  |
| `campaign_id` | BIGINT | non |  | FK → admission_campaigns.id |  |
| `status` | ENUM dossier_status | non | open |  |  |
| `ai_summary` | TEXT | oui |  |  | Résumé généré par l'agent IA (indicatif, jamais une décision). |
| `ai_summary_updated_at` | TIMESTAMP WITH TIME ZONE | oui |  |  |  |
| `closed_at` | TIMESTAMP WITH TIME ZONE | oui |  |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- CHECK `ck_dossiers_ai_summary_has_date` : `(ai_summary IS NULL) = (ai_summary_updated_at IS NULL)`
- INDEX `ix_dossiers_campaign_status` (campaign_id, status)
- INDEX `ix_dossiers_candidate_id` (candidate_id)
- UNIQUE INDEX `uq_dossiers_active_candidate_campaign` (candidate_id, campaign_id) WHERE status NOT IN ('enrolled', 'withdrawn', 'closed')

### `preinscriptions`

Base class used for declarative class definitions. The :class:`_orm.DeclarativeBase` allows for the creation of new declarative bases in such a way that is compatible with type checkers:: from sqlalchemy.orm import DeclarativeBase class Base(DeclarativeBase): pass The above ``Base`` class is now usable as the base for new declarative mappings. The superclass makes use of the ``__init_subclass__()`` method to set up new classes and metaclasses aren't used. When first used, the :class:`_orm.DeclarativeBase` class instantiates a new :class:`_orm.registry` to be used with the base, assuming one was not provided explicitly. The :class:`_orm.DeclarativeBase` class supports class-level attributes which act as parameters for the construction of this registry; such as to indicate a specific :class:`_schema.MetaData` collection as well as a specific value for :paramref:`_orm.registry.type_annotation_map`:: from typing_extensions import Annotated from sqlalchemy import BigInteger from sqlalchemy import MetaData from sqlalchemy import String from sqlalchemy.orm import DeclarativeBase bigint = Annotated[int, "bigint"] my_metadata = MetaData() class Base(DeclarativeBase): metadata = my_metadata type_annotation_map = { str: String().with_variant(String(255), "mysql", "mariadb"), bigint: BigInteger(), } Class-level attributes which may be specified include: :param metadata: optional :class:`_schema.MetaData` collection. If a :class:`_orm.registry` is constructed automatically, this :class:`_schema.MetaData` collection will be used to construct it. Otherwise, the local :class:`_schema.MetaData` collection will supersede that used by an existing :class:`_orm.registry` passed using the :paramref:`_orm.DeclarativeBase.registry` parameter. :param type_annotation_map: optional type annotation map that will be passed to the :class:`_orm.registry` as :paramref:`_orm.registry.type_annotation_map`. :param registry: supply a pre-existing :class:`_orm.registry` directly. .. versionadded:: 2.0 Added :class:`.DeclarativeBase`, so that declarative base classes may be constructed in such a way that is also recognized by :pep:`484` type checkers. As a result, :class:`.DeclarativeBase` and other subclassing-oriented APIs should be seen as superseding previous "class returned by a function" APIs, namely :func:`_orm.declarative_base` and :meth:`_orm.registry.generate_base`, where the base class returned cannot be recognized by type checkers without using plugins. **__init__ behavior** In a plain Python class, the base-most ``__init__()`` method in the class hierarchy is ``object.__init__()``, which accepts no arguments. However, when the :class:`_orm.DeclarativeBase` subclass is first declared, the class is given an ``__init__()`` method that links to the :paramref:`_orm.registry.constructor` constructor function, if no ``__init__()`` method is already present; this is the usual declarative constructor that will assign keyword arguments as attributes on the instance, assuming those attributes are established at the class level (i.e. are mapped, or are linked to a descriptor). This constructor is **never accessed by a mapped class without being called explicitly via super()**, as mapped classes are themselves given an ``__init__()`` method directly which calls :paramref:`_orm.registry.constructor`, so in the default case works independently of what the base-most ``__init__()`` method does. .. versionchanged:: 2.0.1 :class:`_orm.DeclarativeBase` has a default constructor that links to :paramref:`_orm.registry.constructor` by default, so that calls to ``super().__init__()`` can access this constructor. Previously, due to an implementation mistake, this default constructor was missing, and calling ``super().__init__()`` would invoke ``object.__init__()``. The :class:`_orm.DeclarativeBase` subclass may also declare an explicit ``__init__()`` method which will replace the use of the :paramref:`_orm.registry.constructor` function at this level:: class Base(DeclarativeBase): def __init__(self, id=None): self.id = id Mapped classes still will not invoke this constructor implicitly; it remains only accessible by calling ``super().__init__()``:: class MyClass(Base): def __init__(self, id=None, name=None): self.name = name super().__init__(id=id) Note that this is a different behavior from what functions like the legacy :func:`_orm.declarative_base` would do; the base created by those functions would always install :paramref:`_orm.registry.constructor` for ``__init__()``.

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `dossier_id` | BIGINT | non |  | FK → dossiers.id |  |
| `program_id` | BIGINT | non |  | FK → programs.id |  |
| `status` | ENUM preinscription_status | non | draft |  |  |
| `choice_rank` | SMALLINT | non | 1 |  |  |
| `submitted_at` | TIMESTAMP WITH TIME ZONE | oui |  |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- CHECK `ck_preinscriptions_submitted_has_date` : `status = 'draft' OR submitted_at IS NOT NULL`
- UNIQUE `uq_preinscriptions_dossier_id_program_id` (dossier_id, program_id)
- INDEX `ix_preinscriptions_dossier_id` (dossier_id)
- INDEX `ix_preinscriptions_program_id` (program_id)
- INDEX `ix_preinscriptions_status` (status)

### `equivalence_requests`

Base class used for declarative class definitions. The :class:`_orm.DeclarativeBase` allows for the creation of new declarative bases in such a way that is compatible with type checkers:: from sqlalchemy.orm import DeclarativeBase class Base(DeclarativeBase): pass The above ``Base`` class is now usable as the base for new declarative mappings. The superclass makes use of the ``__init_subclass__()`` method to set up new classes and metaclasses aren't used. When first used, the :class:`_orm.DeclarativeBase` class instantiates a new :class:`_orm.registry` to be used with the base, assuming one was not provided explicitly. The :class:`_orm.DeclarativeBase` class supports class-level attributes which act as parameters for the construction of this registry; such as to indicate a specific :class:`_schema.MetaData` collection as well as a specific value for :paramref:`_orm.registry.type_annotation_map`:: from typing_extensions import Annotated from sqlalchemy import BigInteger from sqlalchemy import MetaData from sqlalchemy import String from sqlalchemy.orm import DeclarativeBase bigint = Annotated[int, "bigint"] my_metadata = MetaData() class Base(DeclarativeBase): metadata = my_metadata type_annotation_map = { str: String().with_variant(String(255), "mysql", "mariadb"), bigint: BigInteger(), } Class-level attributes which may be specified include: :param metadata: optional :class:`_schema.MetaData` collection. If a :class:`_orm.registry` is constructed automatically, this :class:`_schema.MetaData` collection will be used to construct it. Otherwise, the local :class:`_schema.MetaData` collection will supersede that used by an existing :class:`_orm.registry` passed using the :paramref:`_orm.DeclarativeBase.registry` parameter. :param type_annotation_map: optional type annotation map that will be passed to the :class:`_orm.registry` as :paramref:`_orm.registry.type_annotation_map`. :param registry: supply a pre-existing :class:`_orm.registry` directly. .. versionadded:: 2.0 Added :class:`.DeclarativeBase`, so that declarative base classes may be constructed in such a way that is also recognized by :pep:`484` type checkers. As a result, :class:`.DeclarativeBase` and other subclassing-oriented APIs should be seen as superseding previous "class returned by a function" APIs, namely :func:`_orm.declarative_base` and :meth:`_orm.registry.generate_base`, where the base class returned cannot be recognized by type checkers without using plugins. **__init__ behavior** In a plain Python class, the base-most ``__init__()`` method in the class hierarchy is ``object.__init__()``, which accepts no arguments. However, when the :class:`_orm.DeclarativeBase` subclass is first declared, the class is given an ``__init__()`` method that links to the :paramref:`_orm.registry.constructor` constructor function, if no ``__init__()`` method is already present; this is the usual declarative constructor that will assign keyword arguments as attributes on the instance, assuming those attributes are established at the class level (i.e. are mapped, or are linked to a descriptor). This constructor is **never accessed by a mapped class without being called explicitly via super()**, as mapped classes are themselves given an ``__init__()`` method directly which calls :paramref:`_orm.registry.constructor`, so in the default case works independently of what the base-most ``__init__()`` method does. .. versionchanged:: 2.0.1 :class:`_orm.DeclarativeBase` has a default constructor that links to :paramref:`_orm.registry.constructor` by default, so that calls to ``super().__init__()`` can access this constructor. Previously, due to an implementation mistake, this default constructor was missing, and calling ``super().__init__()`` would invoke ``object.__init__()``. The :class:`_orm.DeclarativeBase` subclass may also declare an explicit ``__init__()`` method which will replace the use of the :paramref:`_orm.registry.constructor` function at this level:: class Base(DeclarativeBase): def __init__(self, id=None): self.id = id Mapped classes still will not invoke this constructor implicitly; it remains only accessible by calling ``super().__init__()``:: class MyClass(Base): def __init__(self, id=None, name=None): self.name = name super().__init__(id=id) Note that this is a different behavior from what functions like the legacy :func:`_orm.declarative_base` would do; the base created by those functions would always install :paramref:`_orm.registry.constructor` for ``__init__()``.

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `dossier_id` | BIGINT | non |  | FK → dossiers.id |  |
| `target_program_id` | BIGINT | non |  | FK → programs.id |  |
| `origin_diploma` | VARCHAR(255) | non |  |  |  |
| `origin_program` | VARCHAR(255) | oui |  |  |  |
| `origin_institution` | VARCHAR(255) | non |  |  |  |
| `origin_country` | VARCHAR(2) | non | TN |  |  |
| `origin_level` | ENUM education_level | oui |  |  |  |
| `requested_entry_level` | VARCHAR(100) | oui |  |  |  |
| `status` | ENUM equivalence_status | non | submitted |  |  |
| `submitted_at` | TIMESTAMP WITH TIME ZONE | non | now() |  |  |
| `reviewed_by` | BIGINT | oui |  | FK → users.id |  |
| `reviewed_at` | TIMESTAMP WITH TIME ZONE | oui |  |  |  |
| `review_comment` | TEXT | oui |  |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- CHECK `ck_equivalence_requests_reviewed_when_decided` : `status NOT IN ('accepted', 'rejected', 'more_info_requested') OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)`
- INDEX `ix_equivalence_requests_dossier_id` (dossier_id)
- INDEX `ix_equivalence_requests_status` (status)
- INDEX `ix_equivalence_requests_target_program_id` (target_program_id)

### `equivalence_documents`

Pièce justificative (le fichier est stocké hors base, ici seulement ses métadonnées).

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `equivalence_request_id` | BIGINT | non |  | FK → equivalence_requests.id |  |
| `document_type` | ENUM equivalence_document_type | non |  |  |  |
| `file_name` | VARCHAR(255) | non |  |  |  |
| `storage_key` | VARCHAR(1024) | non |  | UNIQUE |  |
| `mime_type` | VARCHAR(100) | non |  |  |  |
| `size_bytes` | BIGINT | non |  |  |  |
| `sha256` | VARCHAR(64) | non |  |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- CHECK `ck_equivalence_documents_sha256_format` : `sha256 ~ '^[0-9a-f]{64}$'`
- CHECK `ck_equivalence_documents_size_positive` : `size_bytes > 0`
- INDEX `ix_equivalence_documents_equivalence_request_id` (equivalence_request_id)

### `qcm`

Base class used for declarative class definitions. The :class:`_orm.DeclarativeBase` allows for the creation of new declarative bases in such a way that is compatible with type checkers:: from sqlalchemy.orm import DeclarativeBase class Base(DeclarativeBase): pass The above ``Base`` class is now usable as the base for new declarative mappings. The superclass makes use of the ``__init_subclass__()`` method to set up new classes and metaclasses aren't used. When first used, the :class:`_orm.DeclarativeBase` class instantiates a new :class:`_orm.registry` to be used with the base, assuming one was not provided explicitly. The :class:`_orm.DeclarativeBase` class supports class-level attributes which act as parameters for the construction of this registry; such as to indicate a specific :class:`_schema.MetaData` collection as well as a specific value for :paramref:`_orm.registry.type_annotation_map`:: from typing_extensions import Annotated from sqlalchemy import BigInteger from sqlalchemy import MetaData from sqlalchemy import String from sqlalchemy.orm import DeclarativeBase bigint = Annotated[int, "bigint"] my_metadata = MetaData() class Base(DeclarativeBase): metadata = my_metadata type_annotation_map = { str: String().with_variant(String(255), "mysql", "mariadb"), bigint: BigInteger(), } Class-level attributes which may be specified include: :param metadata: optional :class:`_schema.MetaData` collection. If a :class:`_orm.registry` is constructed automatically, this :class:`_schema.MetaData` collection will be used to construct it. Otherwise, the local :class:`_schema.MetaData` collection will supersede that used by an existing :class:`_orm.registry` passed using the :paramref:`_orm.DeclarativeBase.registry` parameter. :param type_annotation_map: optional type annotation map that will be passed to the :class:`_orm.registry` as :paramref:`_orm.registry.type_annotation_map`. :param registry: supply a pre-existing :class:`_orm.registry` directly. .. versionadded:: 2.0 Added :class:`.DeclarativeBase`, so that declarative base classes may be constructed in such a way that is also recognized by :pep:`484` type checkers. As a result, :class:`.DeclarativeBase` and other subclassing-oriented APIs should be seen as superseding previous "class returned by a function" APIs, namely :func:`_orm.declarative_base` and :meth:`_orm.registry.generate_base`, where the base class returned cannot be recognized by type checkers without using plugins. **__init__ behavior** In a plain Python class, the base-most ``__init__()`` method in the class hierarchy is ``object.__init__()``, which accepts no arguments. However, when the :class:`_orm.DeclarativeBase` subclass is first declared, the class is given an ``__init__()`` method that links to the :paramref:`_orm.registry.constructor` constructor function, if no ``__init__()`` method is already present; this is the usual declarative constructor that will assign keyword arguments as attributes on the instance, assuming those attributes are established at the class level (i.e. are mapped, or are linked to a descriptor). This constructor is **never accessed by a mapped class without being called explicitly via super()**, as mapped classes are themselves given an ``__init__()`` method directly which calls :paramref:`_orm.registry.constructor`, so in the default case works independently of what the base-most ``__init__()`` method does. .. versionchanged:: 2.0.1 :class:`_orm.DeclarativeBase` has a default constructor that links to :paramref:`_orm.registry.constructor` by default, so that calls to ``super().__init__()`` can access this constructor. Previously, due to an implementation mistake, this default constructor was missing, and calling ``super().__init__()`` would invoke ``object.__init__()``. The :class:`_orm.DeclarativeBase` subclass may also declare an explicit ``__init__()`` method which will replace the use of the :paramref:`_orm.registry.constructor` function at this level:: class Base(DeclarativeBase): def __init__(self, id=None): self.id = id Mapped classes still will not invoke this constructor implicitly; it remains only accessible by calling ``super().__init__()``:: class MyClass(Base): def __init__(self, id=None, name=None): self.name = name super().__init__(id=id) Note that this is a different behavior from what functions like the legacy :func:`_orm.declarative_base` would do; the base created by those functions would always install :paramref:`_orm.registry.constructor` for ``__init__()``.

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `dossier_id` | BIGINT | non |  | FK → dossiers.id |  |
| `program_id` | BIGINT | oui |  | FK → programs.id |  |
| `title` | VARCHAR(255) | non |  |  |  |
| `generated_by` | ENUM qcm_generated_by | non |  |  |  |
| `template_code` | VARCHAR(100) | oui |  |  |  |
| `model_name` | VARCHAR(100) | oui |  |  |  |
| `status` | ENUM qcm_status | non | generated |  |  |
| `score` | NUMERIC(6, 2) | oui |  |  |  |
| `max_score` | NUMERIC(6, 2) | non |  |  |  |
| `summary_for_interviewer` | TEXT | oui |  |  | Synthèse destinée au responsable d'entretien. |
| `started_at` | TIMESTAMP WITH TIME ZONE | oui |  |  |  |
| `completed_at` | TIMESTAMP WITH TIME ZONE | oui |  |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- CHECK `ck_qcm_completed_has_score` : `status <> 'completed' OR (score IS NOT NULL AND completed_at IS NOT NULL)`
- CHECK `ck_qcm_max_score_positive` : `max_score > 0`
- CHECK `ck_qcm_score_range` : `score IS NULL OR (score >= 0 AND score <= max_score)`
- CHECK `ck_qcm_template_has_code` : `generated_by <> 'template' OR template_code IS NOT NULL`
- INDEX `ix_qcm_dossier_id` (dossier_id)
- INDEX `ix_qcm_program_id` (program_id)

### `qcm_questions`

Base class used for declarative class definitions. The :class:`_orm.DeclarativeBase` allows for the creation of new declarative bases in such a way that is compatible with type checkers:: from sqlalchemy.orm import DeclarativeBase class Base(DeclarativeBase): pass The above ``Base`` class is now usable as the base for new declarative mappings. The superclass makes use of the ``__init_subclass__()`` method to set up new classes and metaclasses aren't used. When first used, the :class:`_orm.DeclarativeBase` class instantiates a new :class:`_orm.registry` to be used with the base, assuming one was not provided explicitly. The :class:`_orm.DeclarativeBase` class supports class-level attributes which act as parameters for the construction of this registry; such as to indicate a specific :class:`_schema.MetaData` collection as well as a specific value for :paramref:`_orm.registry.type_annotation_map`:: from typing_extensions import Annotated from sqlalchemy import BigInteger from sqlalchemy import MetaData from sqlalchemy import String from sqlalchemy.orm import DeclarativeBase bigint = Annotated[int, "bigint"] my_metadata = MetaData() class Base(DeclarativeBase): metadata = my_metadata type_annotation_map = { str: String().with_variant(String(255), "mysql", "mariadb"), bigint: BigInteger(), } Class-level attributes which may be specified include: :param metadata: optional :class:`_schema.MetaData` collection. If a :class:`_orm.registry` is constructed automatically, this :class:`_schema.MetaData` collection will be used to construct it. Otherwise, the local :class:`_schema.MetaData` collection will supersede that used by an existing :class:`_orm.registry` passed using the :paramref:`_orm.DeclarativeBase.registry` parameter. :param type_annotation_map: optional type annotation map that will be passed to the :class:`_orm.registry` as :paramref:`_orm.registry.type_annotation_map`. :param registry: supply a pre-existing :class:`_orm.registry` directly. .. versionadded:: 2.0 Added :class:`.DeclarativeBase`, so that declarative base classes may be constructed in such a way that is also recognized by :pep:`484` type checkers. As a result, :class:`.DeclarativeBase` and other subclassing-oriented APIs should be seen as superseding previous "class returned by a function" APIs, namely :func:`_orm.declarative_base` and :meth:`_orm.registry.generate_base`, where the base class returned cannot be recognized by type checkers without using plugins. **__init__ behavior** In a plain Python class, the base-most ``__init__()`` method in the class hierarchy is ``object.__init__()``, which accepts no arguments. However, when the :class:`_orm.DeclarativeBase` subclass is first declared, the class is given an ``__init__()`` method that links to the :paramref:`_orm.registry.constructor` constructor function, if no ``__init__()`` method is already present; this is the usual declarative constructor that will assign keyword arguments as attributes on the instance, assuming those attributes are established at the class level (i.e. are mapped, or are linked to a descriptor). This constructor is **never accessed by a mapped class without being called explicitly via super()**, as mapped classes are themselves given an ``__init__()`` method directly which calls :paramref:`_orm.registry.constructor`, so in the default case works independently of what the base-most ``__init__()`` method does. .. versionchanged:: 2.0.1 :class:`_orm.DeclarativeBase` has a default constructor that links to :paramref:`_orm.registry.constructor` by default, so that calls to ``super().__init__()`` can access this constructor. Previously, due to an implementation mistake, this default constructor was missing, and calling ``super().__init__()`` would invoke ``object.__init__()``. The :class:`_orm.DeclarativeBase` subclass may also declare an explicit ``__init__()`` method which will replace the use of the :paramref:`_orm.registry.constructor` function at this level:: class Base(DeclarativeBase): def __init__(self, id=None): self.id = id Mapped classes still will not invoke this constructor implicitly; it remains only accessible by calling ``super().__init__()``:: class MyClass(Base): def __init__(self, id=None, name=None): self.name = name super().__init__(id=id) Note that this is a different behavior from what functions like the legacy :func:`_orm.declarative_base` would do; the base created by those functions would always install :paramref:`_orm.registry.constructor` for ``__init__()``.

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `qcm_id` | BIGINT | non |  | FK → qcm.id |  |
| `position` | SMALLINT | non |  |  |  |
| `topic` | VARCHAR(100) | oui |  |  |  |
| `question_text` | TEXT | non |  |  |  |
| `choices` | JSONB | non |  |  |  |
| `correct_choice_index` | SMALLINT | non |  |  |  |
| `points` | NUMERIC(5, 2) | non | 1 |  |  |
| `explanation` | TEXT | oui |  |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- CHECK `ck_qcm_questions_choices_array` : `jsonb_typeof(choices) = 'array' AND jsonb_array_length(choices) >= 2`
- CHECK `ck_qcm_questions_correct_choice_in_range` : `correct_choice_index >= 0 AND correct_choice_index < jsonb_array_length(choices)`
- CHECK `ck_qcm_questions_points_positive` : `points > 0`
- UNIQUE `uq_qcm_questions_qcm_id_position` (qcm_id, position)

### `qcm_answers`

Base class used for declarative class definitions. The :class:`_orm.DeclarativeBase` allows for the creation of new declarative bases in such a way that is compatible with type checkers:: from sqlalchemy.orm import DeclarativeBase class Base(DeclarativeBase): pass The above ``Base`` class is now usable as the base for new declarative mappings. The superclass makes use of the ``__init_subclass__()`` method to set up new classes and metaclasses aren't used. When first used, the :class:`_orm.DeclarativeBase` class instantiates a new :class:`_orm.registry` to be used with the base, assuming one was not provided explicitly. The :class:`_orm.DeclarativeBase` class supports class-level attributes which act as parameters for the construction of this registry; such as to indicate a specific :class:`_schema.MetaData` collection as well as a specific value for :paramref:`_orm.registry.type_annotation_map`:: from typing_extensions import Annotated from sqlalchemy import BigInteger from sqlalchemy import MetaData from sqlalchemy import String from sqlalchemy.orm import DeclarativeBase bigint = Annotated[int, "bigint"] my_metadata = MetaData() class Base(DeclarativeBase): metadata = my_metadata type_annotation_map = { str: String().with_variant(String(255), "mysql", "mariadb"), bigint: BigInteger(), } Class-level attributes which may be specified include: :param metadata: optional :class:`_schema.MetaData` collection. If a :class:`_orm.registry` is constructed automatically, this :class:`_schema.MetaData` collection will be used to construct it. Otherwise, the local :class:`_schema.MetaData` collection will supersede that used by an existing :class:`_orm.registry` passed using the :paramref:`_orm.DeclarativeBase.registry` parameter. :param type_annotation_map: optional type annotation map that will be passed to the :class:`_orm.registry` as :paramref:`_orm.registry.type_annotation_map`. :param registry: supply a pre-existing :class:`_orm.registry` directly. .. versionadded:: 2.0 Added :class:`.DeclarativeBase`, so that declarative base classes may be constructed in such a way that is also recognized by :pep:`484` type checkers. As a result, :class:`.DeclarativeBase` and other subclassing-oriented APIs should be seen as superseding previous "class returned by a function" APIs, namely :func:`_orm.declarative_base` and :meth:`_orm.registry.generate_base`, where the base class returned cannot be recognized by type checkers without using plugins. **__init__ behavior** In a plain Python class, the base-most ``__init__()`` method in the class hierarchy is ``object.__init__()``, which accepts no arguments. However, when the :class:`_orm.DeclarativeBase` subclass is first declared, the class is given an ``__init__()`` method that links to the :paramref:`_orm.registry.constructor` constructor function, if no ``__init__()`` method is already present; this is the usual declarative constructor that will assign keyword arguments as attributes on the instance, assuming those attributes are established at the class level (i.e. are mapped, or are linked to a descriptor). This constructor is **never accessed by a mapped class without being called explicitly via super()**, as mapped classes are themselves given an ``__init__()`` method directly which calls :paramref:`_orm.registry.constructor`, so in the default case works independently of what the base-most ``__init__()`` method does. .. versionchanged:: 2.0.1 :class:`_orm.DeclarativeBase` has a default constructor that links to :paramref:`_orm.registry.constructor` by default, so that calls to ``super().__init__()`` can access this constructor. Previously, due to an implementation mistake, this default constructor was missing, and calling ``super().__init__()`` would invoke ``object.__init__()``. The :class:`_orm.DeclarativeBase` subclass may also declare an explicit ``__init__()`` method which will replace the use of the :paramref:`_orm.registry.constructor` function at this level:: class Base(DeclarativeBase): def __init__(self, id=None): self.id = id Mapped classes still will not invoke this constructor implicitly; it remains only accessible by calling ``super().__init__()``:: class MyClass(Base): def __init__(self, id=None, name=None): self.name = name super().__init__(id=id) Note that this is a different behavior from what functions like the legacy :func:`_orm.declarative_base` would do; the base created by those functions would always install :paramref:`_orm.registry.constructor` for ``__init__()``.

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `question_id` | BIGINT | non |  | FK → qcm_questions.id, UNIQUE |  |
| `selected_choice_index` | SMALLINT | non |  |  |  |
| `is_correct` | BOOLEAN | non |  |  |  |
| `points_awarded` | NUMERIC(5, 2) | non | 0 |  |  |
| `answered_at` | TIMESTAMP WITH TIME ZONE | non | now() |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- CHECK `ck_qcm_answers_points_positive` : `points_awarded >= 0`

### `appointments`

Base class used for declarative class definitions. The :class:`_orm.DeclarativeBase` allows for the creation of new declarative bases in such a way that is compatible with type checkers:: from sqlalchemy.orm import DeclarativeBase class Base(DeclarativeBase): pass The above ``Base`` class is now usable as the base for new declarative mappings. The superclass makes use of the ``__init_subclass__()`` method to set up new classes and metaclasses aren't used. When first used, the :class:`_orm.DeclarativeBase` class instantiates a new :class:`_orm.registry` to be used with the base, assuming one was not provided explicitly. The :class:`_orm.DeclarativeBase` class supports class-level attributes which act as parameters for the construction of this registry; such as to indicate a specific :class:`_schema.MetaData` collection as well as a specific value for :paramref:`_orm.registry.type_annotation_map`:: from typing_extensions import Annotated from sqlalchemy import BigInteger from sqlalchemy import MetaData from sqlalchemy import String from sqlalchemy.orm import DeclarativeBase bigint = Annotated[int, "bigint"] my_metadata = MetaData() class Base(DeclarativeBase): metadata = my_metadata type_annotation_map = { str: String().with_variant(String(255), "mysql", "mariadb"), bigint: BigInteger(), } Class-level attributes which may be specified include: :param metadata: optional :class:`_schema.MetaData` collection. If a :class:`_orm.registry` is constructed automatically, this :class:`_schema.MetaData` collection will be used to construct it. Otherwise, the local :class:`_schema.MetaData` collection will supersede that used by an existing :class:`_orm.registry` passed using the :paramref:`_orm.DeclarativeBase.registry` parameter. :param type_annotation_map: optional type annotation map that will be passed to the :class:`_orm.registry` as :paramref:`_orm.registry.type_annotation_map`. :param registry: supply a pre-existing :class:`_orm.registry` directly. .. versionadded:: 2.0 Added :class:`.DeclarativeBase`, so that declarative base classes may be constructed in such a way that is also recognized by :pep:`484` type checkers. As a result, :class:`.DeclarativeBase` and other subclassing-oriented APIs should be seen as superseding previous "class returned by a function" APIs, namely :func:`_orm.declarative_base` and :meth:`_orm.registry.generate_base`, where the base class returned cannot be recognized by type checkers without using plugins. **__init__ behavior** In a plain Python class, the base-most ``__init__()`` method in the class hierarchy is ``object.__init__()``, which accepts no arguments. However, when the :class:`_orm.DeclarativeBase` subclass is first declared, the class is given an ``__init__()`` method that links to the :paramref:`_orm.registry.constructor` constructor function, if no ``__init__()`` method is already present; this is the usual declarative constructor that will assign keyword arguments as attributes on the instance, assuming those attributes are established at the class level (i.e. are mapped, or are linked to a descriptor). This constructor is **never accessed by a mapped class without being called explicitly via super()**, as mapped classes are themselves given an ``__init__()`` method directly which calls :paramref:`_orm.registry.constructor`, so in the default case works independently of what the base-most ``__init__()`` method does. .. versionchanged:: 2.0.1 :class:`_orm.DeclarativeBase` has a default constructor that links to :paramref:`_orm.registry.constructor` by default, so that calls to ``super().__init__()`` can access this constructor. Previously, due to an implementation mistake, this default constructor was missing, and calling ``super().__init__()`` would invoke ``object.__init__()``. The :class:`_orm.DeclarativeBase` subclass may also declare an explicit ``__init__()`` method which will replace the use of the :paramref:`_orm.registry.constructor` function at this level:: class Base(DeclarativeBase): def __init__(self, id=None): self.id = id Mapped classes still will not invoke this constructor implicitly; it remains only accessible by calling ``super().__init__()``:: class MyClass(Base): def __init__(self, id=None, name=None): self.name = name super().__init__(id=id) Note that this is a different behavior from what functions like the legacy :func:`_orm.declarative_base` would do; the base created by those functions would always install :paramref:`_orm.registry.constructor` for ``__init__()``.

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `dossier_id` | BIGINT | non |  | FK → dossiers.id |  |
| `organizer_id` | BIGINT | non |  | FK → users.id |  |
| `scheduled_at` | TIMESTAMP WITH TIME ZONE | non |  |  |  |
| `duration_minutes` | SMALLINT | non | 30 |  |  |
| `mode` | ENUM appointment_mode | non |  |  |  |
| `location` | VARCHAR(255) | oui |  |  |  |
| `meeting_url` | VARCHAR(1024) | oui |  |  |  |
| `status` | ENUM appointment_status | non | scheduled |  |  |
| `cancellation_reason` | TEXT | oui |  |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- CHECK `ck_appointments_cancel_has_reason` : `status <> 'cancelled' OR cancellation_reason IS NOT NULL`
- CHECK `ck_appointments_duration_range` : `duration_minutes BETWEEN 5 AND 240`
- CHECK `ck_appointments_online_has_url` : `mode <> 'online' OR meeting_url IS NOT NULL`
- INDEX `ix_appointments_dossier_id` (dossier_id)
- INDEX `ix_appointments_organizer_scheduled` (organizer_id, scheduled_at)

### `interview_results`

Base class used for declarative class definitions. The :class:`_orm.DeclarativeBase` allows for the creation of new declarative bases in such a way that is compatible with type checkers:: from sqlalchemy.orm import DeclarativeBase class Base(DeclarativeBase): pass The above ``Base`` class is now usable as the base for new declarative mappings. The superclass makes use of the ``__init_subclass__()`` method to set up new classes and metaclasses aren't used. When first used, the :class:`_orm.DeclarativeBase` class instantiates a new :class:`_orm.registry` to be used with the base, assuming one was not provided explicitly. The :class:`_orm.DeclarativeBase` class supports class-level attributes which act as parameters for the construction of this registry; such as to indicate a specific :class:`_schema.MetaData` collection as well as a specific value for :paramref:`_orm.registry.type_annotation_map`:: from typing_extensions import Annotated from sqlalchemy import BigInteger from sqlalchemy import MetaData from sqlalchemy import String from sqlalchemy.orm import DeclarativeBase bigint = Annotated[int, "bigint"] my_metadata = MetaData() class Base(DeclarativeBase): metadata = my_metadata type_annotation_map = { str: String().with_variant(String(255), "mysql", "mariadb"), bigint: BigInteger(), } Class-level attributes which may be specified include: :param metadata: optional :class:`_schema.MetaData` collection. If a :class:`_orm.registry` is constructed automatically, this :class:`_schema.MetaData` collection will be used to construct it. Otherwise, the local :class:`_schema.MetaData` collection will supersede that used by an existing :class:`_orm.registry` passed using the :paramref:`_orm.DeclarativeBase.registry` parameter. :param type_annotation_map: optional type annotation map that will be passed to the :class:`_orm.registry` as :paramref:`_orm.registry.type_annotation_map`. :param registry: supply a pre-existing :class:`_orm.registry` directly. .. versionadded:: 2.0 Added :class:`.DeclarativeBase`, so that declarative base classes may be constructed in such a way that is also recognized by :pep:`484` type checkers. As a result, :class:`.DeclarativeBase` and other subclassing-oriented APIs should be seen as superseding previous "class returned by a function" APIs, namely :func:`_orm.declarative_base` and :meth:`_orm.registry.generate_base`, where the base class returned cannot be recognized by type checkers without using plugins. **__init__ behavior** In a plain Python class, the base-most ``__init__()`` method in the class hierarchy is ``object.__init__()``, which accepts no arguments. However, when the :class:`_orm.DeclarativeBase` subclass is first declared, the class is given an ``__init__()`` method that links to the :paramref:`_orm.registry.constructor` constructor function, if no ``__init__()`` method is already present; this is the usual declarative constructor that will assign keyword arguments as attributes on the instance, assuming those attributes are established at the class level (i.e. are mapped, or are linked to a descriptor). This constructor is **never accessed by a mapped class without being called explicitly via super()**, as mapped classes are themselves given an ``__init__()`` method directly which calls :paramref:`_orm.registry.constructor`, so in the default case works independently of what the base-most ``__init__()`` method does. .. versionchanged:: 2.0.1 :class:`_orm.DeclarativeBase` has a default constructor that links to :paramref:`_orm.registry.constructor` by default, so that calls to ``super().__init__()`` can access this constructor. Previously, due to an implementation mistake, this default constructor was missing, and calling ``super().__init__()`` would invoke ``object.__init__()``. The :class:`_orm.DeclarativeBase` subclass may also declare an explicit ``__init__()`` method which will replace the use of the :paramref:`_orm.registry.constructor` function at this level:: class Base(DeclarativeBase): def __init__(self, id=None): self.id = id Mapped classes still will not invoke this constructor implicitly; it remains only accessible by calling ``super().__init__()``:: class MyClass(Base): def __init__(self, id=None, name=None): self.name = name super().__init__(id=id) Note that this is a different behavior from what functions like the legacy :func:`_orm.declarative_base` would do; the base created by those functions would always install :paramref:`_orm.registry.constructor` for ``__init__()``.

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `appointment_id` | BIGINT | non |  | FK → appointments.id, UNIQUE |  |
| `interviewer_id` | BIGINT | non |  | FK → users.id |  |
| `observations` | TEXT | non |  |  |  |
| `score` | NUMERIC(4, 2) | oui |  |  |  |
| `opinion` | ENUM interview_opinion | non |  |  |  |
| `recorded_at` | TIMESTAMP WITH TIME ZONE | non | now() |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- CHECK `ck_interview_results_score_range` : `score IS NULL OR score BETWEEN 0 AND 20`
- INDEX `ix_interview_results_interviewer_id` (interviewer_id)

### `decisions`

Décision OFFICIELLE : toujours prise par un humain responsable (trigger SQL).

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `dossier_id` | BIGINT | non |  | FK → dossiers.id |  |
| `program_id` | BIGINT | oui |  | FK → programs.id |  |
| `decision` | ENUM decision_value | non |  |  |  |
| `observations` | TEXT | oui |  |  |  |
| `responsible_id` | BIGINT | non |  | FK → users.id | Responsable HUMAIN obligatoire (trigger) : un agent IA ne peut pas décider. |
| `decided_at` | TIMESTAMP WITH TIME ZONE | non | now() |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- CHECK `ck_decisions_admission_has_program` : `decision NOT IN ('admitted', 'admitted_with_conditions') OR program_id IS NOT NULL`
- CHECK `ck_decisions_conditions_explained` : `decision <> 'admitted_with_conditions' OR observations IS NOT NULL`
- INDEX `ix_decisions_dossier_id` (dossier_id)
- INDEX `ix_decisions_program_id` (program_id)
- INDEX `ix_decisions_responsible_id` (responsible_id)

### `notifications`

Base class used for declarative class definitions. The :class:`_orm.DeclarativeBase` allows for the creation of new declarative bases in such a way that is compatible with type checkers:: from sqlalchemy.orm import DeclarativeBase class Base(DeclarativeBase): pass The above ``Base`` class is now usable as the base for new declarative mappings. The superclass makes use of the ``__init_subclass__()`` method to set up new classes and metaclasses aren't used. When first used, the :class:`_orm.DeclarativeBase` class instantiates a new :class:`_orm.registry` to be used with the base, assuming one was not provided explicitly. The :class:`_orm.DeclarativeBase` class supports class-level attributes which act as parameters for the construction of this registry; such as to indicate a specific :class:`_schema.MetaData` collection as well as a specific value for :paramref:`_orm.registry.type_annotation_map`:: from typing_extensions import Annotated from sqlalchemy import BigInteger from sqlalchemy import MetaData from sqlalchemy import String from sqlalchemy.orm import DeclarativeBase bigint = Annotated[int, "bigint"] my_metadata = MetaData() class Base(DeclarativeBase): metadata = my_metadata type_annotation_map = { str: String().with_variant(String(255), "mysql", "mariadb"), bigint: BigInteger(), } Class-level attributes which may be specified include: :param metadata: optional :class:`_schema.MetaData` collection. If a :class:`_orm.registry` is constructed automatically, this :class:`_schema.MetaData` collection will be used to construct it. Otherwise, the local :class:`_schema.MetaData` collection will supersede that used by an existing :class:`_orm.registry` passed using the :paramref:`_orm.DeclarativeBase.registry` parameter. :param type_annotation_map: optional type annotation map that will be passed to the :class:`_orm.registry` as :paramref:`_orm.registry.type_annotation_map`. :param registry: supply a pre-existing :class:`_orm.registry` directly. .. versionadded:: 2.0 Added :class:`.DeclarativeBase`, so that declarative base classes may be constructed in such a way that is also recognized by :pep:`484` type checkers. As a result, :class:`.DeclarativeBase` and other subclassing-oriented APIs should be seen as superseding previous "class returned by a function" APIs, namely :func:`_orm.declarative_base` and :meth:`_orm.registry.generate_base`, where the base class returned cannot be recognized by type checkers without using plugins. **__init__ behavior** In a plain Python class, the base-most ``__init__()`` method in the class hierarchy is ``object.__init__()``, which accepts no arguments. However, when the :class:`_orm.DeclarativeBase` subclass is first declared, the class is given an ``__init__()`` method that links to the :paramref:`_orm.registry.constructor` constructor function, if no ``__init__()`` method is already present; this is the usual declarative constructor that will assign keyword arguments as attributes on the instance, assuming those attributes are established at the class level (i.e. are mapped, or are linked to a descriptor). This constructor is **never accessed by a mapped class without being called explicitly via super()**, as mapped classes are themselves given an ``__init__()`` method directly which calls :paramref:`_orm.registry.constructor`, so in the default case works independently of what the base-most ``__init__()`` method does. .. versionchanged:: 2.0.1 :class:`_orm.DeclarativeBase` has a default constructor that links to :paramref:`_orm.registry.constructor` by default, so that calls to ``super().__init__()`` can access this constructor. Previously, due to an implementation mistake, this default constructor was missing, and calling ``super().__init__()`` would invoke ``object.__init__()``. The :class:`_orm.DeclarativeBase` subclass may also declare an explicit ``__init__()`` method which will replace the use of the :paramref:`_orm.registry.constructor` function at this level:: class Base(DeclarativeBase): def __init__(self, id=None): self.id = id Mapped classes still will not invoke this constructor implicitly; it remains only accessible by calling ``super().__init__()``:: class MyClass(Base): def __init__(self, id=None, name=None): self.name = name super().__init__(id=id) Note that this is a different behavior from what functions like the legacy :func:`_orm.declarative_base` would do; the base created by those functions would always install :paramref:`_orm.registry.constructor` for ``__init__()``.

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `user_id` | BIGINT | non |  | FK → users.id |  |
| `dossier_id` | BIGINT | oui |  | FK → dossiers.id |  |
| `kind` | ENUM notification_kind | non |  |  |  |
| `channel` | ENUM notification_channel | non | email |  |  |
| `template_code` | VARCHAR(100) | oui |  |  |  |
| `subject` | VARCHAR(255) | non |  |  |  |
| `scheduled_for` | TIMESTAMP WITH TIME ZONE | non | now() |  |  |
| `status` | ENUM notification_status | non | pending |  |  |
| `attempts` | SMALLINT | non | 0 |  |  |
| `sent_at` | TIMESTAMP WITH TIME ZONE | oui |  |  |  |
| `last_error` | TEXT | oui |  |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- CHECK `ck_notifications_attempts_positive` : `attempts >= 0`
- CHECK `ck_notifications_sent_has_date` : `status <> 'sent' OR sent_at IS NOT NULL`
- INDEX `ix_notifications_dossier_id` (dossier_id)
- INDEX `ix_notifications_status_scheduled` (status, scheduled_for)
- INDEX `ix_notifications_user_id` (user_id)

### `audit_log`

Journal des actions (append-only : UPDATE/DELETE interdits par trigger). Aucun secret.

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `occurred_at` | TIMESTAMP WITH TIME ZONE | non | now() |  |  |
| `actor_type` | ENUM actor_type | non |  |  |  |
| `actor_user_id` | BIGINT | oui |  | FK → users.id |  |
| `action` | VARCHAR(100) | non |  |  |  |
| `entity_type` | VARCHAR(100) | non |  |  |  |
| `entity_id` | BIGINT | oui |  |  |  |
| `details` | JSONB | oui |  |  |  |
| `request_id` | VARCHAR(64) | oui |  |  |  |

Contraintes et index :

- CHECK `ck_audit_log_user_actor_has_id` : `actor_type <> 'user' OR actor_user_id IS NOT NULL`
- INDEX `ix_audit_log_actor_user_id` (actor_user_id)
- INDEX `ix_audit_log_entity` (entity_type, entity_id)
- INDEX `ix_audit_log_occurred_at` (occurred_at)

### `status_history`

Historique des changements de statut, alimenté automatiquement par trigger.

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `entity_type` | VARCHAR(100) | non |  |  |  |
| `entity_id` | BIGINT | non |  |  |  |
| `old_status` | VARCHAR(50) | oui |  |  |  |
| `new_status` | VARCHAR(50) | non |  |  |  |
| `changed_by` | BIGINT | oui |  |  | Lu depuis SET LOCAL app.current_user_id ; NULL = système. |
| `changed_at` | TIMESTAMP WITH TIME ZONE | non | now() |  |  |

Contraintes et index :

- INDEX `ix_status_history_entity` (entity_type, entity_id, changed_at)

## SA-14 — Documents et synchronisation

### `source_documents`

_Voir section SA-12._

### `document_chunks`

Base class used for declarative class definitions. The :class:`_orm.DeclarativeBase` allows for the creation of new declarative bases in such a way that is compatible with type checkers:: from sqlalchemy.orm import DeclarativeBase class Base(DeclarativeBase): pass The above ``Base`` class is now usable as the base for new declarative mappings. The superclass makes use of the ``__init_subclass__()`` method to set up new classes and metaclasses aren't used. When first used, the :class:`_orm.DeclarativeBase` class instantiates a new :class:`_orm.registry` to be used with the base, assuming one was not provided explicitly. The :class:`_orm.DeclarativeBase` class supports class-level attributes which act as parameters for the construction of this registry; such as to indicate a specific :class:`_schema.MetaData` collection as well as a specific value for :paramref:`_orm.registry.type_annotation_map`:: from typing_extensions import Annotated from sqlalchemy import BigInteger from sqlalchemy import MetaData from sqlalchemy import String from sqlalchemy.orm import DeclarativeBase bigint = Annotated[int, "bigint"] my_metadata = MetaData() class Base(DeclarativeBase): metadata = my_metadata type_annotation_map = { str: String().with_variant(String(255), "mysql", "mariadb"), bigint: BigInteger(), } Class-level attributes which may be specified include: :param metadata: optional :class:`_schema.MetaData` collection. If a :class:`_orm.registry` is constructed automatically, this :class:`_schema.MetaData` collection will be used to construct it. Otherwise, the local :class:`_schema.MetaData` collection will supersede that used by an existing :class:`_orm.registry` passed using the :paramref:`_orm.DeclarativeBase.registry` parameter. :param type_annotation_map: optional type annotation map that will be passed to the :class:`_orm.registry` as :paramref:`_orm.registry.type_annotation_map`. :param registry: supply a pre-existing :class:`_orm.registry` directly. .. versionadded:: 2.0 Added :class:`.DeclarativeBase`, so that declarative base classes may be constructed in such a way that is also recognized by :pep:`484` type checkers. As a result, :class:`.DeclarativeBase` and other subclassing-oriented APIs should be seen as superseding previous "class returned by a function" APIs, namely :func:`_orm.declarative_base` and :meth:`_orm.registry.generate_base`, where the base class returned cannot be recognized by type checkers without using plugins. **__init__ behavior** In a plain Python class, the base-most ``__init__()`` method in the class hierarchy is ``object.__init__()``, which accepts no arguments. However, when the :class:`_orm.DeclarativeBase` subclass is first declared, the class is given an ``__init__()`` method that links to the :paramref:`_orm.registry.constructor` constructor function, if no ``__init__()`` method is already present; this is the usual declarative constructor that will assign keyword arguments as attributes on the instance, assuming those attributes are established at the class level (i.e. are mapped, or are linked to a descriptor). This constructor is **never accessed by a mapped class without being called explicitly via super()**, as mapped classes are themselves given an ``__init__()`` method directly which calls :paramref:`_orm.registry.constructor`, so in the default case works independently of what the base-most ``__init__()`` method does. .. versionchanged:: 2.0.1 :class:`_orm.DeclarativeBase` has a default constructor that links to :paramref:`_orm.registry.constructor` by default, so that calls to ``super().__init__()`` can access this constructor. Previously, due to an implementation mistake, this default constructor was missing, and calling ``super().__init__()`` would invoke ``object.__init__()``. The :class:`_orm.DeclarativeBase` subclass may also declare an explicit ``__init__()`` method which will replace the use of the :paramref:`_orm.registry.constructor` function at this level:: class Base(DeclarativeBase): def __init__(self, id=None): self.id = id Mapped classes still will not invoke this constructor implicitly; it remains only accessible by calling ``super().__init__()``:: class MyClass(Base): def __init__(self, id=None, name=None): self.name = name super().__init__(id=id) Note that this is a different behavior from what functions like the legacy :func:`_orm.declarative_base` would do; the base created by those functions would always install :paramref:`_orm.registry.constructor` for ``__init__()``.

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `source_document_id` | BIGINT | non |  | FK → source_documents.id | Document source officiel de l'information (traçabilité obligatoire). |
| `program_id` | BIGINT | oui |  | FK → programs.id | Formation concernée (NULL = chunk transverse). |
| `chunk_index` | INTEGER | non |  |  |  |
| `content` | TEXT | non |  |  |  |
| `section_title` | VARCHAR(255) | oui |  |  |  |
| `page_number` | INTEGER | oui |  |  |  |
| `token_count` | INTEGER | oui |  |  |  |
| `embedding` | VECTOR(1024) | oui |  |  | vector(1024) pgvector, index HNSW cosinus. |
| `embedding_model` | VARCHAR(100) | oui |  |  |  |
| `metadata` | JSONB | oui |  |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |
| `is_demo` | BOOLEAN | non | false |  | true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md). |

Contraintes et index :

- CHECK `ck_document_chunks_chunk_index_positive` : `chunk_index >= 0`
- CHECK `ck_document_chunks_token_count_positive` : `token_count IS NULL OR token_count > 0`
- UNIQUE `uq_document_chunks_source_document_id_chunk_index` (source_document_id, chunk_index)
- INDEX `ix_document_chunks_embedding_hnsw` (embedding) USING hnsw
- INDEX `ix_document_chunks_program_id` (program_id)
- INDEX `ix_document_chunks_source_document_id` (source_document_id)

### `sync_jobs`

Base class used for declarative class definitions. The :class:`_orm.DeclarativeBase` allows for the creation of new declarative bases in such a way that is compatible with type checkers:: from sqlalchemy.orm import DeclarativeBase class Base(DeclarativeBase): pass The above ``Base`` class is now usable as the base for new declarative mappings. The superclass makes use of the ``__init_subclass__()`` method to set up new classes and metaclasses aren't used. When first used, the :class:`_orm.DeclarativeBase` class instantiates a new :class:`_orm.registry` to be used with the base, assuming one was not provided explicitly. The :class:`_orm.DeclarativeBase` class supports class-level attributes which act as parameters for the construction of this registry; such as to indicate a specific :class:`_schema.MetaData` collection as well as a specific value for :paramref:`_orm.registry.type_annotation_map`:: from typing_extensions import Annotated from sqlalchemy import BigInteger from sqlalchemy import MetaData from sqlalchemy import String from sqlalchemy.orm import DeclarativeBase bigint = Annotated[int, "bigint"] my_metadata = MetaData() class Base(DeclarativeBase): metadata = my_metadata type_annotation_map = { str: String().with_variant(String(255), "mysql", "mariadb"), bigint: BigInteger(), } Class-level attributes which may be specified include: :param metadata: optional :class:`_schema.MetaData` collection. If a :class:`_orm.registry` is constructed automatically, this :class:`_schema.MetaData` collection will be used to construct it. Otherwise, the local :class:`_schema.MetaData` collection will supersede that used by an existing :class:`_orm.registry` passed using the :paramref:`_orm.DeclarativeBase.registry` parameter. :param type_annotation_map: optional type annotation map that will be passed to the :class:`_orm.registry` as :paramref:`_orm.registry.type_annotation_map`. :param registry: supply a pre-existing :class:`_orm.registry` directly. .. versionadded:: 2.0 Added :class:`.DeclarativeBase`, so that declarative base classes may be constructed in such a way that is also recognized by :pep:`484` type checkers. As a result, :class:`.DeclarativeBase` and other subclassing-oriented APIs should be seen as superseding previous "class returned by a function" APIs, namely :func:`_orm.declarative_base` and :meth:`_orm.registry.generate_base`, where the base class returned cannot be recognized by type checkers without using plugins. **__init__ behavior** In a plain Python class, the base-most ``__init__()`` method in the class hierarchy is ``object.__init__()``, which accepts no arguments. However, when the :class:`_orm.DeclarativeBase` subclass is first declared, the class is given an ``__init__()`` method that links to the :paramref:`_orm.registry.constructor` constructor function, if no ``__init__()`` method is already present; this is the usual declarative constructor that will assign keyword arguments as attributes on the instance, assuming those attributes are established at the class level (i.e. are mapped, or are linked to a descriptor). This constructor is **never accessed by a mapped class without being called explicitly via super()**, as mapped classes are themselves given an ``__init__()`` method directly which calls :paramref:`_orm.registry.constructor`, so in the default case works independently of what the base-most ``__init__()`` method does. .. versionchanged:: 2.0.1 :class:`_orm.DeclarativeBase` has a default constructor that links to :paramref:`_orm.registry.constructor` by default, so that calls to ``super().__init__()`` can access this constructor. Previously, due to an implementation mistake, this default constructor was missing, and calling ``super().__init__()`` would invoke ``object.__init__()``. The :class:`_orm.DeclarativeBase` subclass may also declare an explicit ``__init__()`` method which will replace the use of the :paramref:`_orm.registry.constructor` function at this level:: class Base(DeclarativeBase): def __init__(self, id=None): self.id = id Mapped classes still will not invoke this constructor implicitly; it remains only accessible by calling ``super().__init__()``:: class MyClass(Base): def __init__(self, id=None, name=None): self.name = name super().__init__(id=id) Note that this is a different behavior from what functions like the legacy :func:`_orm.declarative_base` would do; the base created by those functions would always install :paramref:`_orm.registry.constructor` for ``__init__()``.

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `source_document_id` | BIGINT | oui |  | FK → source_documents.id | Document source officiel de l'information (traçabilité obligatoire). |
| `job_type` | ENUM sync_job_type | non |  |  |  |
| `status` | ENUM sync_status | non | pending |  |  |
| `triggered_by` | BIGINT | oui |  | FK → users.id |  |
| `started_at` | TIMESTAMP WITH TIME ZONE | oui |  |  |  |
| `finished_at` | TIMESTAMP WITH TIME ZONE | oui |  |  |  |
| `processed_count` | INTEGER | non | 0 |  |  |
| `error_count` | INTEGER | non | 0 |  |  |
| `last_error` | TEXT | oui |  |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |
| `updated_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de dernière modification (trigger set_updated_at). |

Contraintes et index :

- CHECK `ck_sync_jobs_counters_positive` : `error_count >= 0 AND processed_count >= 0`
- CHECK `ck_sync_jobs_dates_order` : `finished_at IS NULL OR finished_at >= started_at`
- CHECK `ck_sync_jobs_finished_after_start` : `finished_at IS NULL OR started_at IS NOT NULL`
- CHECK `ck_sync_jobs_terminal_has_end` : `status NOT IN ('succeeded', 'failed', 'partial') OR finished_at IS NOT NULL`
- INDEX `ix_sync_jobs_source_document_id` (source_document_id)
- INDEX `ix_sync_jobs_status_created` (status, created_at)

### `sync_logs`

Base class used for declarative class definitions. The :class:`_orm.DeclarativeBase` allows for the creation of new declarative bases in such a way that is compatible with type checkers:: from sqlalchemy.orm import DeclarativeBase class Base(DeclarativeBase): pass The above ``Base`` class is now usable as the base for new declarative mappings. The superclass makes use of the ``__init_subclass__()`` method to set up new classes and metaclasses aren't used. When first used, the :class:`_orm.DeclarativeBase` class instantiates a new :class:`_orm.registry` to be used with the base, assuming one was not provided explicitly. The :class:`_orm.DeclarativeBase` class supports class-level attributes which act as parameters for the construction of this registry; such as to indicate a specific :class:`_schema.MetaData` collection as well as a specific value for :paramref:`_orm.registry.type_annotation_map`:: from typing_extensions import Annotated from sqlalchemy import BigInteger from sqlalchemy import MetaData from sqlalchemy import String from sqlalchemy.orm import DeclarativeBase bigint = Annotated[int, "bigint"] my_metadata = MetaData() class Base(DeclarativeBase): metadata = my_metadata type_annotation_map = { str: String().with_variant(String(255), "mysql", "mariadb"), bigint: BigInteger(), } Class-level attributes which may be specified include: :param metadata: optional :class:`_schema.MetaData` collection. If a :class:`_orm.registry` is constructed automatically, this :class:`_schema.MetaData` collection will be used to construct it. Otherwise, the local :class:`_schema.MetaData` collection will supersede that used by an existing :class:`_orm.registry` passed using the :paramref:`_orm.DeclarativeBase.registry` parameter. :param type_annotation_map: optional type annotation map that will be passed to the :class:`_orm.registry` as :paramref:`_orm.registry.type_annotation_map`. :param registry: supply a pre-existing :class:`_orm.registry` directly. .. versionadded:: 2.0 Added :class:`.DeclarativeBase`, so that declarative base classes may be constructed in such a way that is also recognized by :pep:`484` type checkers. As a result, :class:`.DeclarativeBase` and other subclassing-oriented APIs should be seen as superseding previous "class returned by a function" APIs, namely :func:`_orm.declarative_base` and :meth:`_orm.registry.generate_base`, where the base class returned cannot be recognized by type checkers without using plugins. **__init__ behavior** In a plain Python class, the base-most ``__init__()`` method in the class hierarchy is ``object.__init__()``, which accepts no arguments. However, when the :class:`_orm.DeclarativeBase` subclass is first declared, the class is given an ``__init__()`` method that links to the :paramref:`_orm.registry.constructor` constructor function, if no ``__init__()`` method is already present; this is the usual declarative constructor that will assign keyword arguments as attributes on the instance, assuming those attributes are established at the class level (i.e. are mapped, or are linked to a descriptor). This constructor is **never accessed by a mapped class without being called explicitly via super()**, as mapped classes are themselves given an ``__init__()`` method directly which calls :paramref:`_orm.registry.constructor`, so in the default case works independently of what the base-most ``__init__()`` method does. .. versionchanged:: 2.0.1 :class:`_orm.DeclarativeBase` has a default constructor that links to :paramref:`_orm.registry.constructor` by default, so that calls to ``super().__init__()`` can access this constructor. Previously, due to an implementation mistake, this default constructor was missing, and calling ``super().__init__()`` would invoke ``object.__init__()``. The :class:`_orm.DeclarativeBase` subclass may also declare an explicit ``__init__()`` method which will replace the use of the :paramref:`_orm.registry.constructor` function at this level:: class Base(DeclarativeBase): def __init__(self, id=None): self.id = id Mapped classes still will not invoke this constructor implicitly; it remains only accessible by calling ``super().__init__()``:: class MyClass(Base): def __init__(self, id=None, name=None): self.name = name super().__init__(id=id) Note that this is a different behavior from what functions like the legacy :func:`_orm.declarative_base` would do; the base created by those functions would always install :paramref:`_orm.registry.constructor` for ``__init__()``.

| Colonne | Type | Null | Défaut | Clé / référence | Description |
|---|---|---|---|---|---|
| `id` | BIGINT | non |  | PK | Clé primaire technique (BIGINT identity). |
| `sync_job_id` | BIGINT | non |  | FK → sync_jobs.id |  |
| `level` | ENUM sync_log_level | non |  |  |  |
| `message` | TEXT | non |  |  |  |
| `details` | JSONB | oui |  |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | non | now() |  | Date de création (UTC, défaut now()). |

Contraintes et index :

- INDEX `ix_sync_logs_sync_job_id` (sync_job_id)

