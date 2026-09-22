from datetime import datetime, timezone, timedelta
from io import BytesIO
import hashlib
import hmac
import logging
import secrets
from typing import Any

import jwt
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import (
    Project, AIComponent, Dependency, EvaluationDataset, EvaluationRecord, ValidationTest,
    ChangeRequest, ImpactResult, BehavioralPrediction, MetricResult,
    ValidationResult, CalibrationRecord, PromptVersion, Experiment, User,
)
from app.services.analysis import (
    fingerprint, analyze, validation_plan, score_impact,
    maintainability_metrics, compare_validation_strategies,
)
from app.core.config import settings
from app.services.report import build_report

logger = logging.getLogger('aimpf.api')
router = APIRouter(prefix='/api')

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class RegisterIn(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)

class LoginIn(RegisterIn):
    pass

class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None

class ComponentIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    type: str = Field(min_length=1, max_length=64)
    version: str | None = None
    description: str | None = None
    criticality_override: float | None = Field(default=None, ge=0, le=1)

class DependencyIn(BaseModel):
    source_component_id: int
    target_component_id: int
    dependency_type: str = Field(min_length=1, max_length=64)
    weight: float = Field(ge=0, le=1)

class EvaluationIn(BaseModel):
    component_id: int | None = None
    evaluation_category: str = Field(min_length=1, max_length=128)
    score: float = Field(ge=0, le=1)
    dataset_version: str | None = None
    notes: str | None = None

class DatasetIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    version: str = Field(min_length=1, max_length=64)
    task_type: str = Field(min_length=1, max_length=64)
    description: str | None = None
    sample_count: int = Field(default=0, ge=0)

class ChangeIn(BaseModel):
    component_id: int
    change_type: str
    description: str
    severity: float = Field(ge=0, le=1)

class ObservationIn(BaseModel):
    test_id: int
    observed_value: float = Field(ge=0, le=1)
    behavior: str | None = None
    impact_result_id: int | None = None

class PromptIn(BaseModel):
    component_id: int
    version: str
    prompt_text: str
    metadata_json: dict[str, Any] = Field(default_factory=dict)

class ExperimentIn(BaseModel):
    name: str
    hypothesis: str
    baseline_precision: float | None = Field(default=None, ge=0, le=1)
    baseline_recall: float | None = Field(default=None, ge=0, le=1)
    aimpf_precision: float | None = Field(default=None, ge=0, le=1)
    aimpf_recall: float | None = Field(default=None, ge=0, le=1)

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 210_000)
    return f'pbkdf2_sha256$210000${salt.hex()}${digest.hex()}'

def _verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, rounds, salt_hex, digest_hex = encoded.split('$')
        if scheme != 'pbkdf2_sha256':
            return False
        candidate = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt_hex), int(rounds)).hex()
        return hmac.compare_digest(candidate, digest_hex)
    except Exception:
        return False

def _token_for(user: User) -> str:
    return jwt.encode({'sub': str(user.id), 'email': user.email, 'exp': datetime.now(timezone.utc) + timedelta(hours=24)}, settings.secret_key, algorithm='HS256')

def current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User | None:
    if not authorization:
        return None
    if not authorization.lower().startswith('bearer '):
        raise HTTPException(401, 'Invalid authorization header')
    try:
        payload = jwt.decode(authorization.split(' ', 1)[1], settings.secret_key, algorithms=['HS256'])
        user = db.get(User, int(payload['sub']))
    except Exception as exc:
        raise HTTPException(401, 'Invalid or expired token') from exc
    if not user:
        raise HTTPException(401, 'User not found')
    return user

def require_user(user: User | None = Depends(current_user)) -> User:
    if not user:
        raise HTTPException(401, 'Authentication required')
    return user

def _normalize_change_type(change_type: str) -> str:
    return str(change_type).strip().upper().replace(' ', '_').replace('-', '_')

def _project_or_404(pid: int, db: Session) -> Project:
    project = db.get(Project, pid)
    if not project:
        raise HTTPException(404, 'Project not found')
    return project

def _component_or_404(pid: int, cid: int, db: Session) -> AIComponent:
    component = db.get(AIComponent, cid)
    if not component or component.project_id != pid:
        raise HTTPException(404, 'Component not found')
    return component

# ---------------------------------------------------------------------------
# Health/auth
# ---------------------------------------------------------------------------
@router.get('/health')
def health():
    return {'status': 'ok', 'service': 'AIMPF', 'stack': 'FastAPI', 'algorithm_version': settings.algorithm_version}

@router.post('/auth/register')
def register(x: RegisterIn, db: Session = Depends(get_db)):
    email = x.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, 'Email already registered')
    user = User(email=email, password_hash=_hash_password(x.password))
    db.add(user); db.commit(); db.refresh(user)
    return {'token': _token_for(user), 'user': {'id': user.id, 'email': user.email}}

@router.post('/auth/login')
def login(x: LoginIn, db: Session = Depends(get_db)):
    email = x.email.strip().lower(); user = db.scalar(select(User).where(User.email == email))
    if not user or not _verify_password(x.password, user.password_hash):
        raise HTTPException(401, 'Invalid credentials')
    return {'token': _token_for(user), 'user': {'id': user.id, 'email': user.email}}

@router.get('/auth/me')
def me(user: User = Depends(require_user)):
    return {'id': user.id, 'email': user.email}

# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------
@router.get('/projects')
def projects(db: Session = Depends(get_db), user: User | None = Depends(current_user)):
    stmt = select(Project).order_by(Project.id)
    if user: stmt = stmt.where((Project.user_id == user.id) | (Project.user_id.is_(None)))
    out=[]
    for p in db.scalars(stmt).all():
        comps=db.scalars(select(AIComponent).where(AIComponent.project_id==p.id)).all()
        deps=db.scalars(select(Dependency).where(Dependency.project_id==p.id)).all()
        mets=db.scalar(select(MetricResult).where(MetricResult.project_id==p.id,MetricResult.metric_name=='AIMI').order_by(MetricResult.computed_at.desc()))
        out.append({'id':p.id,'name':p.name,'description':p.description,'aimi':mets.value if mets else None,'components':len(comps),'dependencies':len(deps)})
    return out

