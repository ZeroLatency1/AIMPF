from app.models import EvaluationDataset

def test_evaluation_dataset_model_registered():
    assert EvaluationDataset.__tablename__ == 'evaluation_datasets'
