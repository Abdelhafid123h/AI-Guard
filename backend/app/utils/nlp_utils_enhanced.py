from transformers import pipeline
import spacy
import os

class NLPModels:
    def __init__(self):
        print("🔄 Initialisation des modèles NLP...")
        
        # 1. Modèle spaCy français
        try:
            self.spacy_model = spacy.load("fr_core_news_sm")
            print("✅ Modèle spaCy français chargé")
        except OSError:
            print("⚠️ Modèle spaCy français non trouvé. Installation requise : python -m spacy download fr_core_news_sm")
            self.spacy_model = None
        
        # 2. Modèle BERT original (multilingue)
        try:
            self.bert_model = pipeline(
                "ner",
                model="dslim/bert-base-NER",
                aggregation_strategy="simple",
                device=-1  # CPU
            )
            print("✅ Modèle BERT multilingue chargé")
        except Exception as e:
            print(f"⚠️ Erreur chargement BERT : {e}")
            self.bert_model = None
        
        # 3. NOUVEAU : Modèle CamemBERT français spécialisé
        try:
            print("📦 Tentative de chargement de CamemBERT...")
            self.camembert_model = pipeline(
                "ner",
                model="Jean-Baptiste/camembert-ner",
                aggregation_strategy="simple",
                device=-1,  # CPU
                return_all_scores=False,
                trust_remote_code=True
            )
            print("✅ Modèle CamemBERT français chargé")
        except Exception as e:
            print(f"⚠️ CamemBERT non disponible : {str(e)[:100]}...")
            self.camembert_model = None
        
        # 4. NOUVEAU : Modèle français alternatif (plus léger)
        try:
            print("📦 Tentative de chargement du modèle français alternatif...")
            # Utilisons un modèle plus simple et fiable
            self.french_model = pipeline(
                "ner",
                model="dbmdz/bert-large-cased-finetuned-conll03-english",  # Modèle plus stable
                aggregation_strategy="simple",
                device=-1
            )
            print("✅ Modèle français alternatif chargé")
        except Exception as e:
            print(f"⚠️ Modèle alternatif non disponible : {str(e)[:100]}...")
            self.french_model = None
            
        print("🎯 Initialisation des modèles terminée")
        
    def get_available_models(self):
        """Retourne la liste des modèles disponibles"""
        models = []
        if self.bert_model:
            models.append("BERT (multilingue)")
        if self.camembert_model:
            models.append("CamemBERT (français)")
        if hasattr(self, 'french_model') and self.french_model:
            models.append("Modèle français alternatif")
        if self.spacy_model:
            models.append("spaCy (français)")
        return models
