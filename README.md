# hamed

`hamed` («**RAMEDCollect**») est un outil d'assistance à la gestion des collectes de données mobile (ODK) pour l'identification des indigents du RAMED.

Il est déployé au niveau des SLDSES (Service Local du Développement Social et de l'Économie Solidaire) sur une machine dédiée (Ubuntu Desktop) qui sert à la fois de serveur et de client.

Il est essentiellement une interface Web interagissant avec une instance ONA locale via son API.

## Fonctionnement

* Création d'une `Collect` représentant une mission d'enquête sociale dans une commune (recensement basé sur une liste de potentiels indigents – ~ 100).
 * Génération auto d'un XLSForm basé sur celui d'enquête sociale générique (changement `ID` et `title`).
 * Création auto du `XForm` sur ONA.
 * Ajout du rôle `dataentry-only` pour le compte `agent` sur le formulaire.
* L'utilisateur peut ensuite:
 * Configurer ses tablettes (ODK Collect) pour le formulaire créé.
 * Former les enquêteurs et déclencher la mission.
 * Une fois la collecte terminée, tous les formulaires sont soumis à ONA.
* Cloture d'une `Collect`, mettant un terme à la première étape du processus:
 * Désactivation du formulaire sur ONA.
 * Téléchargement des données JSON.
 * Génération d'un CSV contenant les nom/age/sexe des cibles.
 * Génération d'un XLSForm pour *scanner* les certificats signés
 * Création du formulaire de *scan* sur ONA.
 * Ajout du CSV sur le formulaire ONA.
 * Ajout du rôle `dataentry-only` pour le compte `agent` sur le formulaire.
* L'utilisateur peut ensuite :
 * Consulter un aperçu des données des cibles 
 * Copier les fichiers PDF (formulaire d'enquête sociale *condensé* généré, certificat de résidence non signé, certificat d'indigence non signé) sur une clé USB.
 * Imprimer tous les documents (3 par cible) via la fonction *Impression USB* de l'imprimante.
 * Étudier les enquêtes sociales et soumettre tous les documents à la mairie de la commune pour signature.
 * Une fois les documents signés reçus : 
   * Configurer une tablette avec le formulaire de *scan*.
   * *Scanner* les documents avec la tablette (le formulaire scan un code bar présent sur chaque document puis demande la prise de photo des deux certificats signés).
* Finalisation d'une `Collect`:
 * Désactivation du formulaire *scan* sur ONA.
 * Téléchargement des donnés ONA.
 * Génération des différents exports (exports XLSX ONA et JSON)
 * Export des médias (photos de toutes les pièces d'identité)
* L'utilisateur peut alors :
 * Envoyer l'export XLSX à ses partenaires (Direction Régionale et Nationale, ANAM) par e-mail.
 * Tenter la télétransmission des données à l'ANAM.
 * Exporter toutes les données sur clé USB via l'outil fourni.
 * Faire remonter la clé USB et les copies dure via le circuit physique.

 
## Équipements
 Tous les équipements sont à l'usage du SLDSES et non dédié à l'identification des indigents du RAMED.
 
* Un onduleur
* Un routeur WiFi `Linksys E900`
 * `dd-wrt.v24-21061_NEWD-2_K2.6_mega-nv64k`
 * WAN DHCP, LAN DHCPD, DNSMasq
* Un ordinateur de bureau `HP EliteDesk 800G2SFF`
 * `Ubuntu 16.04.2 LTS Desktop`
 * `ramed-server.cercle`, `ona.cercle`
 * Users: `sldses` (Unity), `ona` (ONA, hamed)
* Un NAS `WD MyCloud 2TB`
 * `nas.cercle`
 * Dossier `Public` avec drivers imprimante et documentations.
 * Dossier `SLDSES` pour archives/backups (aucun backup automatique).
* Une imprimante `Canon iR1435iF`
 * `printer.cercle`
 * Impression USB (mode recto-verso)

## Mode avancé
Un *mode avancé* permet d'effectuer des opérations destructrices de données:

* Changement de l'état de la `Collect` (`STARTED`, `ENDED`, `FINALIZED`)
* Suppression des donnés du formulaire de *scan* (hamed + ONA)
* Suppression de toutes les données (scan et enquête sociale, hamed + ONA)
* Suppression individuelle de cible (hamed + ONA)

Ces opérations ne font pas partie de la routine d'utilisation et sont donc invisibles et inaccessibles par défaut.
Elles peuvent être activées via:

* L'utilisateur utilise le lien *Activer le mode avancé* dans la documentation.
* Il communique le numéro affiché au support (BDD DNDS) qui a accès à ce document et lui communique le numéro de déverrouillage.
* Le mode avancé est alors activé pour la journée.

### ActivationCode
Le `RequestCode` est une chaine composée du `cercle_id` et de la date (`33170301` pour Douentza –33– le 1 mars 2017) chiffrée par décalage (Caesar Cipher) avec un pas de `x` où `x` vaut l'heure de la demande.

L'alphabet est a-z suivi de 0-9.

La librairie [`hamed-advanced`](https://github.com/yeleman/hamed-advanced) permet le chiffrement/déchiffrement et un binaire Windows est fourni à la DNDS.

Exemple:

* `RequestCode: RLLJPILJN` (Douentza, 15/3/2017 à 17h)
* `ActivationCode: IPMLL` (074 –day of year, 33 –Douentza)

 
## Déploiement

* Django settings:
 * `COLLECT_DOCUMENTS_FOLDER = "/home/shared/Collectes-RAMED"`: Chemin absolu pour l'export des fichiers (dossiers, médias, etc).
 * `WEBSOCKET_SERVER_PORT = 8888`: Port du serveur Websocket (lancé via le mgmt command `socket_server` servant à gérer l'export USB avec feedback de la progression.
 * `ALLOWED_HOSTS = ['ramed-server.cercle', 'ramed-server', 'localhost']`
 * `FOLDER_OPENER_SERVER = "http://localhost:8000"`: URL du *serveur* permettant d'ouvrir `nautilus` sur un chemin en particulier. Utilisé pour *Voir les fichiers à imprimer*. 
* Ajouter au démarrage de la session Unity `python3.6 /home/ona/hamed/extras/folder-opener.py`
* Django Model `Settings`: `ona-server`, `ona-username`, `ona-token`, `cercle-id` (doit être dans `locations.py`), `dataentry-username`, `upload-server`.