@router.post('/projects')
def create_project(x: ProjectIn, db: Session = Depends(get_db), user: User | None = Depends(current_user)):
    p=Project(name=x.name,description=x.description,user_id=user.id if user else None)
    db.add(p);db.commit();db.refresh(p)
    return {'id':p.id,'name':p.name,'description':p.description,'aimi':None,'components':0,'dependencies':0}

@router.get('/projects/{pid}')
def get_project(pid:int, db:Session=Depends(get_db)):
    p=db.get(Project,pid)
    if not p: raise HTTPException(404,'Project not found')
    return {'id':p.id,'name':p.name,'description':p.description,'user_id':p.user_id}

@router.patch('/projects/{pid}')
def update_project(pid:int,x:ProjectIn,db:Session=Depends(get_db),user:User|None=Depends(current_user)):
    p=db.get(Project,pid)
    if not p: raise HTTPException(404,'Project not found')
    if p.user_id and (not user or p.user_id!=user.id): raise HTTPException(403,'Forbidden')
    p.name=x.name;p.description=x.description;p.updated_at=datetime.now(timezone.utc);db.commit()
    return {'id':p.id,'name':p.name,'description':p.description}

@router.delete('/projects/{pid}')
def delete_project(pid:int,db:Session=Depends(get_db),user:User|None=Depends(current_user)):
    p=db.get(Project,pid)
    if not p: raise HTTPException(404,'Project not found')
    if p.user_id and (not user or p.user_id!=user.id): raise HTTPException(403,'Forbidden')
    db.delete(p);db.commit();return {'deleted':pid}

# ---------------------------------------------------------------------------
# Components/dependencies
# ---------------------------------------------------------------------------
@router.get('/projects/{pid}/components')
def components(pid:int,db:Session=Depends(get_db)):
    rows=db.scalars(select(AIComponent).where(AIComponent.project_id==pid).order_by(AIComponent.id)).all()
    return [{'id':c.id,'name':c.name,'type':c.type,'version':c.version,'description':c.description,'criticality_override':c.criticality_override} for c in rows]

@router.post('/projects/{pid}/components')
def create_component(pid:int,x:ComponentIn,db:Session=Depends(get_db)):
    if not db.get(Project,pid):raise HTTPException(404,'Project not found')
    c=AIComponent(project_id=pid,**x.model_dump());db.add(c);db.commit();db.refresh(c)
    return {'id':c.id,'name':c.name,'type':c.type,'version':c.version}

@router.patch('/projects/{pid}/components/{cid}')
def update_component(pid:int,cid:int,x:ComponentIn,db:Session=Depends(get_db)):
    c=db.get(AIComponent,cid)
    if not c or c.project_id!=pid:raise HTTPException(404,'Component not found')
    for k,v in x.model_dump().items():
        if v is not None or k in ('name','type'): setattr(c,k,v)
    c.updated_at=datetime.now(timezone.utc);db.commit();return {'id':c.id,'name':c.name,'type':c.type,'version':c.version}

@router.delete('/projects/{pid}/components/{cid}')
def delete_component(pid:int,cid:int,db:Session=Depends(get_db)):
    c=db.get(AIComponent,cid)
    if not c or c.project_id!=pid:raise HTTPException(404,'Component not found')
    db.delete(c);db.commit();return {'deleted':cid}

@router.get('/projects/{pid}/dependencies')
def dependencies(pid:int,db:Session=Depends(get_db)):
    rows=db.scalars(select(Dependency).where(Dependency.project_id==pid).order_by(Dependency.id)).all()
    return [{'id':d.id,'source_component_id':d.source_component_id,'target_component_id':d.target_component_id,'dependency_type':d.dependency_type,'weight':d.weight} for d in rows]

@router.post('/projects/{pid}/dependencies')
def create_dependency(pid:int,x:DependencyIn,db:Session=Depends(get_db)):
    if not db.get(Project,pid):raise HTTPException(404,'Project not found')
    for cid in (x.source_component_id,x.target_component_id):
        c=db.get(AIComponent,cid)
        if not c or c.project_id!=pid:raise HTTPException(400,'Both components must belong to project')
    d=Dependency(project_id=pid,**x.model_dump());db.add(d);db.commit();db.refresh(d)
    return {'id':d.id,'source_component_id':d.source_component_id,'target_component_id':d.target_component_id,'dependency_type':d.dependency_type,'weight':d.weight}

@router.delete('/projects/{pid}/dependencies/{did}')
def delete_dependency(pid:int,did:int,db:Session=Depends(get_db)):
    d=db.get(Dependency,did)
    if not d or d.project_id!=pid:raise HTTPException(404,'Dependency not found')
    db.delete(d);db.commit();return {'deleted':did}

@router.get('/projects/{pid}/graph')
def graph(pid:int,db:Session=Depends(get_db)):
    comps=db.scalars(select(AIComponent).where(AIComponent.project_id==pid)).all(); deps=db.scalars(select(Dependency).where(Dependency.project_id==pid)).all()
    return {'nodes':[{'id':str(c.id),'label':c.name,'type':c.type,'criticality':c.criticality_override} for c in comps],'edges':[{'id':str(d.id),'source':str(d.source_component_id),'target':str(d.target_component_id),'weight':d.weight,'type':d.dependency_type} for d in deps]}

