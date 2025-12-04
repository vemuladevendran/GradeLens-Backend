import pandas as pd
class GenerateRubrics:
    def rubric_generation(self, rubric_file_csv):
        rubric = pd.read_csv(rubric_file_csv)

        criterion = rubric["Criterion"].unique().tolist()
        levels = rubric["Level"].unique().tolist()
        
        rubric_prompt = ""

        for c in criterion:
            weight = rubric[rubric["Criterion"]==c]["Weight"].values[0]
            rubric_prompt += f"- Criterion: {c} (Weight: {weight})"
            for l in levels:
                rubric[(rubric["Criterion"] == c) & (rubric["Level"] == l)]["Description"].values
                rubric_prompt += f"\n  - Level => {l}: {rubric[(rubric["Criterion"] == c) & (rubric["Level"] == l)]['Description'].values[0]}"
            rubric_prompt += "\n\n"

        return rubric_prompt