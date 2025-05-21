import random

suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
card_values = {r: i+2 for i, r in enumerate(ranks)}  # A = 14 for Ace, J = 11, Q = 12, K = 13,
# explaining the card values
#The enumerate function is used to assign a value to each rank, starting from 2 for '2' and going up to 14 for 'A'.
# The dictionary comprehension creates a mapping of ranks to their respective values.
# For example, '2' maps to 2, '3' maps to 3, ..., '10' maps to 10, 'J' maps to 11, 'Q' maps to 12, 'K' maps to 13, and 'A' maps to 14.
# This mapping is used to calculate the points for each card in a player's hand.
# The card values are used to determine the score of a player's hand, with higher ranks contributing more points.
# The values are used in the calculate_points function to sum up the points of a player's hand.

def create_deck():
    return [{'suit': s, 'rank': r} for s in suits for r in ranks] # Create a standard 52-card deck

def calculate_points(hand):
    return sum(card_values[c['rank']] for c in hand) # Calculate points based on card values. i.e 2-10 = 2-10, J = 11, Q = 12, K = 13, A = 14