@router.patch('/projects/{pid}/dependencies/{did}')
def update_dependency(pid:int,did:int,x:DependencyIn,db:Session=Depends(get_db)):
    d=db.get(Dependency,did)
    if not d or d.project_id!=pid: raise HTTPException(404,'Dependency not found')
    for cid in (x.source_component_id,x.target_component_id): _component_or_404(pid,cid,db)
    for k,v in x.model_dump().items(): setattr(d,k,v)
    db.commit();db.refresh(d)
    return {'id':d.id,'source_component_id':d.source_component_id,'target_component_id':d.target_component_id,'dependency_type':d.dependency_type,'weight':d.weight}

@router.patch('/projects/{pid}/evaluations/{eid}')
def update_evaluation(pid:int,eid:int,x:EvaluationIn,db:Session=Depends(get_db)):
    r=db.get(EvaluationRecord,eid)
    if not r or r.project_id!=pid: raise HTTPException(404,'Evaluation not found')
    if x.component_id:
        c=db.get(AIComponent,x.component_id)
        if not c or c.project_id!=pid: raise HTTPException(400,'Component not in project')
    for key,value in x.model_dump().items(): setattr(r,key,value)
    db.commit();db.refresh(r)
    return {'id':r.id,'score':r.score,'evaluation_category':r.evaluation_category,'dataset_version':r.dataset_version}

@router.delete('/projects/{pid}/evaluations/{eid}')
def delete_evaluation(pid:int,eid:int,db:Session=Depends(get_db)):
    r=db.get(EvaluationRecord,eid)
    if not r or r.project_id!=pid: raise HTTPException(404,'Evaluation not found')
    db.delete(r);db.commit();return {'deleted':eid}

@router.patch('/projects/{pid}/prompts/{prompt_id}')
def update_prompt(pid:int,prompt_id:int,x:PromptIn,db:Session=Depends(get_db)):
    r=db.get(PromptVersion,prompt_id)
    if not r or r.component_id != x.component_id or not db.get(AIComponent,x.component_id) or db.get(AIComponent,x.component_id).project_id!=pid:
        raise HTTPException(404,'Prompt version not found')
    r.version=x.version;r.prompt_text=x.prompt_text;r.metadata_json=x.metadata_json
    db.commit();db.refresh(r);return {'id':r.id,'component_id':r.component_id,'version':r.version}

@router.delete('/projects/{pid}/prompts/{prompt_id}')
def delete_prompt(pid:int,prompt_id:int,db:Session=Depends(get_db)):
    r=db.get(PromptVersion,prompt_id)
    if not r: raise HTTPException(404,'Prompt version not found')
    c=db.get(AIComponent,r.component_id)
    if not c or c.project_id!=pid: raise HTTPException(404,'Prompt version not found')
    db.delete(r);db.commit();return {'deleted':prompt_id}

@router.get('/projects/{pid}/criticality')
def criticality(pid:int,db:Session=Depends(get_db)):
    comps=db.scalars(select(AIComponent).where(AIComponent.project_id==pid)).all()
    deps=db.scalars(select(Dependency).where(Dependency.project_id==pid)).all()
    from app.services.analysis import build_graph
    g=build_graph(comps,deps)
    import networkx as nx
    between=nx.betweenness_centrality(g,normalized=True) if len(g) else {}
    return [{'id':c.id,'name':c.name,'type':c.type,'criticality':float(c.criticality_override if c.criticality_override is not None else g.nodes[c.id].get('criticality',.5)),'betweenness':float(between.get(c.id,0))} for c in sorted(comps,key=lambda x:(float(x.criticality_override if x.criticality_override is not None else g.nodes[x.id].get('criticality',.5)),between.get(x.id,0)),reverse=True)]

@router.get('/projects/{pid}/recommendations')
def recommendations(pid:int,db:Session=Depends(get_db)):
    comps=db.scalars(select(AIComponent).where(AIComponent.project_id==pid)).all()
    deps=db.scalars(select(Dependency).where(Dependency.project_id==pid)).all()
    evals=db.scalars(select(EvaluationRecord).where(EvaluationRecord.project_id==pid).order_by(EvaluationRecord.recorded_at.asc())).all()
    impacts=db.scalars(select(ImpactResult).join(ChangeRequest).where(ChangeRequest.project_id==pid).order_by(ImpactResult.created_at.desc()).limit(20)).all()
    rec=[]
    low_eval=sorted(evals,key=lambda e:e.score)[:3]
    for e in low_eval:
        rec.append({'priority':'HIGH' if e.score<.6 else 'MEDIUM','category':'behavioral','title':f'Improve {e.evaluation_category}','reason':f'Latest recorded score is {e.score:.2f}','action':'Add or strengthen a regression dataset and run validation after the next related change.'})
    if len(deps)>len(comps)*1.5:
        rec.append({'priority':'MEDIUM','category':'structure','title':'Review dependency density','reason':f'{len(deps)} dependencies across {len(comps)} components increase propagation surface.','action':'Remove unnecessary edges or lower weights when they are not runtime-critical.'})
    if any(i.risk=='HIGH' for i in impacts):
        rec.append({'priority':'HIGH','category':'change-risk','title':'Gate high-risk changes','reason':'Recent analyses contain HIGH-risk impact predictions.','action':'Require the selected adaptive validation tests before release.'})
    if not rec:
        rec.append({'priority':'LOW','category':'maintainability','title':'Keep an evaluation baseline','reason':'No immediate hotspot was detected.','action':'Continue versioned evaluations so future predictions have historical evidence.'})
    return rec

@router.get('/projects/{pid}/datasets')
def datasets(pid:int,db:Session=Depends(get_db)):
    rows=db.scalars(select(EvaluationDataset).where(EvaluationDataset.project_id==pid).order_by(EvaluationDataset.created_at.desc())).all()
    return [{'id':d.id,'name':d.name,'version':d.version,'task_type':d.task_type,'description':d.description,'sample_count':d.sample_count,'created_at':d.created_at} for d in rows]

