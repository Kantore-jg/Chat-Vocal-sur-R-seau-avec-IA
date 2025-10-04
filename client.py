import socket
import threading
import struct
import pyaudio
import wave
import io
import time
from datetime import datetime

class VocalChatClient:
    def __init__(self, host='127.0.0.1', port=5555):
        self.host = host
        self.port = port
        self.socket = None
        self.username = None
        self.running = False
        self.connected_users = []
        
        # Configuration audio
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.RECORD_SECONDS = 3
        
        self.audio = pyaudio.PyAudio()
        
    def connect(self, username):
        """Se connecter au serveur"""
        try:
            self.username = username
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            
            # Envoyer le username
            username_bytes = username.encode('utf-8')
            self.socket.send(struct.pack('!I', len(username_bytes)))
            self.socket.send(username_bytes)
            
            self.running = True
            print(f"✅ Connecté au serveur comme '{username}'")
            print("=" * 60)
            
            # Démarrer le thread de réception
            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur de connexion: {e}")
            return False
    
    def receive_messages(self):
        """Recevoir et traiter les messages du serveur"""
        while self.running:
            try:
                # Recevoir le type de message
                msg_type_data = self.socket.recv(1)
                if not msg_type_data:
                    break
                
                msg_type = struct.unpack('B', msg_type_data)[0]
                
                if msg_type == 1:  # Audio
                    self.receive_audio()
                elif msg_type == 2:  # Texte
                    self.receive_text()
                elif msg_type == 3:  # Liste utilisateurs
                    self.receive_user_list()
                    
            except Exception as e:
                if self.running:
                    print(f"❌ Erreur réception: {e}")
                break
        
        self.disconnect()
    
    def receive_audio(self):
        """Recevoir et jouer un message audio"""
        try:
            # Recevoir le username
            username_length = struct.unpack('!I', self.socket.recv(4))[0]
            username = self.socket.recv(username_length).decode('utf-8')
            
            # Recevoir la taille audio
            audio_size = struct.unpack('!I', self.socket.recv(4))[0]
            
            # Recevoir les données audio
            audio_data = b''
            remaining = audio_size
            while remaining > 0:
                chunk = self.socket.recv(min(remaining, 4096))
                if not chunk:
                    break
                audio_data += chunk
                remaining -= len(chunk)
            
            if len(audio_data) == audio_size:
                print(f"🎵 Audio reçu de {username}")
                self.play_audio(audio_data)
            
        except Exception as e:
            print(f"❌ Erreur réception audio: {e}")
    
    def receive_text(self):
        """Recevoir un message texte"""
        try:
            # Recevoir le username
            username_length = struct.unpack('!I', self.socket.recv(4))[0]
            username = self.socket.recv(username_length).decode('utf-8')
            
            # Recevoir le message
            msg_length = struct.unpack('!I', self.socket.recv(4))[0]
            message = self.socket.recv(msg_length).decode('utf-8')
            
            print(f"💬 {username}: {message}")
            
        except Exception as e:
            print(f"❌ Erreur réception texte: {e}")
    
    def receive_user_list(self):
        """Recevoir la liste des utilisateurs"""
        try:
            list_length = struct.unpack('!I', self.socket.recv(4))[0]
            users_str = self.socket.recv(list_length).decode('utf-8')
            
            if users_str:
                self.connected_users = users_str.split(',')
                print(f"👥 Utilisateurs connectés: {users_str}")
            else:
                self.connected_users = []
                print("👥 Aucun autre utilisateur connecté")
                
        except Exception as e:
            print(f"❌ Erreur réception liste: {e}")
    
    def record_audio(self):
        """Enregistrer de l'audio depuis le micro"""
        print(f"🎤 Enregistrement pendant {self.RECORD_SECONDS} secondes...")
        
        stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )
        
        frames = []
        for i in range(0, int(self.RATE / self.CHUNK * self.RECORD_SECONDS)):
            data = stream.read(self.CHUNK)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        
        # Convertir en bytes WAV
        audio_buffer = io.BytesIO()
        with wave.open(audio_buffer, 'wb') as wf:
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(self.audio.get_sample_size(self.FORMAT))
            wf.setframerate(self.RATE)
            wf.writeframes(b''.join(frames))
        
        audio_data = audio_buffer.getvalue()
        print(f"✅ Enregistré ({len(audio_data)} bytes)")
        
        return audio_data
    
    def play_audio(self, audio_data):
        """Jouer des données audio"""
        try:
            # Lire le WAV depuis les bytes
            audio_buffer = io.BytesIO(audio_data)
            with wave.open(audio_buffer, 'rb') as wf:
                stream = self.audio.open(
                    format=self.audio.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True
                )
                
                data = wf.readframes(self.CHUNK)
                while data:
                    stream.write(data)
                    data = wf.readframes(self.CHUNK)
                
                stream.stop_stream()
                stream.close()
            
            print("🔊 Lecture terminée")
            
        except Exception as e:
            print(f"❌ Erreur lecture audio: {e}")
    
    def send_audio(self):
        """Enregistrer et envoyer un message audio"""
        try:
            audio_data = self.record_audio()
            
            # Envoyer au serveur
            self.socket.send(struct.pack('B', 1))  # Type: audio
            self.socket.send(struct.pack('!I', len(audio_data)))
            self.socket.send(audio_data)
            
            print("📤 Audio envoyé")
            
        except Exception as e:
            print(f"❌ Erreur envoi audio: {e}")
    
    def send_text(self, message):
        """Envoyer un message texte"""
        try:
            message_bytes = message.encode('utf-8')
            
            self.socket.send(struct.pack('B', 2))  # Type: texte
            self.socket.send(struct.pack('!I', len(message_bytes)))
            self.socket.send(message_bytes)
            
            print(f"📤 Message envoyé: {message}")
            
        except Exception as e:
            print(f"❌ Erreur envoi texte: {e}")
    
    def disconnect(self):
        """Se déconnecter proprement"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        print("👋 Déconnecté du serveur")
    
    def run_cli(self):
        """Interface en ligne de commande"""
        print("\n" + "=" * 60)
        print("🎙️  CHAT VOCAL - Commandes disponibles:")
        print("=" * 60)
        print("  v ou voice  - Enregistrer et envoyer un message vocal")
        print("  t ou text   - Envoyer un message texte")
        print("  u ou users  - Voir les utilisateurs connectés")
        print("  q ou quit   - Quitter")
        print("=" * 60 + "\n")
        
        while self.running:
            try:
                cmd = input("Commande> ").strip().lower()
                
                if cmd in ['v', 'voice']:
                    self.send_audio()
                    
                elif cmd in ['t', 'text']:
                    message = input("Message> ").strip()
                    if message:
                        self.send_text(message)
                    
                elif cmd in ['u', 'users']:
                    if self.connected_users:
                        print(f"👥 Utilisateurs: {', '.join(self.connected_users)}")
                    else:
                        print("👥 Aucun autre utilisateur")
                    
                elif cmd in ['q', 'quit']:
                    print("👋 Au revoir!")
                    break
                    
                else:
                    print("⚠️  Commande inconnue. Tapez 'h' pour l'aide")
                    
            except KeyboardInterrupt:
                print("\n⚠️  Interruption détectée")
                break
            except Exception as e:
                print(f"❌ Erreur: {e}")
        
        self.disconnect()
    
    def cleanup(self):
        """Nettoyer les ressources"""
        self.disconnect()
        self.audio.terminate()


if __name__ == "__main__":
    print("🎙️  CLIENT CHAT VOCAL")
    print("=" * 60)
    
    # Configuration
    server_host = input("Adresse du serveur [127.0.0.1]: ").strip() or "127.0.0.1"
    server_port = input("Port [5555]: ").strip() or "5555"
    username = input("Votre nom d'utilisateur: ").strip()
    
    if not username:
        print("❌ Nom d'utilisateur requis!")
        exit(1)
    
    # Créer et connecter le client
    client = VocalChatClient(host=server_host, port=int(server_port))
    
    try:
        if client.connect(username):
            time.sleep(0.5)  # Laisser le temps de recevoir la liste
            client.run_cli()
        else:
            print("❌ Impossible de se connecter")
    except KeyboardInterrupt:
        print("\n⚠️  Interruption")
    finally:
        client.cleanup()