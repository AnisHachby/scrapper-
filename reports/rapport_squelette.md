# Modèle de Détection Signal vs Bruit à la BVC

## Résumé
*À rédiger à la fin*

## 1. Introduction
- Contexte du stage chez Capital Trust Securities
- La problématique d'un desk actions dans un marché étroit
- Objectif : distinguer les mouvements réels du bruit de liquidité

## 2. Revue de littérature et microstructure
- Amihud (2002) et l'illiquidité
- Asymétrie d'information (Kyle, Glosten & Milgrom)
- Spécificités de la Bourse de Casablanca (fixing, blocs, retard d'information)

## 3. Données et Méthodologie
- Les Bulletins de la Cote comme source officielle et vérifiable
- Scraping et parsing des PDF (44 894 lignes de prix, 500 270 transactions)
- Résolution des anomalies de données (valeurs suspendues, OPA)
- Scraping des communiqués AMMC

## 4. Ingénierie des features
- Rendement et momentum multi-horizons
- Mesures de liquidité (Amihud, Volume Relatif)
- Part du marché de blocs
- Fenêtre anti look-ahead pour les catalyseurs

## 5. Le Modèle : Random Forest
- Choix de l'algorithme vs alternatives (Deep Learning, Règles simples)
- La cible de confirmation (3% de mouvement, confirmé sur 5 jours à 2%)
- Validation temporelle (Walk-Forward TimeSeriesSplit)

## 6. Résultats
- Taux de base et courbe de Précision/Rappel
- Performance aux différents seuils
- Importance des variables (le momentum domine, pourquoi ?)
- La limite des 70% comme mesure structurelle du marché

## 7. Robustesse et Limites
- Stabilité selon les définitions de label
- Dérive temporelle (baisse de précision en 2026)
- Fuite temporelle et comparaison K-fold

## 8. Études de Cas
(Voir annexe ou document séparé pour STROC, IB MAROC, BALIMA)

## Conclusion
- Un filtre défensif "ne pas courir après" efficace
- Pistes d'amélioration (carnet d'ordres en temps réel, NLP sur la presse)
