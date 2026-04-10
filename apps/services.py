"""
Gemini AI Service for Phoenix Scientific Platform
Integrates with Google Gemini API for various AI tasks
"""

try:
    # Try new google.genai package first
    from google import genai
    USE_NEW_GENAI = True
except ImportError:
    # Fallback to deprecated google.generativeai
    import google.generativeai as genai
    USE_NEW_GENAI = False
    import warnings
    warnings.warn(
        "google.generativeai package is deprecated. Please install google-genai package: pip install google-genai",
        FutureWarning,
        stacklevel=2
    )

from django.conf import settings
import json
import logging

logger = logging.getLogger(__name__)


def _parse_json_from_llm_text(result_text: str):
    """
    Gemini ba'zan ```json ... ``` yoki matn orasiga JSON qo'shib qaytaradi.
    """
    if not result_text or not str(result_text).strip():
        return None
    s = str(result_text).strip()
    if '```' in s:
        for part in s.split('```'):
            chunk = part.strip()
            if chunk.lower().startswith('json'):
                chunk = chunk[4:].lstrip()
            if chunk.startswith('{'):
                try:
                    return json.loads(chunk)
                except json.JSONDecodeError:
                    continue
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    start = s.find('{')
    end = s.rfind('}')
    if start >= 0 and end > start:
        try:
            return json.loads(s[start : end + 1])
        except json.JSONDecodeError:
            pass
    return None


def _extract_docx_text_via_zip(file_path: str) -> str:
    """DOCX is a ZIP of XML; read word/document.xml without treating the whole file as plain text."""
    import zipfile
    from xml.etree import ElementTree as ET

    try:
        with zipfile.ZipFile(file_path, 'r') as zf:
            names = zf.namelist()
            doc_xml = 'word/document.xml'
            if doc_xml not in names:
                return ''
            data = zf.read(doc_xml)
        root = ET.fromstring(data)
        parts = []
        for el in root.iter():
            tag = el.tag.split('}')[-1] if '}' in el.tag else el.tag
            if tag == 't' and el.text:
                parts.append(el.text)
            elif tag == 'tab':
                parts.append(' ')
        text = ' '.join(parts)
        return ' '.join(text.split())
    except Exception as e:
        logger.debug(f'DOCX zip/XML extraction failed: {e}')
        return ''


def extract_plain_text_from_file(file_path: str) -> str:
    """
    Extract readable text for word counting / analysis. No Gemini client — safe for translation pricing.
    DOCX: docx2txt, then ZIP+document.xml fallback (never read .docx as raw UTF-8).
    """
    import os

    try:
        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.docx':
            try:
                import docx2txt
                text = docx2txt.process(file_path)
                if text and text.strip():
                    return text.strip()
            except ImportError:
                logger.warning('docx2txt not installed; using ZIP fallback for DOCX')
            except Exception as e:
                logger.warning(f'docx2txt failed for {file_path}: {e}')
            zip_text = _extract_docx_text_via_zip(file_path)
            return zip_text.strip() if zip_text else ''

        if ext == '.txt':
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read().strip()
            except Exception as e:
                logger.error(f'Error reading TXT {file_path}: {e}')
                return ''

        # PDF — avval pdfplumber (sifat yaxshiroq), keyin PyPDF2
        try:
            import pdfplumber
            text = ''
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + '\n'
            if text.strip():
                return text.strip()
        except ImportError:
            logger.debug('pdfplumber not installed')
        except Exception as e:
            logger.debug(f'pdfplumber failed: {e}')

        try:
            import PyPDF2
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ''
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + '\n'
                if text.strip():
                    return text.strip()
        except Exception as e:
            logger.debug(f'PyPDF2 extraction failed: {e}')

        if ext in ('.doc',):
            return ''

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read().strip()
        except Exception:
            return ''

    except Exception as e:
        logger.error(f'extract_plain_text_from_file failed for {file_path}: {e}', exc_info=True)
        return ''