@router.post('/projects/{pid}/datasets')
def create_dataset(pid:int,x:DatasetIn,db:Session=Depends(get_db)):
    _project_or_404(pid,db)
    d=EvaluationDataset(project_id=pid,**x.model_dump())
    db.add(d);db.commit();db.refresh(d)
    return {'id':d.id,'name':d.name,'version':d.version,'task_type':d.task_type,'description':d.description,'sample_count':d.sample_count}

@router.patch('/projects/{pid}/datasets/{dataset_id}')
def update_dataset(pid:int,dataset_id:int,x:DatasetIn,db:Session=Depends(get_db)):
    d=db.get(EvaluationDataset,dataset_id)
    if not d or d.project_id!=pid: raise HTTPException(404,'Dataset not found')
    for key,value in x.model_dump().items(): setattr(d,key,value)
    db.commit();db.refresh(d)
    return {'id':d.id,'name':d.name,'version':d.version,'task_type':d.task_type,'description':d.description,'sample_count':d.sample_count}

@router.delete('/projects/{pid}/datasets/{dataset_id}')
def delete_dataset(pid:int,dataset_id:int,db:Session=Depends(get_db)):
    d=db.get(EvaluationDataset,dataset_id)
    if not d or d.project_id!=pid: raise HTTPException(404,'Dataset not found')
    db.delete(d);db.commit();return {'deleted':dataset_id}

# ---------------------------------------------------------------------------
# Evaluations / prompt tracking / RAG
# ---------------------------------------------------------------------------
@router.get('/projects/{pid}/evaluations')
def evaluations(pid:int,db:Session=Depends(get_db)):
    rows=db.scalars(select(EvaluationRecord).where(EvaluationRecord.project_id==pid).order_by(EvaluationRecord.recorded_at.desc())).all()
    return [{'id':r.id,'component_id':r.component_id,'evaluation_category':r.evaluation_category,'score':r.score,'dataset_version':r.dataset_version,'notes':r.notes,'recorded_at':r.recorded_at} for r in rows]

@router.post('/projects/{pid}/evaluations')
def create_evaluation(pid:int,x:EvaluationIn,db:Session=Depends(get_db)):
    if not db.get(Project,pid):raise HTTPException(404,'Project not found')
    if x.component_id:
        c=db.get(AIComponent,x.component_id)
        if not c or c.project_id!=pid:raise HTTPException(400,'Component not in project')
    r=EvaluationRecord(project_id=pid,**x.model_dump());db.add(r);db.commit();db.refresh(r)
    return {'id':r.id,'score':r.score,'evaluation_category':r.evaluation_category}

@router.get('/projects/{pid}/prompts')
def prompts(pid:int,db:Session=Depends(get_db)):
    rows=db.scalars(select(PromptVersion).join(AIComponent).where(AIComponent.project_id==pid).order_by(PromptVersion.created_at.desc())).all()
    return [{'id':r.id,'component_id':r.component_id,'version':r.version,'prompt_text':r.prompt_text,'metadata_json':r.metadata_json,'created_at':r.created_at} for r in rows]

@router.post('/projects/{pid}/prompts')
def create_prompt(pid:int,x:PromptIn,db:Session=Depends(get_db)):
    c=db.get(AIComponent,x.component_id)
    if not c or c.project_id!=pid:raise HTTPException(400,'Component not in project')
    r=PromptVersion(**x.model_dump());db.add(r);db.commit();db.refresh(r)
    return {'id':r.id,'component_id':r.component_id,'version':r.version}

@router.post('/projects/{pid}/evaluations/rag')
def evaluate_rag(pid:int,payload:dict[str,Any],db:Session=Depends(get_db)):
    """Deterministic offline RAG evaluator. Inputs are gold document ids/text and retrieved ids/text."""
    gold=list(payload.get('gold_ids') or []); retrieved=list(payload.get('retrieved_ids') or [])
    gold_set=set(map(str,gold)); ret=list(map(str,retrieved)); ret_set=set(ret)
    tp=len(gold_set & ret_set); precision=tp/max(1,len(ret)); recall=tp/max(1,len(gold_set)); f1=2*precision*recall/max(1e-9,precision+recall)
    query_terms=set(str(payload.get('query','')).lower().split()); docs=payload.get('retrieved_texts') or []
    lexical=sum(1 for d in docs if query_terms and query_terms & set(str(d).lower().split()))/max(1,len(docs))
    grounding=float(payload.get('grounding_score', recall))
    category_scores={'retrieval quality':f1,'grounding':grounding,'accuracy':float(payload.get('accuracy',f1))}
    for cat,score in category_scores.items(): db.add(EvaluationRecord(project_id=pid,evaluation_category=cat,score=max(0,min(1,score)),dataset_version=payload.get('dataset_version'),notes='Offline RAG evaluator'))
    db.commit()
    return {'precision':precision,'recall':recall,'f1':f1,'lexical_relevance':lexical,'grounding':grounding,'scores':category_scores,'evaluator':'deterministic-offline','dataset_version':payload.get('dataset_version')}

@router.get('/projects/{pid}/evaluations/summary')
def evaluation_summary(pid:int,db:Session=Depends(get_db)):
    rows=db.scalars(select(EvaluationRecord).where(EvaluationRecord.project_id==pid).order_by(EvaluationRecord.recorded_at.desc(), EvaluationRecord.id.desc())).all()
    grouped={}
    for r in rows:
        key=r.evaluation_category.strip().lower()
        grouped.setdefault(key,[]).append(r.score)
    return [{'category':k,'count':len(v),'latest':v[0],'mean':sum(v)/len(v),'min':min(v),'max':max(v)} for k,v in sorted(grouped.items())]

