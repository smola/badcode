

class Ranker:
    def __init__(self, scoring):
        self.scoring = scoring
        self.scores = {}
        self.percentiles = {}

    def add(self, element):
        score = self.scoring(element)
        self.scores[id(element)] = score
    
    def finalize(self):
        sorted_scores = sorted(self.scores.values())
        total = len(sorted_scores)
        for idx, score in enumerate(sorted_scores):
            if score in self.percentiles:
                continue
            below = len([1 for s in sorted_scores[:idx] if s < score])
            percentile = float(below) / total
            self.percentiles[score] = percentile

    def get(self, element):
        score = self.scores[id(element)]
        percentile = self.percentiles[score]
        return percentile
