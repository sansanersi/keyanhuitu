class IllustrationEvaluator:
    def evaluate_all(self, required, actual, svg=""):
        completeness = len([e for e in actual if e.name in required]) / max(len(required),1) * 100
        return {"total_score": round(completeness, 1), "completeness": {"score": completeness}, "summary": {"total_score": completeness}}