@router.get('/projects/{pid}/analysis/{impact_id}')
def analysis_detail(pid:int,impact_id:int,db:Session=Depends(get_db)):
    ir=db.get(ImpactResult,impact_id)
    if not ir: raise HTTPException(404,'Impact result not found')
    cr=db.get(ChangeRequest,ir.change_request_id)
    if not cr or cr.project_id!=pid: raise HTTPException(404,'Impact result not found')
    preds=db.scalars(select(BehavioralPrediction).where(BehavioralPrediction.impact_result_id==impact_id)).all()
    vals=db.scalars(select(ValidationResult).where(ValidationResult.impact_result_id==impact_id).order_by(ValidationResult.recorded_at.desc())).all()
    tests=db.scalars(select(ValidationTest).order_by(ValidationTest.id)).all()
    plan=validation_plan({p.behavior:p.predicted_value for p in preds},{p.behavior:p.confidence for p in preds},tests)
    return {'impact':{'id':ir.id,'overall_impact':ir.overall_component_impact,'risk':ir.risk,'confidence':ir.confidence,'structural':ir.structural_impact,'behavioral':ir.behavioral_impact,'evaluation':ir.evaluation_impact,'maintenance':ir.maintenance_impact,'estimated_hours_min':ir.estimated_hours_min,'estimated_hours_max':ir.estimated_hours_max},'change':{'id':cr.id,'component_id':cr.component_id,'change_type':cr.change_type,'description':cr.description,'severity':cr.severity,'fingerprint':cr.fingerprint,'algorithm_version':cr.algorithm_version,'configuration_version':cr.configuration_version},'predictions':[{'behavior':p.behavior,'predicted_value':p.predicted_value,'confidence':p.confidence,'evidence_status':p.evidence_status} for p in preds],'validations':[{'id':v.id,'behavior':v.behavior,'predicted_value':v.predicted_value,'observed_value':v.observed_value,'residual':v.prediction_error,'absolute_error':v.absolute_error,'percentage_error':v.percentage_error} for v in vals], 'validation_plan': plan}

# ---------------------------------------------------------------------------
# Change analysis and adaptive validation
# ---------------------------------------------------------------------------
@router.post('/projects/{pid}/changes/analyze')
def change(pid:int,x:ChangeIn,db:Session=Depends(get_db)):
    c=db.get(AIComponent,x.component_id)
    if not c or c.project_id!=pid:raise HTTPException(404,'Component not found')
    comps=db.scalars(select(AIComponent).where(AIComponent.project_id==pid)).all()
    deps=db.scalars(select(Dependency).where(Dependency.project_id==pid)).all()
    evals=db.scalars(select(EvaluationRecord).where(EvaluationRecord.project_id==pid)).all()
    tests=db.scalars(select(ValidationTest)).all()
    normalized=_normalize_change_type(x.change_type)
    fp=fingerprint(normalized,x.severity,x.description)
    a=analyze(x.component_id,normalized,fp,comps,deps,evals)
    calibrations=db.scalars(select(CalibrationRecord).where(CalibrationRecord.project_id==pid).order_by(CalibrationRecord.created_at.asc())).all()
    latest_cal={r.behavior:r for r in calibrations}
    for b,cal in latest_cal.items():
        if b in a['predictions']:
            a['predictions'][b]=max(0.0,min(1.0,a['predictions'][b]+0.5*(cal.updated_value-a['predictions'][b])))
            a['prediction_confidence'][b]=min(0.95,a['prediction_confidence'].get(b,0.5)+0.05)
    a.update(score_impact(a['structural'], a['predictions'], a['prediction_confidence']))
    plan=validation_plan(a['predictions'],a['prediction_confidence'],tests)
    cr=ChangeRequest(project_id=pid,component_id=x.component_id,change_type=normalized,description=x.description,severity=x.severity,fingerprint=fp,algorithm_version=settings.algorithm_version,configuration_version='1')
    db.add(cr);db.flush()
    ir=ImpactResult(change_request_id=cr.id,structural_impact=a['structural'],behavioral_impact=a['behavioral'],evaluation_impact=a['evaluation'],maintenance_impact=a['maintenance'],overall_component_impact=a['overall'],confidence=a['confidence'],risk=a['risk'],estimated_hours_min=2+8*a['overall'],estimated_hours_max=6+20*a['overall'])
    db.add(ir);db.flush()
    for b,v in a['predictions'].items():
        db.add(BehavioralPrediction(impact_result_id=ir.id,behavior=b,baseline_value=None,predicted_value=v,confidence=a['prediction_confidence'].get(b,0.5),evidence_status='HISTORICAL' if evals else 'PRIOR'))
    db.commit()
    logger.info('change_analyzed project=%s impact=%s risk=%s',pid,ir.id,ir.risk)
    return {'id':ir.id,'overall_impact':a['overall'],'risk':a['risk'],'confidence':a['confidence'],'estimated_hours_min':ir.estimated_hours_min,'estimated_hours_max':ir.estimated_hours_max,'fingerprint':fp,'predictions':a['predictions'],'validation':{'selected':[t['name'] for t in plan['selected']],'selected_ids':[t['id'] for t in plan['selected']],'reasons':{t['name']:t['reason'] for t in plan['selected']},'expected_uncertainty_reduction':plan['expected_uncertainty_reduction'],'uncertainty_before':plan['initial_uncertainty'],'uncertainty_after':plan['final_uncertainty']}}

@router.get('/projects/{pid}/changes')
def changes(pid:int,limit:int=Query(50,ge=1,le=200),db:Session=Depends(get_db)):
    rows=db.scalars(select(ImpactResult).join(ChangeRequest).where(ChangeRequest.project_id==pid).order_by(ImpactResult.created_at.desc()).limit(limit)).all()
    out=[]
    for ir in rows:
        cr=db.get(ChangeRequest,ir.change_request_id);c=db.get(AIComponent,cr.component_id)
        out.append({'impact_result_id':ir.id,'change_id':cr.id,'component_id':cr.component_id,'component_name':c.name if c else None,'change_type':cr.change_type,'description':cr.description,'severity':cr.severity,'overall_impact':ir.overall_component_impact,'confidence':ir.confidence,'risk':ir.risk,'created_at':ir.created_at})
    return out

