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


class GeminiService:
    """Service for Gemini AI integration"""
    
    def __init__(self):
        if USE_NEW_GENAI:
            # New google.genai package
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
            self.model_name = 'gemini-pro'
        else:
            # Deprecated google.generativeai package
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-pro')
            self.client = None
    
    def generate_abstract_and_keywords(self, article_text):
        """Generate abstract and keywords from article text"""
        try:
            prompt = f"""
            Ushbu ilmiy maqolaning matni asosida unga mos annotatsiya (taxminan 50-70 so'z) 
            va 3-5 ta kalit so'zlar generatsiya qil. 
            
            Matn: {article_text}
            
            JSON formatida javob ber:
            {{
                "abstract": "annotatsiya matni",
                "keywords": ["kalit so'z 1", "kalit so'z 2", ...]
            }}
            """
            
            if USE_NEW_GENAI:
                # New API
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                result_text = response.text if hasattr(response, 'text') else str(response)
            else:
                # Deprecated API
                response = self.model.generate_content(prompt)
                result_text = response.text
            
            result = json.loads(result_text)
            
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
            
            Matn: "{text}"
            
            Faqat qayta yozilgan matnni ber, boshqa hech qanday izoh qo'sma.
            """
            
            if USE_NEW_GENAI:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                result_text = response.text if hasattr(response, 'text') else str(response)
            else:
                response = self.model.generate_content(prompt)
                result_text = response.text
            
            return result_text.strip()
        except Exception as e:
            logger.error(f"Error rephrasing text: {e}", exc_info=True)
            return text
    
    def format_references(self, references, style='APA'):
        """Format references according to citation style"""
        try:
            prompt = f"""
            Quyidagi adabiyotlar ro'yxatini {style} standartiga muvofiq formatlab ber.
            Har bir manbani alohida qatordan yoz.
            
            {references}
            """
            
            if USE_NEW_GENAI:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                result_text = response.text if hasattr(response, 'text') else str(response)
            else:
                response = self.model.generate_content(prompt)
                result_text = response.text
            
            return result_text.strip()
        except Exception as e:
            logger.error(f"Error formatting references: {e}", exc_info=True)
            return references
    
    def transliterate_text(self, text, direction='cyr_to_lat'):
        """Transliterate text between Cyrillic and Latin"""
        try:
            if direction == 'cyr_to_lat':
                prompt = f'Quyidagi kirill alifbosidagi matnni lotin alifbosiga o\'girib ber: "{text}"'
            else:
                prompt = f'Quyidagi lotin alifbosidagi matnni kirill alifbosiga o\'girib ber: "{text}"'
            
            if USE_NEW_GENAI:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                result_text = response.text if hasattr(response, 'text') else str(response)
            else:
                response = self.model.generate_content(prompt)
                result_text = response.text
            
            return result_text.strip()
        except Exception as e:
            logger.error(f"Error transliterating text: {e}", exc_info=True)
            return text
    
    def extract_text_from_pdf(self, file_path):
        """Extract text content from PDF file"""
        try:
            import os
            # Try PyPDF2 first
            try:
                import PyPDF2
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
                    return text.strip()
            except ImportError:
                # Fallback to pdfplumber
                try:
                    import pdfplumber
                    text = ""
                    with pdfplumber.open(file_path) as pdf:
                        for page in pdf.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text += page_text + "\n"
                    return text.strip()
                except ImportError:
                    # Final fallback: try basic text extraction
                    logger.warning("PyPDF2 and pdfplumber not installed, using basic extraction")
                    # Try to read as text file (for some PDFs)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                            return file.read()
                    except:
                        return ""
        except Exception as e:
            logger.error(f"Error extracting text from PDF {file_path}: {e}", exc_info=True)
            return ""
    
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
        Check plagiarism using Gemini AI
        Analyzes text for originality, plagiarism, and AI-generated content
        """
        try:
            if not text or len(text.strip()) < 50:
                logger.warning("Text too short for plagiarism check")
                return {
                    'plagiarism_percentage': 0.0,
                    'ai_content_percentage': 0.0,
                    'originality': 100.0
                }
            
            # Use Gemini to analyze text for plagiarism and AI content
            prompt = f"""Quyidagi matnni tahlil qiling va quyidagi formatda javob bering:
1. Plagiat foizi (0-100): matnning boshqa manbalardan ko'chirilgan qismi
2. AI kontent foizi (0-100): matnning sun'iy intellekt tomonidan yaratilgan qismi
3. Originality foizi (0-100): matnning o'ziga xosligi

Matn:
{text[:5000]}  # Limit to 5000 characters for API efficiency

Javobni quyidagi JSON formatida bering:
{{
    "plagiarism_percentage": <raqam>,
    "ai_content_percentage": <raqam>,
    "originality": <raqam>
}}"""

            if USE_NEW_GENAI:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                result_text = response.text if hasattr(response, 'text') else str(response)
            else:
                response = self.model.generate_content(prompt)
                result_text = response.text
            
            # Parse JSON response
            import json
            import re
            
            # Extract JSON from response
            json_match = re.search(r'\{[^}]+\}', result_text, re.DOTALL)
            if json_match:
                result_data = json.loads(json_match.group())
                
                plagiarism = float(result_data.get('plagiarism_percentage', 0))
                ai_content = float(result_data.get('ai_content_percentage', 0))
                originality = float(result_data.get('originality', 100 - plagiarism))
                
                # Ensure values are within valid range
                plagiarism = max(0, min(100, plagiarism))
                ai_content = max(0, min(100, ai_content))
                originality = max(0, min(100, originality))
                
                return {
                    'plagiarism_percentage': round(plagiarism, 2),
                    'ai_content_percentage': round(ai_content, 2),
                    'originality': round(originality, 2)
                }
            else:
                # Fallback: use simple heuristic analysis
                logger.warning("Could not parse JSON from Gemini response, using heuristic")
                return self._heuristic_plagiarism_check(text)
                
        except Exception as e:
            logger.error(f"Error checking plagiarism with Gemini: {e}", exc_info=True)
            # Fallback to heuristic method
            return self._heuristic_plagiarism_check(text)
    
    def _heuristic_plagiarism_check(self, text):
        """
        Heuristic plagiarism check as fallback
        Analyzes text patterns, repetition, and common phrases
        """
        try:
            import re
            from collections import Counter
            
            # Simple heuristic: check for repeated phrases
            words = text.lower().split()
            word_freq = Counter(words)
            
            # Check for very common words (potential plagiarism indicators)
            common_phrases = [
                'according to', 'as stated', 'it is important', 'in conclusion',
                'furthermore', 'moreover', 'however', 'therefore', 'thus'
            ]
            
            common_count = sum(1 for phrase in common_phrases if phrase in text.lower())
            plagiarism_score = min(25, common_count * 3)  # Max 25% from common phrases
            
            # Check for AI patterns (repetitive structures, formal language)
            sentences = re.split(r'[.!?]+', text)
            avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
            
            # AI content tends to have consistent sentence length
            ai_score = min(15, abs(avg_sentence_length - 20) * 0.5) if avg_sentence_length > 15 else 5
            
            originality = max(70, 100 - plagiarism_score - ai_score)
            
            return {
                'plagiarism_percentage': round(plagiarism_score, 2),
                'ai_content_percentage': round(ai_score, 2),
                'originality': round(originality, 2)
            }
        except Exception as e:
            logger.error(f"Error in heuristic plagiarism check: {e}", exc_info=True)
            # Final fallback
            return {
                'plagiarism_percentage': 0.0,
                'ai_content_percentage': 0.0,
                'originality': 100.0
            }


# Singleton instance - lazy initialization
_gemini_service_instance = None

def get_gemini_service():
    """Get or create Gemini service singleton instance"""
    global _gemini_service_instance
    if _gemini_service_instance is None:
        _gemini_service_instance = GeminiService()
    return _gemini_service_instance
