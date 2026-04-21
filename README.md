pour lancer le Quiz:
python3 -m http.server 5000

Il est placé en service system sous le nom quiz.service
restart:
‘‘‘
sudo systemctl restart quiz.service
‘‘‘
Pour créer le service:
‘‘‘
sudo nano /etc/systemd/system/quiz.service
‘‘‘
with the content:
‘‘‘
[Unit]
Description=Serveur de Quiz Le Secret du Gladiateur
After=network.target

[Service]
# Le dossier où se trouvent index.html et server.py
WorkingDirectory=/home/pi/bookTest/leSecretDuGladiateur
# La commande pour lancer le serveur
ExecStart=/usr/bin/python3 /home/pi/bookTest/leSecretDuGladiateur/server.py
# Redémarrer automatiquement en cas de crash
Restart=always
# Utilisateur qui lance le service
User=pi
# Pour voir les logs en temps réel sans tampon (buffering)
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
‘‘‘

Load the config
sudo systemctl daemon-reload
sudo systemctl enable quiz.service