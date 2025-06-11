from fastapi import FastAPI, Query, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, exc
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from fastapi_pagination import Page, add_pagination, paginate, Params
from fastapi_pagination.limit_offset import LimitOffsetPage, LimitOffsetParams
from pydantic import BaseModel

DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI()

# MODELS
class CentroTreinamento(Base):
    __tablename__ = "centros_treinamento"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True)

class Categoria(Base):
    __tablename__ = "categorias"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True)

class Atleta(Base):
    __tablename__ = "atletas"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    cpf = Column(String, unique=True, index=True)
    centro_treinamento_id = Column(Integer, ForeignKey("centros_treinamento.id"))
    categoria_id = Column(Integer, ForeignKey("categorias.id"))

    centro_treinamento = relationship("CentroTreinamento")
    categoria = relationship("Categoria")

Base.metadata.create_all(bind=engine)

# SCHEMAS

class CentroTreinamentoSchema(BaseModel):
    id: int
    nome: str
    class Config:
        orm_mode = True

class CategoriaSchema(BaseModel):
    id: int
    nome: str
    class Config:
        orm_mode = True

class AtletaCreate(BaseModel):
    nome: str
    cpf: str
    centro_treinamento_id: int
    categoria_id: int

class AtletaResponse(BaseModel):
    nome: str
    centro_treinamento: str
    categoria: str

    class Config:
        orm_mode = True

# DEPENDENCY
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ENDPOINTS

@app.post("/atletas/", status_code=201)
def create_atleta(atleta: AtletaCreate, db: Session = Depends(get_db)):
    db_atleta = Atleta(**atleta.dict())
    try:
        db.add(db_atleta)
        db.commit()
        db.refresh(db_atleta)
    except exc.IntegrityError as e:
        db.rollback()
        if "UNIQUE constraint failed: atletas.cpf" in str(e.orig):
            return JSONResponse(
                status_code=303,
                content={"detail": f"Já existe um atleta cadastrado com o cpf: {atleta.cpf}"}
            )
        raise
    return {"id": db_atleta.id}

@app.get("/atletas/", response_model=LimitOffsetPage[AtletaResponse])
def get_atletas(
    nome: str = Query(None),
    cpf: str = Query(None),
    params: LimitOffsetParams = Depends(),
    db: Session = Depends(get_db)
):
    query = db.query(Atleta)
    if nome:
        query = query.filter(Atleta.nome.ilike(f"%{nome}%"))
    if cpf:
        query = query.filter(Atleta.cpf == cpf)
    atletas = query.all()
    # Custom response
    result = [
        AtletaResponse(
            nome=a.nome,
            centro_treinamento=a.centro_treinamento.nome if a.centro_treinamento else None,
            categoria=a.categoria.nome if a.categoria else None
        )
        for a in atletas
    ]
    return paginate(result, params)

# Exemplo de manipulação de exceção de integridade em outro módulo/tabela
@app.post("/centros_treinamento/", status_code=201)
def create_centro_treinamento(centro: CentroTreinamentoSchema, db: Session = Depends(get_db)):
    db_centro = CentroTreinamento(nome=centro.nome)
    try:
        db.add(db_centro)
        db.commit()
        db.refresh(db_centro)
    except exc.IntegrityError as e:
        db.rollback()
        return JSONResponse(
            status_code=303,
            content={"detail": f"Já existe um centro de treinamento cadastrado com o nome: {centro.nome}"}
        )
    return {"id": db_centro.id}

@app.post("/categorias/", status_code=201)
def create_categoria(categoria: CategoriaSchema, db: Session = Depends(get_db)):
    db_categoria = Categoria(nome=categoria.nome)
    try:
        db.add(db_categoria)
        db.commit()
        db.refresh(db_categoria)
    except exc.IntegrityError as e:
        db.rollback()
        return JSONResponse(
            status_code=303,
            content={"detail": f"Já existe uma categoria cadastrada com o nome: {categoria.nome}"}
        )
    return {"id": db_categoria.id}

add_pagination(app)