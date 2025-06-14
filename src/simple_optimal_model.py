"""
Simple Optimal Betting Model
Uses only available data: historical performance, win rates, and current odds
Provides Win/Place/Show recommendations with conservative Kelly Criterion
"""

import numpy as np
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from database import Race, RaceEntry, HistoricalPerformance, Horse, Jockey, Trainer
from datetime import date, timedelta


class SimpleOptimalBettingModel:
    def __init__(self, db: Session, bankroll: float = 1000.0):
        self.db = db
        self.bankroll = bankroll
        self.kelly_fraction = 0.25  # Conservative 25% Kelly
        self.max_bet_pct = 0.05    # Max 5% of bankroll per bet
        self.max_race_pct = 0.10   # Max 10% of bankroll per race
        self.min_edge = 0.15       # Minimum 15% edge required
        
    def analyze_race(self, race: Race) -> List[Dict]:
        """Analyze a race and return betting recommendations"""
        entries = self.db.query(RaceEntry).filter(
            RaceEntry.race_id == race.id
        ).all()
        
        if not entries:
            return []
            
        # Calculate probabilities for each entry
        entry_probabilities = []
        for entry in entries:
            prob = self._calculate_entry_probability(entry, race)
            if prob is not None:
                entry_probabilities.append({
                    'entry': entry,
                    'win_prob': prob,
                    'place_prob': prob * 1.8,  # Rough place probability
                    'show_prob': prob * 2.5    # Rough show probability
                })
                
        if not entry_probabilities:
            return []
            
        # Normalize probabilities
        total_prob = sum(ep['win_prob'] for ep in entry_probabilities)
        if total_prob > 0:
            for ep in entry_probabilities:
                ep['win_prob'] /= total_prob
                ep['place_prob'] = min(ep['place_prob'] / total_prob, 0.95)
                ep['show_prob'] = min(ep['show_prob'] / total_prob, 0.95)
                
        # Find betting opportunities
        recommendations = []
        for ep in entry_probabilities:
            entry = ep['entry']
            
            # Check each bet type
            for bet_type, prob_key in [('WIN', 'win_prob'), ('PLACE', 'place_prob'), ('SHOW', 'show_prob')]:
                prob = ep[prob_key]
                
                # Get appropriate odds
                if bet_type == 'WIN':
                    odds = entry.current_odds
                elif bet_type == 'PLACE':
                    # Estimate place odds as ~40% of win odds
                    odds = entry.current_odds * 0.4
                else:  # SHOW
                    # Estimate show odds as ~25% of win odds
                    odds = entry.current_odds * 0.25
                    
                # Calculate edge
                implied_prob = 1 / (odds + 1)
                edge = prob - implied_prob
                
                if edge >= self.min_edge:
                    # Calculate bet size using Kelly Criterion
                    kelly_bet = (prob * odds - (1 - prob)) / odds
                    bet_fraction = self.kelly_fraction * kelly_bet
                    
                    # Apply constraints
                    bet_fraction = min(bet_fraction, self.max_bet_pct)
                    bet_amount = round(self.bankroll * bet_fraction, 0)
                    
                    if bet_amount >= 10:  # Minimum $10 bet
                        recommendations.append({
                            'entry_id': entry.id,
                            'horse_name': entry.horse.name,
                            'post_position': entry.post_position,
                            'bet_type': bet_type,
                            'current_odds': entry.current_odds,
                            'estimated_odds': odds,
                            'win_probability': ep['win_prob'],
                            'bet_probability': prob,
                            'edge': edge,
                            'bet_amount': bet_amount,
                            'expected_value': 1 + edge
                        })
                        
        # Sort by expected value and apply race limit
        recommendations.sort(key=lambda x: x['expected_value'], reverse=True)
        
        # Ensure total race bets don't exceed limit
        total_bet = sum(r['bet_amount'] for r in recommendations)
        max_race_bet = self.bankroll * self.max_race_pct
        
        if total_bet > max_race_bet:
            scale_factor = max_race_bet / total_bet
            for rec in recommendations:
                rec['bet_amount'] = round(rec['bet_amount'] * scale_factor, 0)
                
        # Filter out small bets after scaling
        recommendations = [r for r in recommendations if r['bet_amount'] >= 10]
        
        # Select best bet type per horse
        best_by_horse = {}
        for rec in recommendations:
            horse_name = rec['horse_name']
            if horse_name not in best_by_horse or rec['expected_value'] > best_by_horse[horse_name]['expected_value']:
                best_by_horse[horse_name] = rec
                
        return list(best_by_horse.values())
        
    def _calculate_entry_probability(self, entry: RaceEntry, race: Race) -> Optional[float]:
        """Calculate win probability based on available data"""
        # Get historical performance data
        horse_perfs = self.db.query(HistoricalPerformance).filter(
            HistoricalPerformance.horse_id == entry.horse_id
        ).order_by(HistoricalPerformance.race_date.desc()).limit(20).all()
        
        if len(horse_perfs) < 3:
            return None
            
        # Calculate base score from performance (70% weight)
        perf_score = self._calculate_performance_score(entry, horse_perfs, race)
        
        # Add market assessment (30% weight)
        if entry.current_odds and entry.current_odds > 0:
            market_prob = 1 / (entry.current_odds + 1)
            # Don't let market completely override performance
            market_score = market_prob * 0.3
        else:
            market_score = 0.1  # Default if no odds
            
        # Combine scores
        total_score = (perf_score * 0.7) + market_score
        
        # Convert to probability (ensure reasonable bounds)
        return min(max(total_score, 0.02), 0.5)
        
    def _calculate_performance_score(self, entry: RaceEntry, horse_perfs: List, race: Race) -> float:
        """Calculate performance-based score"""
        score = 0.0
        
        # Recent form (last 5 races)
        recent_perfs = horse_perfs[:5]
        if recent_perfs:
            avg_finish = np.mean([p.finish_position for p in recent_perfs])
            # Convert average finish to score (1st = 1.0, 10th = 0.1)
            finish_score = max(0, 1.1 - (avg_finish * 0.1))
            score += finish_score * 0.3
            
        # Win rate
        total_races = len(horse_perfs)
        wins = sum(1 for p in horse_perfs if p.finish_position == 1)
        win_rate = wins / total_races if total_races > 0 else 0
        score += win_rate * 0.25
        
        # Speed figures (if available)
        speed_figs = [p.speed_figure for p in recent_perfs if p.speed_figure]
        if speed_figs:
            avg_speed = np.mean(speed_figs)
            # Normalize around 80 as average
            speed_score = min(1.0, avg_speed / 80)
            score += speed_score * 0.15
            
        # Distance suitability
        distance_perfs = [p for p in horse_perfs if abs(p.distance - race.distance) < 0.25]
        if distance_perfs:
            dist_avg_finish = np.mean([p.finish_position for p in distance_perfs[:5]])
            dist_score = max(0, 1.1 - (dist_avg_finish * 0.1))
            score += dist_score * 0.1
            
        # Jockey win rate
        if entry.jockey_id:
            jockey_perfs = self.db.query(HistoricalPerformance).filter(
                HistoricalPerformance.jockey_id == entry.jockey_id
            ).limit(50).all()
            
            if jockey_perfs:
                jockey_wins = sum(1 for p in jockey_perfs if p.finish_position == 1)
                jockey_win_rate = jockey_wins / len(jockey_perfs)
                score += jockey_win_rate * 0.1
                
        # Trainer win rate
        if entry.trainer_id:
            trainer_perfs = self.db.query(HistoricalPerformance).filter(
                HistoricalPerformance.trainer_id == entry.trainer_id
            ).limit(50).all()
            
            if trainer_perfs:
                trainer_wins = sum(1 for p in trainer_perfs if p.finish_position == 1)
                trainer_win_rate = trainer_wins / len(trainer_perfs)
                score += trainer_win_rate * 0.1
                
        return score