class GeminiService:
    """Service for Gemini AI integration"""
    
    def __init__(self):
        self.api_key = (getattr(settings, "GEMINI_API_KEY", "") or "").strip()
        self.model_name = (getattr(settings, "GEMINI_MODEL", None) or "gemini-1.5-flash").strip() or "gemini-1.5-flash"
        self.max_output_tokens = int(getattr(settings, "GEMINI_MAX_OUTPUT_TOKENS", 8192) or 8192)
        self.plagiarism_input_chars = int(getattr(settings, "GEMINI_PLAGIARISM_INPUT_CHARS", 12000) or 12000)
        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not set; Gemini deep analysis will be skipped (heuristic-only)")
        if USE_NEW_GENAI:
            self.client = genai.Client(api_key=self.api_key) if self.api_key else None
            self.model = None
        else:
            self.client = None
            if self.api_key:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.model_name)
            else:
                self.model = None

    def _generate_text(self, prompt: str) -> str | None:
        """Bitta LLM chaqiruvi — ikkala SDK uchun."""
        if not self.api_key:
            return None
        try:
            if USE_NEW_GENAI:
                if not self.client:
                    return None
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                )
                if hasattr(response, "text") and response.text:
                    return response.text.strip()
                return str(response).strip() if response is not None else None
            if not self.model:
                return None
            import google.generativeai as genai_mod

            gen_cfg = genai_mod.GenerationConfig(
                temperature=0.25,
                max_output_tokens=min(self.max_output_tokens, 8192),
            )
            response = self.model.generate_content(prompt, generation_config=gen_cfg)
            if not response or not getattr(response, "text", None):
                return None
            return response.text.strip()
        except Exception as e:
            logger.error("Gemini generate_content failed: %s", e, exc_info=True)
            return None

    def generate_abstract_and_keywords(self, article_text):
        """Generate abstract and keywords from article text"""
        try:
            prompt = f"""
            Ushbu ilmiy maqolaning matni asosida unga mos annotatsiya (taxminan 50-70 so'z) 
            va 3-5 ta kalit so'zlar generatsiya qil. 
            
            Matn: {article_text[:20000]}
            
            JSON formatida javob ber:
            {{
                "abstract": "annotatsiya matni",
                "keywords": ["kalit so'z 1", "kalit so'z 2", ...]
            }}
            """
            result_text = self._generate_text(prompt)
            if not result_text:
                return {'abstract': '', 'keywords': []}
            result = _parse_json_from_llm_text(result_text)
            if not isinstance(result, dict):
                return {'abstract': '', 'keywords': []}
            return {
                'abstract': result.get('abstract', ''),
                'keywords': result.get('keywords', [])
            }
        except Exception as e:
            logger.error(f"Error generating abstract and keywords: {e}", exc_info=True)
            return {'abstract': '', 'keywords': []}
    
    def rephrase_text(self, text):
        """Rephrase text in academic style"""
        try:
            prompt = f"""
            Quyidagi matnni ilmiy uslubda, ma'nosini saqlagan holda qayta yozib ber (rephrasing).
            
            Matn: "{text[:15000]}"
            
            Faqat qayta yozilgan matnni ber, boshqa hech qanday izoh qo'sma.
            """
            out = self._generate_text(prompt)
            return (out or text).strip()
        except Exception as e:
            logger.error(f"Error rephrasing text: {e}", exc_info=True)
            return text
    
    def format_references(self, references, style='APA'):
        """Format references according to citation style"""
        try:
            prompt = f"""
            Quyidagi adabiyotlar ro'yxatini {style} standartiga muvofiq formatlab ber.
            Har bir manbani alohida qatordan yoz.
            
            {str(references)[:20000]}
            """
            out = self._generate_text(prompt)
            return (out or references).strip() if isinstance(references, str) else (out or str(references)).strip()
        except Exception as e:
            logger.error(f"Error formatting references: {e}", exc_info=True)
            return references
    
    def transliterate_text(self, text, direction='cyr_to_lat'):
        """Transliterate text between Cyrillic and Latin"""
        try:
            snippet = text[:12000] if text else ''
            if direction == 'cyr_to_lat':
                prompt = f'Quyidagi kirill alifbosidagi matnni lotin alifbosiga o\'girib ber: "{snippet}"'
            else:
                prompt = f'Quyidagi lotin alifbosidagi matnni kirill alifbosiga o\'girib ber: "{snippet}"'
            out = self._generate_text(prompt)
            return (out or text).strip()
        except Exception as e:
            logger.error(f"Error transliterating text: {e}", exc_info=True)
            return text
    
    def extract_text_from_document(self, file_path):
        """Extract text content from PDF, DOCX, DOC, or TXT files"""
        return extract_plain_text_from_file(file_path)

    def extract_text_from_pdf(self, file_path):
        """Backward-compatible name: PDF/DOCX/TXT — bitta ajratuvchi."""
        return extract_plain_text_from_file(file_path)
    
    def count_words_in_document(self, file_content):
        """Estimate word count from document content"""
        try:
            # Simple word count estimation
            words = file_content.split()
            return len(words)
        except Exception as e:
            logger.error(f"Error counting words: {e}", exc_info=True)
            return 0
    
    def check_plagiarism(self, text):
        """
        Advanced plagiarism & AI content detection engine.
        Multi-dimensional analysis inspired by Turnitin, Copyleaks, GPTZero, Originality.ai.
        Returns detailed report with per-section breakdown, confidence scores, and risk levels.
        """
        import re
        import math
        from collections import Counter

        if not text or len(text.strip()) < 50:
            return self._empty_report()

        # ── 1. Split text into logical sections for per-section analysis ──
        sections = self._split_into_sections(text)

        # ── 2. Run local heuristic analysis (always available, fast) ──
        heuristic = self._advanced_heuristic_analysis(text, sections)

        # ── 3. Run Gemini AI deep analysis ──
        gemini_result = self._gemini_deep_analysis(text, sections)

        # ── 4. Merge results with weighted ensemble ──
        report = self._merge_analysis(heuristic, gemini_result, text, sections)

        return report

    def _empty_report(self):
        return {
            'plagiarism_percentage': 0.0,
            'ai_content_percentage': 0.0,
            'originality': 100.0,
            'report': {
                'overall_risk': 'low',
                'confidence': 0,
                'word_count': 0,
                'sentence_count': 0,
                'sections': [],
                'plagiarism_breakdown': {
                    'direct_copy': 0, 'paraphrase': 0, 'mosaic': 0, 'self_citation': 0
                },
                'ai_detection': {
                    'overall_ai_probability': 0,
                    'human_probability': 100,
                    'mixed_probability': 0,
                    'model_confidence': 'low',
                    'patterns': []
                },
                'stylometric': {
                    'vocabulary_richness': 0, 'avg_sentence_length': 0,
                    'sentence_length_variance': 0, 'readability_score': 0,
                    'passive_voice_ratio': 0, 'transition_density': 0
                },
                'recommendations': [],
                'analysis_mode': 'insufficient_text',
                'llm_model': None,
                'disclaimer_uz': 'Tekshirish uchun matn yetarli emas (kamida ~50 belgi).',
            }
        }

    def _split_into_sections(self, text):
        import re
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n|\n{2,}', text) if p.strip() and len(p.strip()) > 30]
        if not paragraphs:
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
            chunk_size = max(3, len(sentences) // 5)
            paragraphs = [' '.join(sentences[i:i+chunk_size]) for i in range(0, len(sentences), chunk_size)]
        if not paragraphs:
            paragraphs = [text]
        return paragraphs[:20]

    def _advanced_heuristic_analysis(self, text, sections):
        import re, math
        from collections import Counter

        words = text.lower().split()
        word_count = len(words)
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        sentence_count = max(len(sentences), 1)

        # ── Vocabulary richness (Type-Token Ratio) ──
        unique_words = set(words)
        ttr = len(unique_words) / max(word_count, 1)

        # ── Sentence length stats ──
        sent_lengths = [len(s.split()) for s in sentences]
        avg_sent_len = sum(sent_lengths) / sentence_count
        variance = sum((l - avg_sent_len) ** 2 for l in sent_lengths) / sentence_count
        std_dev = math.sqrt(variance)

        # ── Readability (Flesch-like simplified) ──
        syllable_count = sum(max(1, len(re.findall(r'[aeiouyAEIOUY]', w))) for w in words)
        readability = max(0, min(100, 206.835 - 1.015 * (word_count / sentence_count) - 84.6 * (syllable_count / max(word_count, 1))))

        # ── Passive voice detection ──
        passive_patterns = re.findall(r'\b(?:is|are|was|were|been|being|be)\s+\w+(?:ed|en|t)\b', text.lower())
        passive_ratio = len(passive_patterns) / sentence_count * 100

        # ── Transition word density ──
        transitions = ['however', 'furthermore', 'moreover', 'therefore', 'consequently',
                       'nevertheless', 'additionally', 'in addition', 'on the other hand',
                       'in contrast', 'similarly', 'likewise', 'as a result', 'thus',
                       'hence', 'accordingly', 'meanwhile', 'subsequently', 'specifically',
                       'for instance', 'for example', 'in particular', 'notably']
        text_lower = text.lower()
        transition_count = sum(1 for t in transitions if t in text_lower)
        transition_density = transition_count / sentence_count * 100

        # ── AI Detection Heuristics ──
        # Low variance = AI-like uniformity
        uniformity_score = max(0, 30 - std_dev * 3) if std_dev < 10 else 0
        # High transition density = AI-like
        transition_ai_signal = min(25, max(0, (transition_density - 8) * 3))
        # Very consistent paragraph lengths = AI
        para_lengths = [len(s.split()) for s in sections]
        para_variance = sum((l - sum(para_lengths)/max(len(para_lengths),1))**2 for l in para_lengths) / max(len(para_lengths),1)
        para_uniformity = max(0, 20 - math.sqrt(para_variance) * 0.5) if para_variance < 400 else 0
        # Repetitive phrase patterns
        bigrams = [' '.join(words[i:i+2]) for i in range(len(words)-1)]
        bigram_freq = Counter(bigrams)
        repetitive_bigrams = sum(1 for _, c in bigram_freq.items() if c > 3)
        repetition_signal = min(15, repetitive_bigrams * 2)

        ai_heuristic = min(95, uniformity_score + transition_ai_signal + para_uniformity + repetition_signal)

        # ── Plagiarism Heuristics ──
        # Common academic clichés (potential copy-paste indicators)
        cliche_phrases = [
            'it is well known that', 'studies have shown that', 'research indicates',
            'according to recent studies', 'the results suggest that', 'it can be concluded',
            'plays an important role', 'has been widely studied', 'in recent years',
            'the purpose of this study', 'the aim of this research', 'significant impact on',
            'comprehensive analysis', 'systematic review', 'literature review shows'
        ]
        cliche_count = sum(1 for p in cliche_phrases if p in text_lower)
        cliche_signal = min(20, cliche_count * 4)

        # Long exact n-gram repetitions (5-grams)
        fivegrams = [' '.join(words[i:i+5]) for i in range(len(words)-4)]
        fivegram_freq = Counter(fivegrams)
        repeated_fivegrams = sum(1 for _, c in fivegram_freq.items() if c > 2)
        ngram_signal = min(25, repeated_fivegrams * 5)

        plagiarism_heuristic = min(90, cliche_signal + ngram_signal)

        # ── Per-section scores ──
        section_results = []
        for idx, sec in enumerate(sections):
            sec_words = sec.lower().split()
            sec_sents = [s.strip() for s in re.split(r'[.!?]+', sec) if s.strip()]
            sec_sent_count = max(len(sec_sents), 1)
            sec_sent_lens = [len(s.split()) for s in sec_sents]
            sec_avg = sum(sec_sent_lens) / sec_sent_count
            sec_var = sum((l - sec_avg)**2 for l in sec_sent_lens) / sec_sent_count
            sec_std = math.sqrt(sec_var)

            sec_ai = min(95, max(0, 30 - sec_std * 3) + min(20, sum(1 for t in transitions if t in sec.lower()) / sec_sent_count * 30))
            sec_plag = min(90, sum(1 for p in cliche_phrases if p in sec.lower()) * 8)

            section_results.append({
                'index': idx + 1,
                'preview': sec[:120] + ('...' if len(sec) > 120 else ''),
                'word_count': len(sec_words),
                'plagiarism_score': round(sec_plag, 1),
                'ai_score': round(sec_ai, 1),
                'risk': 'high' if max(sec_plag, sec_ai) > 60 else 'medium' if max(sec_plag, sec_ai) > 30 else 'low'
            })

        return {
            'ai_score': round(ai_heuristic, 2),
            'plagiarism_score': round(plagiarism_heuristic, 2),
            'word_count': word_count,
            'sentence_count': sentence_count,
            'sections': section_results,
            'stylometric': {
                'vocabulary_richness': round(ttr * 100, 1),
                'avg_sentence_length': round(avg_sent_len, 1),
                'sentence_length_variance': round(std_dev, 1),
                'readability_score': round(readability, 1),
                'passive_voice_ratio': round(passive_ratio, 1),
                'transition_density': round(transition_density, 1),
            }
        }

    def _gemini_deep_analysis(self, text, sections):
        """Run deep Gemini AI analysis with professional prompt."""
        if not self.api_key:
            return None
        lim = max(4000, min(int(self.plagiarism_input_chars), 100_000))
        sample = (text or '')[:lim]
        prompt = f"""You are an advanced academic integrity analysis engine, combining the capabilities of Turnitin, Copyleaks, GPTZero, and Originality.ai.

Analyze the following academic text with extreme precision. Provide a comprehensive JSON report.

TEXT TO ANALYZE (first {lim} characters):
\"\"\"
{sample}
\"\"\"

Return ONLY valid JSON (no markdown, no explanation) with this exact structure:
{{
  "plagiarism_percentage": <float 0-100>,
  "ai_content_percentage": <float 0-100>,
  "originality": <float 0-100>,
  "plagiarism_breakdown": {{
    "direct_copy": <float 0-100>,
    "paraphrase": <float 0-100>,
    "mosaic": <float 0-100>,
    "self_citation": <float 0-100>
  }},
  "ai_detection": {{
    "overall_ai_probability": <float 0-100>,
    "human_probability": <float 0-100>,
    "mixed_probability": <float 0-100>,
    "model_confidence": "<low|medium|high>",
    "patterns": ["<string>"]
  }},
  "section_analysis": [
    {{ "section_index": <int>, "plagiarism_score": <float>, "ai_score": <float>, "flag": "<clean|suspicious|flagged>", "note": "<string>" }}
  ],
  "recommendations": ["<string>"],
  "sources": [
    {{
      "source": "<string: full URL where text might be found, e.g. https://scholar.google.com/scholar?q=ENCODED_QUERY or https://www.google.com/search?q=ENCODED_QUERY or https://cyberleninka.ru/... or real-looking academic URL>",
      "snippet": "<string: short excerpt from the text that may be plagiarized (20-80 chars)>",
      "similarity": <float 0-100, estimated match percentage for this source>
    }}
  ]
}}
IMPORTANT: For "sources", do a deep analysis: identify specific phrases or sentences that look copied. For each, suggest a concrete search URL (Google Scholar, Google, CyberLeninka, eLibrary, ResearchGate, etc.) using the suspicious phrase as the search query (URL-encoded). Provide 0-8 sources. If no clear plagiarism, return empty sources array."""

        for attempt in range(2):
            try:
                result_text = self._generate_text(prompt)
                if not result_text:
                    logger.warning("Gemini plagiarism: empty response (attempt %s)", attempt + 1)
                    continue
                result = _parse_json_from_llm_text(result_text)
                if isinstance(result, dict) and any(
                    k in result for k in ('plagiarism_percentage', 'ai_content_percentage', 'originality')
                ):
                    return result
                logger.warning("Gemini plagiarism: invalid JSON structure (attempt %s)", attempt + 1)
            except Exception as e:
                logger.error("Gemini deep analysis attempt failed: %s", e, exc_info=True)
        return None

    def _merge_analysis(self, heuristic, gemini, text, sections):
        """Merge heuristic + Gemini results with weighted ensemble."""
        import math

        # Weights: Gemini 0.65, Heuristic 0.35 (if Gemini available)
        if gemini:
            w_g, w_h = 0.65, 0.35
            plag = round(w_g * float(gemini.get('plagiarism_percentage', 0)) + w_h * heuristic['plagiarism_score'], 1)
            ai = round(w_g * float(gemini.get('ai_content_percentage', 0)) + w_h * heuristic['ai_score'], 1)
            orig = round(max(0, 100 - plag * 0.6 - ai * 0.4), 1)

            g_breakdown = gemini.get('plagiarism_breakdown', {})
            breakdown = {
                'direct_copy': round(float(g_breakdown.get('direct_copy', 0)), 1),
                'paraphrase': round(float(g_breakdown.get('paraphrase', 0)), 1),
                'mosaic': round(float(g_breakdown.get('mosaic', 0)), 1),
                'self_citation': round(float(g_breakdown.get('self_citation', 0)), 1),
            }

            g_ai = gemini.get('ai_detection', {})
            ai_detection = {
                'overall_ai_probability': round(float(g_ai.get('overall_ai_probability', ai)), 1),
                'human_probability': round(float(g_ai.get('human_probability', 100 - ai)), 1),
                'mixed_probability': round(float(g_ai.get('mixed_probability', 0)), 1),
                'model_confidence': g_ai.get('model_confidence', 'medium'),
                'patterns': g_ai.get('patterns', [])[:10],
            }

            recommendations = gemini.get('recommendations', [])[:8]

            # Merge section analysis
            g_sections = {s.get('section_index', i+1): s for i, s in enumerate(gemini.get('section_analysis', []))}
            merged_sections = []
            for hs in heuristic['sections']:
                idx = hs['index']
                gs = g_sections.get(idx, {})
                sec_plag = round(w_g * float(gs.get('plagiarism_score', 0)) + w_h * hs['plagiarism_score'], 1)
                sec_ai = round(w_g * float(gs.get('ai_score', 0)) + w_h * hs['ai_score'], 1)
                risk = 'high' if max(sec_plag, sec_ai) > 60 else 'medium' if max(sec_plag, sec_ai) > 30 else 'low'
                merged_sections.append({
                    'index': idx,
                    'preview': hs['preview'],
                    'word_count': hs['word_count'],
                    'plagiarism_score': sec_plag,
                    'ai_score': sec_ai,
                    'risk': risk,
                    'flag': gs.get('flag', risk),
                    'note': gs.get('note', ''),
                })
            confidence = 85
            analysis_mode = 'hybrid'
            llm_model = self.model_name
            disclaimer_uz = (
                'Natija lokal heuristic va LLM (Gemini) tahlili aralashmasi; rasmiy plagiat/AI qidiruvi o‘rnini bosmaydi. '
                'Yakuniy qaror inson eksperti uchun yo‘riqnoma sifatida qabul qilinsin.'
            )
        else:
            # Heuristic only
            plag = heuristic['plagiarism_score']
            ai = heuristic['ai_score']
            orig = round(max(0, 100 - plag * 0.6 - ai * 0.4), 1)
            breakdown = {'direct_copy': 0, 'paraphrase': 0, 'mosaic': 0, 'self_citation': 0}
            ai_detection = {
                'overall_ai_probability': ai,
                'human_probability': round(100 - ai, 1),
                'mixed_probability': 0,
                'model_confidence': 'low',
                'patterns': [],
            }
            merged_sections = heuristic['sections']
            recommendations = []
            confidence = 45
            analysis_mode = 'heuristic_only'
            llm_model = None
            disclaimer_uz = (
                'GEMINI_API_KEY yo‘q yoki LLM javob bermadi — faqat lokal heuristic tahlil ishlatildi. '
                'Aniqroq baho uchun serverda Gemini kalitini sozlang.'
            )

        plag = max(0, min(100, plag))
        ai = max(0, min(100, ai))
        orig = max(0, min(100, orig))

        overall_risk = 'high' if max(plag, ai) > 60 else 'medium' if max(plag, ai) > 30 else 'low'

        if not recommendations:
            if plag > 50:
                recommendations.append("Matnda ko'chirilgan qismlar ko'p. Iltimos, o'z so'zlaringiz bilan qayta yozing.")
            if ai > 50:
                recommendations.append("AI tomonidan yaratilgan kontent aniqlandi. Matnni shaxsiy uslubda qayta ishlang.")
            if plag < 30 and ai < 30:
                recommendations.append("Matn yaxshi originallikka ega. Kichik tahrirlar bilan yanada yaxshilash mumkin.")

        sources = []
        if gemini and isinstance(gemini.get('sources'), list):
            for s in gemini['sources'][:12]:
                if isinstance(s, dict) and s.get('source'):
                    sources.append({
                        'source': str(s.get('source', '')).strip()[:500],
                        'snippet': str(s.get('snippet', ''))[:300],
                        'similarity': min(100, max(0, float(s.get('similarity', 0)))),
                    })

        return {
            'plagiarism_percentage': plag,
            'ai_content_percentage': ai,
            'originality': orig,
            'report': {
                'overall_risk': overall_risk,
                'confidence': confidence,
                'word_count': heuristic['word_count'],
                'sentence_count': heuristic['sentence_count'],
                'sections': merged_sections,
                'plagiarism_breakdown': breakdown,
                'ai_detection': ai_detection,
                'stylometric': heuristic['stylometric'],
                'recommendations': recommendations,
                'sources': sources,
                'analysis_mode': analysis_mode,
                'llm_model': llm_model,
                'disclaimer_uz': disclaimer_uz,
            },
            'sources': sources,
        }

    def suggest_udk(self, article_title, abstract, keywords, udc_reference_text):
        """
        AI deep analysis: suggest the most suitable UDK (Universal Decimal Classification) code
        for the article based on its title, abstract and keywords. Uses udc_reference_text
        (list of code + description) to pick the best match.
        Returns {"udk_code": "...", "udk_description": "..."} or None on failure.
        """
        try:
            keywords_str = ', '.join(keywords) if isinstance(keywords, (list, tuple)) else str(keywords or '')
            prompt = f"""Sen ilmiy maqolalar uchun UDK (Universal o'nli klassifikatsiya) kodini tanlashda yordam beradigan mutaxassissan.

MAQOLA:
Sarlavha: {article_title or ''}
Annotatsiya: {(abstract or '')[:1500]}
Kalit so'zlar: {keywords_str}

Quyidagi ro'yxatdan maqola mavzusiga ENG MOS va ENG ANIQ bitta UDK kodini tanla.
MUHIM: Faqat ro'yxatda KO'RSATILGAN kodlardan birini qaytaring. Hech qachon 33, 9, 30, 61 kabi oddiy kodlar yozma — ro'yxatda bunday kodlar yo'q. Faqat nuqta bor aniq kod (masalan 332.1, 330.1, 001.892) tanlang.

RUXSAT ETILGAN UDK RO'YXATI:
{udc_reference_text}

Javobni faqat quyidagi JSON formatida bering, boshqa matn yozma:
{{"udk_code": "tanlangan aniq kod", "udk_description": "qisqa tavsif (o'zbekcha yoki ruscha)"}}
"""
            raw = self._generate_text(prompt)
            if not raw:
                return None
            data = _parse_json_from_llm_text(raw)
            if not isinstance(data, dict):
                return None
            code = (data.get('udk_code') or '').strip()
            desc = (data.get('udk_description') or '').strip()[:500]
            if code:
                return {'udk_code': code, 'udk_description': desc}
        except Exception as e:
            logger.error(f"Gemini suggest_udk failed: {e}", exc_info=True)
        return None


# Singleton instance - lazy initialization
_gemini_service_instance = None

def get_gemini_service():
    """Get or create Gemini service singleton instance"""
    global _gemini_service_instance
    if _gemini_service_instance is None:
        _gemini_service_instance = GeminiService()
    return _gemini_service_instance
