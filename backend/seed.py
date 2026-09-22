from sqlalchemy import select

from app.db.session import Base, SessionLocal, engine
from app.services.analysis import maintainability_metrics
from app.models import (
    AIComponent,
    Dependency,
    EvaluationDataset,
    EvaluationRecord,
    MetricResult,
    Project,
    ValidationTest,
)


def ensure_seed_data() -> int:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        project = db.scalar(select(Project).where(Project.name == 'Customer Support AI'))
        if project is None:
            project = Project(
                name='Customer Support AI',
                description='AI-powered customer support using LLM + RAG + knowledge repository',
            )
            db.add(project)
            db.flush()

        component_specs = [
            ('Customer Support Prompt', 'PROMPT'),
            ('System Prompt', 'SYSTEM_PROMPT'),
            ('LLM', 'LLM'),
            ('RAG Pipeline', 'RAG_PIPELINE'),
            ('Vector Database', 'VECTOR_DATABASE'),
            ('Product Knowledge Repository', 'KNOWLEDGE_REPOSITORY'),
            ('Customer API', 'API'),
            ('Evaluation Dataset', 'EVALUATION_DATASET'),
        ]
        components = {}
        for name, component_type in component_specs:
            component = db.scalar(
                select(AIComponent).where(
                    AIComponent.project_id == project.id,
                    AIComponent.name == name,
                )
            )
            if component is None:
                component = AIComponent(project_id=project.id, name=name, type=component_type)
                db.add(component)
                db.flush()
            components[name] = component

        dependency_specs = [
            ('System Prompt', 'LLM', 'uses', .90),
            ('Customer Support Prompt', 'LLM', 'uses', .85),
            ('LLM', 'RAG Pipeline', 'invokes', .80),
            ('RAG Pipeline', 'Vector Database', 'retrieves_from', .90),
            ('Vector Database', 'Product Knowledge Repository', 'depends_on', .88),
            ('RAG Pipeline', 'Customer API', 'feeds', .70),
            ('Evaluation Dataset', 'RAG Pipeline', 'evaluated_by', .65),
            ('Evaluation Dataset', 'Customer Support Prompt', 'evaluated_by', .60),
        ]
        for source, target, dependency_type, weight in dependency_specs:
            exists = db.scalar(
                select(Dependency).where(
                    Dependency.project_id == project.id,
                    Dependency.source_component_id == components[source].id,
                    Dependency.target_component_id == components[target].id,
                    Dependency.dependency_type == dependency_type,
                )
            )
            if exists is None:
                db.add(
                    Dependency(
                        project_id=project.id,
                        source_component_id=components[source].id,
                        target_component_id=components[target].id,
                        dependency_type=dependency_type,
                        weight=weight,
                    )
                )

        dataset = db.scalar(
            select(EvaluationDataset).where(
                EvaluationDataset.project_id == project.id,
                EvaluationDataset.version == 'demo-1',
            )
        )
        if dataset is None:
            dataset = EvaluationDataset(
                project_id=project.id,
                name='Customer Support Regression Set',
                version='demo-1',
                task_type='qa_rag',
                description='Versioned seed evaluation set for regression tracking.',
                sample_count=100,
            )
            db.add(dataset)

        scores = {
            'Accuracy': .87,
            'Grounding': .91,
            'Hallucination': .18,
            'Privacy': .94,
            'Safety': .92,
            'Edge Cases': .76,
            'Domain Specific': .83,
            'Retrieval Quality': .89,
            'Consistency': .84,
        }
        for category, score in scores.items():
            exists = db.scalar(
                select(EvaluationRecord).where(
                    EvaluationRecord.project_id == project.id,
                    EvaluationRecord.evaluation_category == category,
                    EvaluationRecord.dataset_version == 'demo-1',
                )
            )
            if exists is None:
                db.add(
                    EvaluationRecord(
                        project_id=project.id,
                        component_id=components['Evaluation Dataset'].id,
                        evaluation_category=category,
                        score=score,
                        dataset_version='demo-1',
                        notes='DEMO SEED DATA',
                    )
                )

        tests = [
            ('retrieval_precision', ['retrieval_quality'], 1.0, .45),
            ('retrieval_recall', ['retrieval_quality', 'grounding'], 1.2, .55),
            ('grounding_evaluation', ['grounding'], 1.0, .60),
            ('hallucination_evaluation', ['hallucination'], 1.1, .50),
            ('prompt_regression', ['format_compliance', 'consistency'], .8, .50),
            ('accuracy_evaluation', ['accuracy', 'domain_relevance'], 1.4, .55),
            ('safety_evaluation', ['safety'], 1.0, .60),
            ('privacy_evaluation', ['privacy'], 1.0, .70),
            ('consistency_evaluation', ['consistency'], .9, .45),
            ('latency_evaluation', ['latency'], .8, .40),
        ]
        for name, covers, cost, gain in tests:
            if db.scalar(select(ValidationTest).where(ValidationTest.test_name == name)) is None:
                db.add(
                    ValidationTest(
                        test_name=name,
                        behavior_dimensions_covered=covers,
                        estimated_cost=cost,
                        expected_information_gain=gain,
                    )
                )

        if db.scalar(
            select(MetricResult).where(
                MetricResult.project_id == project.id,
                MetricResult.metric_name == 'AIMI',
            )
        ) is None:
            seeded_evaluations = db.scalars(
                select(EvaluationRecord)
                .where(EvaluationRecord.project_id == project.id)
                .order_by(EvaluationRecord.recorded_at.asc())
            ).all()
            metric_values = maintainability_metrics(
                list(components.values()),
                db.scalars(select(Dependency).where(Dependency.project_id == project.id)).all(),
                seeded_evaluations,
                [],
            )
            for name, value in metric_values.items():
                db.add(MetricResult(project_id=project.id, metric_name=name, value=float(value)))

        db.commit()
        return project.id


if __name__ == '__main__':
    print('Seeded project', ensure_seed_data())