@router.get('/validation/tests')
def validation_tests(db:Session=Depends(get_db)):
    rows=db.scalars(select(ValidationTest).order_by(ValidationTest.id)).all()
    return [{'id':t.id,'test_name':t.test_name,'behavior_dimensions_covered':t.behavior_dimensions_covered,'estimated_cost':t.estimated_cost,'expected_information_gain':t.expected_information_gain} for t in rows]

@router.get('/projects/{pid}/validation')
def validation_history(pid:int,db:Session=Depends(get_db)):
    rows=db.scalars(select(ValidationResult).join(ImpactResult).join(ChangeRequest).where(ChangeRequest.project_id==pid).order_by(ValidationResult.recorded_at.desc())).all()
    out=[]
    for r in rows:
        t=db.get(ValidationTest,r.test_id); ir=db.get(ImpactResult,r.impact_result_id); cr=db.get(ChangeRequest,ir.change_request_id) if ir else None
        out.append({'id':r.id,'impact_result_id':r.impact_result_id,'test_id':r.test_id,'test_name':t.test_name if t else 'Unknown','behavior':r.behavior,'predicted_value':r.predicted_value,'observed_value':r.observed_value,'prediction_error':r.prediction_error,'absolute_error':r.absolute_error,'percentage_error':r.percentage_error,'recorded_at':r.recorded_at,'change_id':cr.id if cr else None})
    calibrations=db.scalars(select(CalibrationRecord).where(CalibrationRecord.project_id==pid).order_by(CalibrationRecord.created_at.desc())).all()
    return {'results':out,'calibration':[{'id':c.id,'behavior':c.behavior,'previous_value':c.previous_value,'residual':c.residual,'updated_value':c.updated_value,'learning_rate':c.learning_rate,'created_at':c.created_at} for c in calibrations]}

@router.post('/projects/{pid}/validation/observe')
def record_validation(pid:int,x:ObservationIn,db:Session=Depends(get_db)):
    test=db.get(ValidationTest,x.test_id)
    if not test: raise HTTPException(404,'Validation test not found')
    ir=db.get(ImpactResult,x.impact_result_id) if x.impact_result_id else None
    if ir:
        cr=db.get(ChangeRequest,ir.change_request_id)
        if not cr or cr.project_id!=pid: raise HTTPException(404,'Impact result not found for project')
    else:
        ir=db.scalars(select(ImpactResult).join(ChangeRequest).where(ChangeRequest.project_id==pid).order_by(ImpactResult.created_at.desc())).first()
    if not ir:raise HTTPException(404,'No analyzed change found for project')
    preds=db.scalars(select(BehavioralPrediction).where(BehavioralPrediction.impact_result_id==ir.id)).all(); available={p.behavior:p for p in preds}
    behavior=x.behavior
    if behavior is None:
        covered=[b for b in test.behavior_dimensions_covered if b in available]
        behavior=max(covered,key=lambda b:available[b].predicted_value) if covered else None
    if behavior is None or behavior not in available:
        raise HTTPException(400,'Test does not cover a predicted behavior for the selected change')
    covered_dimensions={str(item) for item in test.behavior_dimensions_covered}
    if behavior not in covered_dimensions:
        raise HTTPException(400, f'Test {test.test_name} does not cover behavior {behavior}')
    p=available[behavior]; residual=float(x.observed_value-p.predicted_value); absolute=abs(residual); pct=(absolute/max(abs(p.predicted_value),1e-6))*100
    vr=ValidationResult(impact_result_id=ir.id,test_id=test.id,behavior=behavior,predicted_value=p.predicted_value,observed_value=x.observed_value,prediction_error=residual,absolute_error=absolute,percentage_error=pct)
    db.add(vr)
    previous=p.predicted_value
    latest=db.scalars(select(CalibrationRecord).where(CalibrationRecord.project_id==pid,CalibrationRecord.behavior==behavior).order_by(CalibrationRecord.created_at.desc())).first()
    if latest: previous=latest.updated_value
    updated=max(0,min(1,previous+0.25*residual))
    cal=CalibrationRecord(project_id=pid,behavior=behavior,previous_value=previous,residual=residual,updated_value=updated,learning_rate=.25)
    db.add(cal);db.commit();db.refresh(vr);db.refresh(cal)
    return {'validation_result_id':vr.id,'impact_result_id':ir.id,'test_name':test.test_name,'behavior':behavior,'predicted_value':p.predicted_value,'observed_value':x.observed_value,'prediction_error':residual,'absolute_error':absolute,'percentage_error':pct,'calibration':{'previous_value':previous,'residual':residual,'updated_value':updated,'learning_rate':.25}}

# ---------------------------------------------------------------------------
# Metrics / experiments / reporting
# ---------------------------------------------------------------------------
@router.get('/projects/{pid}/metrics')
def metrics(pid:int,db:Session=Depends(get_db)):
    rows=db.scalars(select(MetricResult).where(MetricResult.project_id==pid).order_by(MetricResult.computed_at.desc())).all()
    return [{'id':m.id,'metric_name':m.metric_name,'value':m.value,'computed_at':m.computed_at} for m in rows]

