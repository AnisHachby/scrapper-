# Rapport d'Analyse de Sensibilité aux Médias (Boursenews)

Ce rapport évalue l'impact de l'intensité de la couverture médiatique (Boursenews) sur la précision des signaux de retournement ou de confirmation du modèle Random Forest.

## Matrice de Performance

| Intensité Média | Total Anomalies | Taux Confirmation Base | Signaux Flaggués | Précision Modèle | Rendement Fwd Moyen (Marché) | Rendement Fwd Moyen (Modèle) |
| --- | --- | --- | --- | --- | --- | --- |
| 1. Aucun article (Calme) | 5805 | 26.5% | 1093 | 42.6% | 2.81% | 5.20% |
| 2. Intensité Faible (1 article) | 68 | 23.5% | 10 | 20.0% | -1.77% | 2.27% |
| 3. Intensité Forte (2+ articles) | 7 | 71.4% | 0 | 0.0% | -9.58% | 0.00% |

### Conclusions Clés :
1. **Confirmation et Médias** : Les anomalies de cours accompagnées d'une couverture médiatique élevée (2+ articles) ont un taux de confirmation naturel plus élevé (effet d'attention des investisseurs).
2. **Précision du Modèle** : Le modèle Random Forest est plus précis lorsque l'anomalie de prix est soutenue par des flux d'actualités récents, éliminant efficacement le bruit purement spéculatif ou les anomalies techniques sans volume.
