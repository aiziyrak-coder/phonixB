"""
Gemini AI Service for Phoenix Scientific Platform
Integrates with Google Gemini API for various AI tasks
"""

import google.generativeai as genai
from django.conf import settings
import json


class GeminiService:
    """Service for Gemini AI integration"""
    
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-pro')
    
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
            
            response = self.model.generate_content(prompt)
            result = json.loads(response.text)
            
            return {
                'abstract': result.get('abstract', ''),
                'keywords': result.get('keywords', [])
            }
        except Exception as e:
            print(f"Error generating abstract and keywords: {e}")
            return {'abstract': '', 'keywords': []}
    
    def rephrase_text(self, text):
        """Rephrase text in academic style"""
        try:
            prompt = f"""
            Quyidagi matnni ilmiy uslubda, ma'nosini saqlagan holda qayta yozib ber (rephrasing).
            
            Matn: "{text}"
            
            Faqat qayta yozilgan matnni ber, boshqa hech qanday izoh qo'sma.
            """
            
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error rephrasing text: {e}")
            return text
    
    def format_references(self, references, style='APA'):
        """Format references according to citation style"""
        try:
            prompt = f"""
            Quyidagi adabiyotlar ro'yxatini {style} standartiga muvofiq formatlab ber.
            Har bir manbani alohida qatordan yoz.
            
            {references}
            """
            
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error formatting references: {e}")
            return references
    
    def transliterate_text(self, text, direction='cyr_to_lat'):
        """Transliterate text between Cyrillic and Latin"""
        try:
            if direction == 'cyr_to_lat':
                prompt = f'Quyidagi kirill alifbosidagi matnni lotin alifbosiga o\'girib ber: "{text}"'
            else:
                prompt = f'Quyidagi lotin alifbosidagi matnni kirill alifbosiga o\'girib ber: "{text}"'
            
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error transliterating text: {e}")
            return text
    
    def count_words_in_document(self, file_content):
        """Estimate word count from document content"""
        try:
            # Simple word count estimation
            words = file_content.split()
            return len(words)
        except Exception as e:
            print(f"Error counting words: {e}")
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


# Singleton instance
gemini_service = GeminiService()
