import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import Horse, Jockey, Trainer, RaceEntry, HistoricalPerformance, Race, Bet
import asyncio
from racing_api import RacingAPIClient

class BettingEngine:
    def __init__(self, db: Session):
        self.db = db
        self.api_client = RacingAPIClient()
        self.daily_budget = 100.0
        self.max_bet_per_race = 50.0
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        
    async def analyze_race(self, race: Race) -> List[Dict]:
        entries = self.db.query(RaceEntry).filter(RaceEntry.race_id == race.id).all()
        recommendations = []
        
        for entry in entries:
            features = await self._extract_features(entry, race)
            if features is not None:
                confidence, expected_value = self._calculate_betting_metrics(features, entry.current_odds)
                
                if expected_value > 1.15:  # Only bet if expected value > 15%
                    bet_amount = self._calculate_bet_size(confidence, expected_value)
                    recommendations.append({
                        'entry_id': entry.id,
                        'horse_name': entry.horse.name,
                        'post_position': entry.post_position,
                        'current_odds': entry.current_odds,
                        'confidence': confidence,
                        'expected_value': expected_value,
                        'bet_amount': bet_amount,
                        'bet_type': 'WIN'
                    })
        
        # Sort by expected value and limit bets
        recommendations.sort(key=lambda x: x['expected_value'], reverse=True)
        return self._optimize_bets(recommendations)
    
    async def _extract_features(self, entry: RaceEntry, race: Race) -> np.ndarray:
        features = []
        
        # Horse performance features
        horse_perfs = self.db.query(HistoricalPerformance).filter(
            HistoricalPerformance.horse_id == entry.horse_id
        ).order_by(HistoricalPerformance.race_date.desc()).limit(10).all()
        
        if len(horse_perfs) < 3:
            return None
            
        # Calculate horse statistics
        avg_finish = np.mean([p.finish_position for p in horse_perfs[:5]])
        win_rate = sum(1 for p in horse_perfs if p.finish_position == 1) / len(horse_perfs)
        avg_speed_fig = np.mean([p.speed_figure for p in horse_perfs[:5] if p.speed_figure])
        
        # Distance preference
        similar_distance_perfs = [p for p in horse_perfs if abs(p.distance - race.distance) < 0.25]
        dist_avg_finish = np.mean([p.finish_position for p in similar_distance_perfs]) if similar_distance_perfs else avg_finish
        
        # Surface preference
        same_surface_perfs = [p for p in horse_perfs if p.surface == race.surface]
        surf_avg_finish = np.mean([p.finish_position for p in same_surface_perfs]) if same_surface_perfs else avg_finish
        
        # Jockey statistics
        jockey_perfs = self.db.query(HistoricalPerformance).filter(
            HistoricalPerformance.jockey_id == entry.jockey_id
        ).order_by(HistoricalPerformance.race_date.desc()).limit(20).all()
        
        jockey_win_rate = sum(1 for p in jockey_perfs if p.finish_position == 1) / len(jockey_perfs) if jockey_perfs else 0.1
        
        # Trainer statistics
        trainer_perfs = self.db.query(HistoricalPerformance).filter(
            HistoricalPerformance.trainer_id == entry.trainer_id
        ).order_by(HistoricalPerformance.race_date.desc()).limit(20).all()
        
        trainer_win_rate = sum(1 for p in trainer_perfs if p.finish_position == 1) / len(trainer_perfs) if trainer_perfs else 0.1
        
        # Post position statistics
        post_position_factor = 1.0 - (abs(entry.post_position - 5) * 0.05)
        
        # Days since last race
        if horse_perfs:
            days_since_last = (race.race_date - horse_perfs[0].race_date).days
            freshness_factor = 1.0 if 14 <= days_since_last <= 45 else 0.8
        else:
            freshness_factor = 0.5
            
        features = [
            avg_finish,
            win_rate,
            avg_speed_fig if avg_speed_fig else 75,
            dist_avg_finish,
            surf_avg_finish,
            jockey_win_rate,
            trainer_win_rate,
            post_position_factor,
            freshness_factor,
            entry.morning_line_odds,
            entry.weight
        ]
        
        return np.array(features)
    
    def _calculate_betting_metrics(self, features: np.ndarray, current_odds: float) -> Tuple[float, float]:
        # Normalize features
        features_2d = features.reshape(1, -1)
        
        # Simple scoring based on key factors
        avg_finish = features[0]
        win_rate = features[1]
        speed_fig = features[2]
        jockey_win_rate = features[5]
        trainer_win_rate = features[6]
        
        # Calculate win probability
        base_prob = (1 / avg_finish) * 0.3
        base_prob += win_rate * 0.25
        base_prob += (speed_fig / 100) * 0.2
        base_prob += jockey_win_rate * 0.15
        base_prob += trainer_win_rate * 0.1
        
        # Adjust for extreme values
        win_probability = min(max(base_prob, 0.05), 0.6)
        
        # Calculate implied probability from odds
        implied_probability = 1 / (current_odds + 1)
        
        # Calculate expected value
        expected_value = (win_probability * current_odds) / implied_probability
        
        # Calculate confidence (how sure we are about our prediction)
        confidence = min(win_probability / implied_probability, 2.0)
        
        return confidence, expected_value
    
    def _calculate_bet_size(self, confidence: float, expected_value: float) -> float:
        # Kelly Criterion with conservative fraction
        kelly_fraction = 0.25  # Use 25% of Kelly for safety
        
        # Calculate optimal bet size
        edge = expected_value - 1.0
        if edge <= 0:
            return 0
            
        bet_fraction = kelly_fraction * edge * confidence
        bet_amount = self.daily_budget * bet_fraction
        
        # Apply constraints
        bet_amount = min(bet_amount, self.max_bet_per_race)
        bet_amount = max(bet_amount, 0)
        
        # Round to nearest dollar
        return round(bet_amount, 0)
    
    def _optimize_bets(self, recommendations: List[Dict]) -> List[Dict]:
        # Filter out small bets
        viable_bets = [r for r in recommendations if r['bet_amount'] >= 5]
        
        # Ensure we don't exceed daily budget
        total_bet = sum(r['bet_amount'] for r in viable_bets)
        
        if total_bet > self.daily_budget:
            # Scale down proportionally
            scale_factor = self.daily_budget / total_bet
            for bet in viable_bets:
                bet['bet_amount'] = round(bet['bet_amount'] * scale_factor, 0)
        
        return viable_bets
    
    def calculate_expected_daily_roi(self, all_recommendations: List[List[Dict]]) -> float:
        total_wagered = sum(sum(r['bet_amount'] for r in race_recs) for race_recs in all_recommendations)
        
        if total_wagered == 0:
            return 0
            
        expected_return = sum(
            sum(r['bet_amount'] * r['expected_value'] for r in race_recs) 
            for race_recs in all_recommendations
        )
        
        return ((expected_return - total_wagered) / total_wagered) * 100