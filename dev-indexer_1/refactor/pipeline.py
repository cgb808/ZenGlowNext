"""Lightweight NLP utilities: NER, POS, stop-word removal, sentiment, QA.

Design goals:
- Zero heavy model load by default (fast heuristics / optional transformers gated by env vars)
- Each function returns structured dict with consistent keys
- Safe fallbacks when model deps absent

Env Flags:
 NLP_ENABLE_TRANSFORMERS=1  -> load small transformers pipelines (sentiment, QA)
 NLP_MODEL_SENTIMENT=name   -> override sentiment model (default: distilbert-base-uncased-finetuned-sst-2-english)
 NLP_MODEL_QA=name          -> override QA model (default: distilbert-base-cased-distilled-squad)

Usage:
 from app.nlp.pipeline import nlp_analyze
 result = nlp_analyze("What is the dosage of amoxicillin for strep throat?", tasks=["ner","sentiment","qa"], qa_context="Amoxicillin 500 mg twice daily for 10 days is common for strep throat.")

Returned schema (subset depending on tasks):
 {
   'text': original,
   'ner': [{'text': 'amoxicillin', 'label': 'DRUG', 'start': 16, 'end': 27}],
   'pos': [{'text': 'dosage', 'pos': 'NOUN'}],
   'no_stop': 'dosage amoxicillin strep throat',
   'sentiment': {'label': 'POSITIVE', 'score': 0.993},
   'qa': {'answer': '500 mg twice daily', 'score': 0.72}
 }
"""
from __future__ import annotations
import os
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Iterable, Optional

# Basic stop words (trimmed)
_STOP = {
    'the','a','an','is','are','to','of','and','or','for','with','on','in','at','as','by','be','this','that','it','from','was','were','can','do','does','what','how','why','when'
}

# Simple regex-based heuristic NER (very small domain-specific patterns)
_DRUG_PATTERN = re.compile(r"\b(amoxicillin|penicillin|azithromycin|ibuprofen|acetaminophen|doxycycline)\b", re.I)
_DOSAGE_PATTERN = re.compile(r"\b\d{1,4}\s?(mg|mcg|g|iu)\b", re.I)

@dataclass
class HeuristicEntity:
    text: str
    label: str
    start: int
    end: int

try:
    _ENABLE_TRANSFORMERS = bool(int(os.getenv("NLP_ENABLE_TRANSFORMERS","0")))
except ValueError:
    _ENABLE_TRANSFORMERS = False

_sentiment_pipe = None
_qa_pipe = None

if _ENABLE_TRANSFORMERS:
    try:
        from transformers import pipeline  # type: ignore
        def _load_sentiment():
            model = os.getenv("NLP_MODEL_SENTIMENT","distilbert-base-uncased-finetuned-sst-2-english")
            return pipeline("sentiment-analysis", model=model)
        def _load_qa():
            model = os.getenv("NLP_MODEL_QA","distilbert-base-cased-distilled-squad")
            return pipeline("question-answering", model=model)
        # Lazy load wrappers
        def _get_sentiment():
            global _sentiment_pipe
            if _sentiment_pipe is None:
                _sentiment_pipe = _load_sentiment()
            return _sentiment_pipe
        def _get_qa():
            global _qa_pipe
            if _qa_pipe is None:
                _qa_pipe = _load_qa()
            return _qa_pipe
    except Exception:  # pragma: no cover - any import failure fallbacks to heuristics
        _ENABLE_TRANSFORMERS = False
        def _get_sentiment(): return None
        def _get_qa(): return None
else:
    def _get_sentiment(): return None
    def _get_qa(): return None

# --- Core functions ---

def ner(text: str) -> List[Dict[str, Any]]:
    ents: List[HeuristicEntity] = []
    for pat, label in ((_DRUG_PATTERN, "DRUG"), (_DOSAGE_PATTERN, "DOSAGE")):
        for m in pat.finditer(text):
            ents.append(HeuristicEntity(m.group(0), label, m.start(), m.end()))
    return [e.__dict__ for e in ents]

def pos_tags(text: str) -> List[Dict[str,str]]:
    # Very lightweight fallback: classify tokens by suffix/pattern heuristics
    tokens = re.findall(r"[A-Za-z0-9_']+", text)
    out = []
    for tok in tokens:
        low = tok.lower()
        if low.endswith('ing'):
            pos = 'VERB'
        elif low.endswith('ed'):
            pos = 'VERB'
        elif low.endswith('ly'):
            pos = 'ADV'
        elif low in _STOP:
            pos = 'STOP'
        elif low[0].isupper():
            pos = 'NOUN'
        else:
            pos = 'NOUN'
        out.append({'text': tok, 'pos': pos})
    return out

def remove_stop_words(text: str) -> str:
    tokens = [t for t in re.findall(r"[A-Za-z0-9_']+", text.lower()) if t not in _STOP]
    return ' '.join(tokens)

def sentiment(text: str) -> Dict[str, Any]:
    pipe = _get_sentiment()
    if pipe is None:
        # Heuristic: neutral baseline with simple polarity hints
        low = text.lower()
        score = 0.5
        if any(w in low for w in ("good","great","excellent","helpful")):
            return {'label':'POSITIVE','score':0.9}
        if any(w in low for w in ("bad","terrible","awful","harm")):
            return {'label':'NEGATIVE','score':0.1}
        return {'label':'NEUTRAL','score':score}
    res = pipe(text)[0]
    return {'label': res['label'], 'score': float(res.get('score',0.0))}

def qa(question: str, context: str) -> Dict[str, Any]:
    pipe = _get_qa()
    if pipe is None:
        # Heuristic extract: pick first dosage entity or fallback to first sentence fragment
        ents = ner(context)
        for e in ents:
            if e['label'] == 'DOSAGE':
                return {'answer': e['text'], 'score': 0.2, 'heuristic': True}
        frag = context.split('.')
        return {'answer': frag[0].strip() if frag else context[:80], 'score': 0.05, 'heuristic': True}
    res = pipe({'question': question, 'context': context})
    return {'answer': res.get('answer',''), 'score': float(res.get('score',0.0))}

def nlp_analyze(text: str, tasks: Iterable[str], qa_context: Optional[str] = None) -> Dict[str, Any]:
    tasks_set = set(t.lower() for t in tasks)
    out: Dict[str, Any] = {'text': text}
    if 'ner' in tasks_set:
        out['ner'] = ner(text)
    if 'pos' in tasks_set:
        out['pos'] = pos_tags(text)
    if 'stop' in tasks_set or 'nostop' in tasks_set:
        out['no_stop'] = remove_stop_words(text)
    if 'sentiment' in tasks_set:
        out['sentiment'] = sentiment(text)
    if 'qa' in tasks_set and qa_context:
        out['qa'] = qa(text, qa_context)
    return out

__all__ = ['ner','pos_tags','remove_stop_words','sentiment','qa','nlp_analyze']
