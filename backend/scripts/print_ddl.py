"""Affiche le DDL PostgreSQL généré depuis les modèles (vérification hors ligne, sans base)."""

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.models import Base

if __name__ == "__main__":
    dialect = postgresql.dialect()
    for table in Base.metadata.sorted_tables:
        print(str(CreateTable(table).compile(dialect=dialect)).strip() + ";\n")
    print(f"-- {len(Base.metadata.tables)} tables")