@router.get('/projects/{pid}/metrics/definitions')
def metric_definitions(pid:int,db:Session=Depends(get_db)):
    if not db.get(Project,pid): raise HTTPException(404,'Project not found')
    return [
        {'name':'CCS','label':'Coupling Complexity Score','unit':'0–100','description':'Structural coupling score; higher values indicate lower dependency coupling.'},
        {'name':'PVS','label':'Prediction Stability Score','unit':'0–100','description':'Historical prediction reliability derived from validation residuals; lower error produces a higher score.'},
        {'name':'KFS','label':'Knowledge Fitness Score','unit':'0–100','description':'Weighted grounding, retrieval, domain-relevance and accuracy evidence; higher is better.'},
        {'name':'ECS','label':'Edge Complexity Score','unit':'0–100','description':'Graph-structure score; higher values indicate a sparser, simpler dependency graph.'},
        {'name':'CDS','label':'Coupling Density Score','unit':'0–100','description':'Dependency-weight score; higher values indicate a lighter coupling burden.'},
        {'name':'BSS','label':'Behavior Stability Score','unit':'0–100','description':'Behavioral quality plus repeatability and consistency evidence; higher is better.'},
        {'name':'MPS','label':'Maintenance Pressure Score','unit':'0–100','description':'Inverse maintenance-pressure proxy based on dependency count; higher indicates lower pressure.'},
        {'name':'AIMI','label':'AI Maintainability Index','unit':'0–100','description':'Composite maintainability index; higher is better.'},
    ]

@router.post('/projects/{pid}/metrics/recompute')
def recompute_metrics(pid:int,db:Session=Depends(get_db)):
    _project_or_404(pid, db)
    comps=db.scalars(select(AIComponent).where(AIComponent.project_id==pid)).all()
    deps=db.scalars(select(Dependency).where(Dependency.project_id==pid)).all()
    evals=db.scalars(select(EvaluationRecord).where(EvaluationRecord.project_id==pid)).all()
    validations=db.scalars(
        select(ValidationResult)
        .join(ImpactResult)
        .join(ChangeRequest)
        .where(ChangeRequest.project_id==pid)
    ).all()
    metric_values=maintainability_metrics(comps,deps,evals,validations)
    for name,val in metric_values.items():
        db.add(MetricResult(project_id=pid,metric_name=name,value=float(val)))
    db.commit()
    return metric_values

@router.get('/projects/{pid}/experiments')
def experiments(pid:int,db:Session=Depends(get_db)):
    rows=db.scalars(select(Experiment).where(Experiment.project_id==pid).order_by(Experiment.created_at.desc())).all()
    return [{'id':e.id,'name':e.name,'hypothesis':e.hypothesis,'baseline_precision':e.baseline_precision,'baseline_recall':e.baseline_recall,'aimpf_precision':e.aimpf_precision,'aimpf_recall':e.aimpf_recall,'result':e.result_json,'created_at':e.created_at} for e in rows]

@router.post('/projects/{pid}/experiments')
def create_experiment(pid:int,x:ExperimentIn,db:Session=Depends(get_db)):
    if not db.get(Project,pid): raise HTTPException(404,'Project not found')
    e=Experiment(project_id=pid,**x.model_dump());db.add(e);db.commit();db.refresh(e);return {'id':e.id,'name':e.name}

@router.patch('/projects/{pid}/experiments/{experiment_id}')
def update_experiment(pid:int,experiment_id:int,x:ExperimentIn,db:Session=Depends(get_db)):
    e=db.get(Experiment,experiment_id)
    if not e or e.project_id!=pid: raise HTTPException(404,'Experiment not found')
    for key,value in x.model_dump().items(): setattr(e,key,value)
    db.commit();db.refresh(e)
    return {'id':e.id,'name':e.name,'hypothesis':e.hypothesis}

@router.delete('/projects/{pid}/experiments/{experiment_id}')
def delete_experiment(pid:int,experiment_id:int,db:Session=Depends(get_db)):
    e=db.get(Experiment,experiment_id)
    if not e or e.project_id!=pid: raise HTTPException(404,'Experiment not found')
    db.delete(e);db.commit()
    return {'deleted':experiment_id}

@router.post('/projects/{pid}/experiments/run')
def run_experiment(pid:int,db:Session=Depends(get_db)):
    _project_or_404(pid, db)
    ir=db.scalars(select(ImpactResult).join(ChangeRequest).where(ChangeRequest.project_id==pid).order_by(ImpactResult.created_at.desc())).first()
    if not ir:raise HTTPException(404,'Run a change analysis first')
    preds=db.scalars(select(BehavioralPrediction).where(BehavioralPrediction.impact_result_id==ir.id)).all()
    tests=db.scalars(select(ValidationTest).order_by(ValidationTest.id)).all()
    comparison=compare_validation_strategies(
        {p.behavior:p.predicted_value for p in preds},
        {p.behavior:p.confidence for p in preds},
        tests,
    )
    adaptive=next(x for x in comparison['strategies'] if x['strategy']=='AIMPF adaptive')
    result={
        'impact_result_id':ir.id,
        'adaptive_tests':adaptive['selected_tests'],
        'adaptive_test_ids':[t.id for t in tests if t.test_name in adaptive['selected_tests']],
        'full_suite_tests':[t.test_name for t in tests],
        'adaptive_cost':adaptive['cost'],
        'full_suite_cost':adaptive['full_suite_cost'],
        'cost_reduction':adaptive['cost_reduction'],
        'uncertainty_before':adaptive['uncertainty_before'],
        'uncertainty_after':adaptive['uncertainty_after'],
        'uncertainty_reduction':adaptive['uncertainty_reduction'],
        'selection_efficiency':adaptive['selection_efficiency'],
        'baseline_comparison':comparison,
    }
    exp=Experiment(project_id=pid,name='Adaptive validation baseline comparison',hypothesis='AIMPF should achieve useful uncertainty reduction at lower validation cost than simple deterministic baselines.',result_json=result)
    db.add(exp);db.commit();
    result['experiment_id']=exp.id
    return result

@router.get('/projects/{pid}/research/comparison')
def research_comparison(pid:int,db:Session=Depends(get_db)):
    _project_or_404(pid, db)
    ir=db.scalars(select(ImpactResult).join(ChangeRequest).where(ChangeRequest.project_id==pid).order_by(ImpactResult.created_at.desc())).first()
    if not ir: raise HTTPException(404,'Run a change analysis first')
    preds=db.scalars(select(BehavioralPrediction).where(BehavioralPrediction.impact_result_id==ir.id)).all()
    tests=db.scalars(select(ValidationTest).order_by(ValidationTest.id)).all()
    comparison=compare_validation_strategies(
        {p.behavior:p.predicted_value for p in preds},
        {p.behavior:p.confidence for p in preds},
        tests,
    )
    comparison['impact_result_id']=ir.id
    comparison['risk']=ir.risk
    comparison['overall_impact']=ir.overall_component_impact
    return comparison

