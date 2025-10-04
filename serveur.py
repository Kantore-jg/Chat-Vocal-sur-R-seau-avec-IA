import socket
import threading
import struct
import time
from datetime import datetime

class VocalChatServer:
    def __init__(self, host='0.0.0.0', port=5555):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = {}  # {socket: {'username': str, 'address': tuple}}
        self.clients_lock = threading.Lock()
        self.running = False
        
    def start(self):
        """Démarrer le serveur"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            print(f"🎙️  Serveur de chat vocal démarré sur {self.host}:{self.port}")
            print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("-" * 60)
            
            # Thread pour accepter les connexions
            accept_thread = threading.Thread(target=self.accept_connections)
            accept_thread.daemon = True
            accept_thread.start()
            
            # Garder le serveur actif
            while self.running:
                time.sleep(1)
                
        except Exception as e:
            print(f"❌ Erreur serveur: {e}")
        finally:
            self.stop()
    
    def accept_connections(self):
        """Accepter les nouvelles connexions clients"""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                print(f"🔌 Nouvelle connexion de {address}")
                
                # Thread pour gérer ce client
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()
                
            except Exception as e:
                if self.running:
                    print(f"❌ Erreur acceptation connexion: {e}")
    
    def handle_client(self, client_socket, address):
        """Gérer un client spécifique"""
        username = None
        
        try:
            # Recevoir le nom d'utilisateur
            username_length = struct.unpack('!I', client_socket.recv(4))[0]
            username = client_socket.recv(username_length).decode('utf-8')
            
            # Ajouter le client à la liste
            with self.clients_lock:
                self.clients[client_socket] = {
                    'username': username,
                    'address': address
                }
            
            print(f"✅ {username} connecté depuis {address}")
            self.broadcast_user_list()
            
            # Boucle de réception des messages
            while self.running:
                # Recevoir le type de message (1 byte)
                msg_type = client_socket.recv(1)
                if not msg_type:
                    break
                
                msg_type = struct.unpack('B', msg_type)[0]
                
                if msg_type == 1:  # Message audio
                    self.handle_audio_message(client_socket, username)
                elif msg_type == 2:  # Message texte
                    self.handle_text_message(client_socket, username)
                
        except Exception as e:
            print(f"⚠️  Erreur avec {username or address}: {e}")
        finally:
            # Nettoyer la déconnexion
            with self.clients_lock:
                if client_socket in self.clients:
                    user_info = self.clients[client_socket]
                    del self.clients[client_socket]
                    print(f"👋 {user_info['username']} déconnecté")
            
            try:
                client_socket.close()
            except:
                pass
            
            self.broadcast_user_list()
    
    def handle_audio_message(self, sender_socket, username):
        """Gérer la réception et broadcast d'un message audio"""
        try:
            # Recevoir la taille du chunk audio
            audio_size = struct.unpack('!I', sender_socket.recv(4))[0]
            
            # Recevoir les données audio
            audio_data = b''
            remaining = audio_size
            while remaining > 0:
                chunk = sender_socket.recv(min(remaining, 4096))
                if not chunk:
                    break
                audio_data += chunk
                remaining -= len(chunk)
            
            if len(audio_data) == audio_size:
                print(f"🎵 Audio reçu de {username} ({audio_size} bytes)")
                
                # Broadcaster aux autres clients
                self.broadcast_audio(sender_socket, username, audio_data)
            
        except Exception as e:
            print(f"❌ Erreur traitement audio: {e}")
    
    def handle_text_message(self, sender_socket, username):
        """Gérer un message texte"""
        try:
            # Recevoir la taille du message
            msg_size = struct.unpack('!I', sender_socket.recv(4))[0]
            
            # Recevoir le message
            message = sender_socket.recv(msg_size).decode('utf-8')
            print(f"💬 {username}: {message}")
            
            # Broadcaster le message texte
            self.broadcast_text(sender_socket, username, message)
            
        except Exception as e:
            print(f"❌ Erreur traitement message texte: {e}")
    
    def broadcast_audio(self, sender_socket, username, audio_data):
        """Envoyer l'audio à tous les clients sauf l'émetteur"""
        username_bytes = username.encode('utf-8')
        
        with self.clients_lock:
            for client_socket in list(self.clients.keys()):
                if client_socket != sender_socket:
                    try:
                        # Type: audio (1)
                        client_socket.send(struct.pack('B', 1))
                        # Taille du username
                        client_socket.send(struct.pack('!I', len(username_bytes)))
                        # Username
                        client_socket.send(username_bytes)
                        # Taille audio
                        client_socket.send(struct.pack('!I', len(audio_data)))
                        # Données audio
                        client_socket.send(audio_data)
                        
                    except Exception as e:
                        print(f"❌ Erreur envoi audio: {e}")
    
    def broadcast_text(self, sender_socket, username, message):
        """Envoyer un message texte à tous les clients"""
        username_bytes = username.encode('utf-8')
        message_bytes = message.encode('utf-8')
        
        with self.clients_lock:
            for client_socket in list(self.clients.keys()):
                if client_socket != sender_socket:
                    try:
                        # Type: texte (2)
                        client_socket.send(struct.pack('B', 2))
                        # Taille username
                        client_socket.send(struct.pack('!I', len(username_bytes)))
                        # Username
                        client_socket.send(username_bytes)
                        # Taille message
                        client_socket.send(struct.pack('!I', len(message_bytes)))
                        # Message
                        client_socket.send(message_bytes)
                        
                    except Exception as e:
                        print(f"❌ Erreur envoi texte: {e}")
    
    def broadcast_user_list(self):
        """Envoyer la liste des utilisateurs connectés à tous"""
        with self.clients_lock:
            usernames = [info['username'] for info in self.clients.values()]
            users_str = ','.join(usernames)
            users_bytes = users_str.encode('utf-8')
            
            print(f"👥 Utilisateurs connectés: {users_str if users_str else 'Aucun'}")
            
            for client_socket in list(self.clients.keys()):
                try:
                    # Type: liste utilisateurs (3)
                    client_socket.send(struct.pack('B', 3))
                    # Taille
                    client_socket.send(struct.pack('!I', len(users_bytes)))
                    # Liste
                    client_socket.send(users_bytes)
                except Exception as e:
                    print(f"❌ Erreur envoi liste: {e}")
    
    def stop(self):
        """Arrêter le serveur proprement"""
        print("\n🛑 Arrêt du serveur...")
        self.running = False
        
        # Fermer toutes les connexions clients
        with self.clients_lock:
            for client_socket in list(self.clients.keys()):
                try:
                    client_socket.close()
                except:
                    pass
            self.clients.clear()
        
        # Fermer le socket serveur
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        print("✅ Serveur arrêté")


if __name__ == "__main__":
    server = VocalChatServer(host='0.0.0.0', port=5555)
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n⚠️  Interruption détectée (Ctrl+C)")
        server.stop()