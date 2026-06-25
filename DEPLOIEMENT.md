# Déploiement — GitHub + Streamlit Community Cloud

Le dépôt est **déjà initialisé et committé**. Il reste 3 étapes.

## 1. Créer le repo GitHub
1. https://github.com/new
2. Nom : `equity-derivatives-desk` · Public ou Private
3. **Ne coche rien** (pas de README/.gitignore/licence)
4. *Create repository*

## 2. Pousser (Terminal)
Remplace `TON_PSEUDO` :
```bash
cd ~/Desktop/equity-derivatives-desk
git remote add origin https://github.com/TON_PSEUDO/equity-derivatives-desk.git
git branch -M main
git push -u origin main
```
> Mot de passe demandé = un **token** GitHub (https://github.com/settings/tokens
> → classic → coche `repo`), pas ton mot de passe.

## 3. Déployer
1. https://share.streamlit.io → connexion GitHub
2. **Create app** → **Deploy a public app from GitHub**
3. Repository `TON_PSEUDO/equity-derivatives-desk` · Branch `main` · **Main file `app.py`**
4. *(Advanced)* Python **3.12**
5. **Deploy!** → ~2-3 min de build → URL publique `https://….streamlit.app`

## Mises à jour
```bash
git add -A && git commit -m "maj" && git push
```
Streamlit Cloud redéploie automatiquement à chaque push sur `main`.