@router.get('/projects/{pid}/experiments/{experiment_id}')
def experiment_detail(pid:int,experiment_id:int,db:Session=Depends(get_db)):
    e=db.get(Experiment,experiment_id)
    if not e or e.project_id!=pid: raise HTTPException(404,'Experiment not found')
    return {'id':e.id,'name':e.name,'hypothesis':e.hypothesis,'baseline_precision':e.baseline_precision,'baseline_recall':e.baseline_recall,'aimpf_precision':e.aimpf_precision,'aimpf_recall':e.aimpf_recall,'result':e.result_json,'created_at':e.created_at}

@router.get('/projects/{pid}/report.pdf')
def report_pdf(pid:int,db:Session=Depends(get_db)):
    p=db.get(Project,pid)
    if not p:raise HTTPException(404,'Project not found')
    comps=db.scalars(select(AIComponent).where(AIComponent.project_id==pid)).all()
    deps=db.scalars(select(Dependency).where(Dependency.project_id==pid)).all()
    impacts=db.scalars(select(ImpactResult).join(ChangeRequest).where(ChangeRequest.project_id==pid).order_by(ImpactResult.created_at.desc()).limit(12)).all()
    vals=db.scalars(select(ValidationResult).join(ImpactResult).join(ChangeRequest).where(ChangeRequest.project_id==pid).order_by(ValidationResult.recorded_at.desc()).limit(12)).all()
    calibrations=db.scalars(select(CalibrationRecord).where(CalibrationRecord.project_id==pid).order_by(CalibrationRecord.created_at.desc()).limit(12)).all()
    mets=db.scalars(select(MetricResult).where(MetricResult.project_id==pid).order_by(MetricResult.computed_at.desc()).limit(20)).all()
    experiments=db.scalars(select(Experiment).where(Experiment.project_id==pid).order_by(Experiment.created_at.desc()).limit(8)).all()
    sections=[
        ('Project overview',[f'Project: {p.name}',f'Description: {p.description or "—"}',f'Components: {len(comps)}',f'Dependencies: {len(deps)}']),
        ('Recent impact analyses',[f'#{ir.id} {db.get(ChangeRequest,ir.change_request_id).change_type} | impact={ir.overall_component_impact:.3f} | risk={ir.risk} | confidence={ir.confidence:.3f} | effort={ir.estimated_hours_min:.1f}–{ir.estimated_hours_max:.1f} h' for ir in impacts] or ['No change analyses recorded.']),
        ('Validation and calibration', [f'validation#{v.id} | behavior={v.behavior} | predicted={v.predicted_value:.3f} | observed={v.observed_value:.3f} | residual={v.prediction_error:.3f} | abs_error={v.absolute_error:.3f}' for v in vals] + [f'calibration#{c.id} | {c.behavior}: {c.previous_value:.3f} → {c.updated_value:.3f} | residual={c.residual:.3f} | lr={c.learning_rate:.2f}' for c in calibrations] or ['No validation observations recorded.']),
        ('Maintainability metrics',[f'{m.metric_name}: {m.value:.2f} ({m.computed_at})' for m in mets] or ['No metrics recorded yet.']),
        ('Research comparison',[f'#{e.id} {e.name} | {e.hypothesis}' for e in experiments] + [
            f"{row['strategy']}: cost={row['cost']:.2f}, uncertainty reduction={row['uncertainty_reduction']*100:.1f}%, tests={', '.join(row['selected_tests'])}"
            for e in experiments[:1] if isinstance(e.result_json, dict)
            for row in e.result_json.get('baseline_comparison',{}).get('strategies',[])
        ] or ['No baseline comparison has been run.']),
        ('Methodology note',[
            'AIMI is the direct mean of seven higher-is-better 0–100 metrics.',
            'PVS uses historical prediction residuals when available; KFS uses retrieval/grounding/domain evidence; BSS uses behavioral quality, consistency and repeatability.',
            'The baseline comparison is deterministic and controlled; it is not a statistical significance test.'
        ]),
    ]
    b=build_report(f'AIMPF Report — {p.name}',sections)
    return StreamingResponse(b,media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="aimpf-{pid}-report.pdf"'})

@router.get('/projects/{pid}/dashboard')
def dashboard(pid:int,db:Session=Depends(get_db)):
    p=db.get(Project,pid)
    if not p:raise HTTPException(404,'Project not found')
    comps=db.scalars(select(AIComponent).where(AIComponent.project_id==pid)).all(); deps=db.scalars(select(Dependency).where(Dependency.project_id==pid)).all(); mets=db.scalars(select(MetricResult).where(MetricResult.project_id==pid,MetricResult.metric_name=='AIMI').order_by(MetricResult.computed_at.desc()).limit(12)).all(); impacts=db.scalars(select(ImpactResult).join(ChangeRequest).where(ChangeRequest.project_id==pid).order_by(ImpactResult.created_at.desc()).limit(8)).all()
    return {'project':{'id':p.id,'name':p.name,'description':p.description,'aimi':mets[0].value if mets else None,'components':len(comps),'dependencies':len(deps)},'high_risk':sum(1 for i in impacts if i.risk=='HIGH'),'trend':[{'label':str(m.computed_at.date()),'aimi':m.value} for m in reversed(mets)],'recent':[{'id':i.id,'change_type':db.get(ChangeRequest,i.change_request_id).change_type,'overall_impact':i.overall_component_impact,'risk':i.risk} for i in impacts]}
