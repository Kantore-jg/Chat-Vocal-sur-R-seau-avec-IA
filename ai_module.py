import json
import wave
import io
import pyttsx3
from vosk import Model, KaldiRecognizer
import pyaudio

class LocalAI:
    def __init__(self, vosk_model_path="model"):
        """
        Initialiser l'IA locale
        
        Args:
            vosk_model_path: Chemin vers le modèle Vosk
                             Télécharger depuis: https://alphacephei.com/vosk/models
                             Recommandé: vosk-model-small-fr-0.22 pour français
        """
        print("🤖 Initialisation de l'IA locale...")
        
        # Speech-to-Text (Vosk)
        try:
            self.vosk_model = Model(vosk_model_path)
            print(f"✅ Modèle Vosk chargé depuis: {vosk_model_path}")
        except Exception as e:
            print(f"❌ Erreur chargement Vosk: {e}")
            print("💡 Téléchargez un modèle sur https://alphacephei.com/vosk/models")
            self.vosk_model = None
        
        # Text-to-Speech (pyttsx3)
        try:
            self.tts_engine = pyttsx3.init()
            
            # Configuration TTS
            self.tts_engine.setProperty('rate', 150)  # Vitesse
            self.tts_engine.setProperty('volume', 0.9)  # Volume
            
            # Essayer de définir une voix française si disponible
            voices = self.tts_engine.getProperty('voices')
            for voice in voices:
                if 'french' in voice.name.lower() or 'fr' in voice.id.lower():
                    self.tts_engine.setProperty('voice', voice.id)
                    break
            
            print("✅ Moteur TTS initialisé")
        except Exception as e:
            print(f"❌ Erreur initialisation TTS: {e}")
            self.tts_engine = None
        
        # Base de connaissances simple pour l'assistant
        self.responses = {
            "bonjour": "Bonjour ! Comment puis-je vous aider ?",
            "salut": "Salut ! Je suis là pour discuter !",
            "comment ça va": "Je vais bien, merci ! Et vous ?",
            "au revoir": "Au revoir ! À bientôt !",
            "merci": "De rien, avec plaisir !",
            "aide": "Je peux transcrire vos messages vocaux et répondre à vos questions !",
            "qui es-tu": "Je suis un assistant IA local intégré au chat vocal !",
            "heure": None,  # Sera géré dynamiquement
            "date": None,   # Sera géré dynamiquement
        }
    
    def speech_to_text_from_wav(self, audio_data):
        """
        Convertir audio WAV en texte avec Vosk
        
        Args:
            audio_data: bytes - données audio au format WAV
            
        Returns:
            str: Texte transcrit ou None si erreur
        """
        if not self.vosk_model:
            print("❌ Modèle Vosk non chargé")
            return None
        
        try:
            # Lire le WAV depuis les bytes
            audio_buffer = io.BytesIO(audio_data)
            with wave.open(audio_buffer, 'rb') as wf:
                # Vérifier le format
                if wf.getnchannels() != 1:
                    print("⚠️  Audio doit être mono")
                    return None
                
                # Créer le recognizer
                recognizer = KaldiRecognizer(self.vosk_model, wf.getframerate())
                recognizer.SetWords(True)
                
                # Traiter l'audio
                text_parts = []
                while True:
                    data = wf.readframes(4000)
                    if len(data) == 0:
                        break
                    
                    if recognizer.AcceptWaveform(data):
                        result = json.loads(recognizer.Result())
                        if 'text' in result and result['text']:
                            text_parts.append(result['text'])
                
                # Récupérer le dernier morceau
                final_result = json.loads(recognizer.FinalResult())
                if 'text' in final_result and final_result['text']:
                    text_parts.append(final_result['text'])
                
                # Combiner tous les morceaux
                full_text = ' '.join(text_parts).strip()
                
                if full_text:
                    print(f"📝 Transcription: \"{full_text}\"")
                    return full_text
                else:
                    print("⚠️  Aucun texte détecté")
                    return None
                    
        except Exception as e:
            print(f"❌ Erreur transcription: {e}")
            return None
    
    def speech_to_text_live(self, duration=5):
        """
        Enregistrer et transcrire en direct depuis le micro
        
        Args:
            duration: Durée d'enregistrement en secondes
            
        Returns:
            str: Texte transcrit
        """
        if not self.vosk_model:
            print("❌ Modèle Vosk non chargé")
            return None
        
        try:
            print(f"🎤 Enregistrement en cours ({duration}s)...")
            
            audio = pyaudio.PyAudio()
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=8000
            )
            
            recognizer = KaldiRecognizer(self.vosk_model, 16000)
            recognizer.SetWords(True)
            
            text_parts = []
            frames_count = int(16000 / 8000 * duration)
            
            for _ in range(frames_count):
                data = stream.read(8000, exception_on_overflow=False)
                
                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    if 'text' in result and result['text']:
                        text_parts.append(result['text'])
            
            # Résultat final
            final_result = json.loads(recognizer.FinalResult())
            if 'text' in final_result and final_result['text']:
                text_parts.append(final_result['text'])
            
            stream.stop_stream()
            stream.close()
            audio.terminate()
            
            full_text = ' '.join(text_parts).strip()
            
            if full_text:
                print(f"📝 Transcription: \"{full_text}\"")
                return full_text
            else:
                print("⚠️  Aucun texte détecté")
                return None
                
        except Exception as e:
            print(f"❌ Erreur enregistrement live: {e}")
            return None
    
    def text_to_speech(self, text, save_to_file=None):
        """
        Convertir du texte en parole
        
        Args:
            text: Texte à synthétiser
            save_to_file: Optionnel - Chemin pour sauvegarder l'audio
            
        Returns:
            bool: True si succès
        """
        if not self.tts_engine:
            print("❌ Moteur TTS non initialisé")
            return False
        
        try:
            print(f"🗣️  Synthèse vocale: \"{text}\"")
            
            if save_to_file:
                self.tts_engine.save_to_file(text, save_to_file)
                self.tts_engine.runAndWait()
                print(f"💾 Audio sauvegardé: {save_to_file}")
            else:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur TTS: {e}")
            return False
    
    def get_ai_response(self, user_input):
        """
        Générer une réponse IA basique
        
        Args:
            user_input: Message de l'utilisateur
            
        Returns:
            str: Réponse de l'IA ou None
        """
        if not user_input:
            return None
        
        user_input_lower = user_input.lower().strip()
        
        # Réponses dynamiques
        if "heure" in user_input_lower:
            from datetime import datetime
            return f"Il est {datetime.now().strftime('%H:%M')}"
        
        if "date" in user_input_lower:
            from datetime import datetime
            return f"Nous sommes le {datetime.now().strftime('%d/%m/%Y')}"
        
        # Réponses prédéfinies
        for keyword, response in self.responses.items():
            if keyword in user_input_lower:
                return response
        
        # Réponse par défaut
        if len(user_input.split()) > 3:
            return "Intéressant ! Pouvez-vous m'en dire plus ?"
        
        return None
    
    def process_audio_message(self, audio_data, auto_respond=False):
        """
        Pipeline complet: Audio -> Texte -> (Optionnel) Réponse
        
        Args:
            audio_data: bytes - Audio WAV
            auto_respond: bool - Générer une réponse automatique
            
        Returns:
            dict: {'transcription': str, 'response': str, 'response_audio': bytes}
        """
        result = {
            'transcription': None,
            'response': None,
            'response_audio': None
        }
        
        # 1. Speech-to-Text
        transcription = self.speech_to_text_from_wav(audio_data)
        result['transcription'] = transcription
        
        if not transcription:
            return result
        
        # 2. Générer réponse si demandé
        if auto_respond:
            response = self.get_ai_response(transcription)
            result['response'] = response
            
            # 3. Text-to-Speech de la réponse
            if response:
                # Créer un fichier temporaire pour la réponse
                import tempfile
                temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                temp_path = temp_file.name
                temp_file.close()
                
                if self.text_to_speech(response, save_to_file=temp_path):
                    # Lire le fichier audio généré
                    try:
                        with open(temp_path, 'rb') as f:
                            result['response_audio'] = f.read()
                        
                        import os
                        os.remove(temp_path)
                    except Exception as e:
                        print(f"❌ Erreur lecture audio réponse: {e}")
        
        return result


# Fonction utilitaire pour tester le module
def test_ai():
    """Tester les fonctionnalités de l'IA"""
    print("🧪 TEST DU MODULE IA LOCALE")
    print("=" * 60)
    
    # Initialiser l'IA
    ai = LocalAI(vosk_model_path="model")
    
    # Test TTS
    print("\n1️⃣  Test Text-to-Speech:")
    ai.text_to_speech("Bonjour ! Je suis l'intelligence artificielle du chat vocal.")
    
    # Test réponses
    print("\n2️⃣  Test génération de réponses:")
    test_inputs = [
        "Bonjour",
        "Quelle heure est-il ?",
        "Qui es-tu ?",
        "Au revoir"
    ]
    
    for user_input in test_inputs:
        response = ai.get_ai_response(user_input)
        print(f"  👤 User: {user_input}")
        print(f"  🤖 AI: {response}\n")
    
    # Test Speech-to-Text live (optionnel)
    print("\n3️⃣  Test Speech-to-Text (Appuyez sur Entrée pour enregistrer 5s)")
    input()
    ai.speech_to_text_live(duration=5)
    
    print("\n✅ Tests terminés!")


if __name__ == "__main__":
    test_ai()