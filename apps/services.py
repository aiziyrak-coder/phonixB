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
        Simulate plagiarism check
        In production, integrate with real plagiarism detection service
        """
        # This is a simulation - integrate real service in production
        import random
        return {
            'plagiarism_percentage': round(random.uniform(5, 25), 2),
            'ai_content_percentage': round(random.uniform(3, 15), 2),
            'originality': round(random.uniform(70, 95), 2)
        }


# Singleton instance - lazy initialization
_gemini_service_instance = None

def get_gemini_service():
    """Get or create Gemini service singleton instance"""
    global _gemini_service_instance
    if _gemini_service_instance is None:
        _gemini_service_instance = GeminiService()
    return _gemini_service_instance
