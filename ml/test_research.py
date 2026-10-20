import copy
import unittest
import numpy as np
import pandas as pd
from research_data import FEATURES, PROTOCOL, features, causal_history, window_dataset


def fixture():
    start=pd.Timestamp("2020-01-01")
    return {"sourceParticipantId":"unit-test","researchContext":{"hba1c":5.5,"sex":"female"},
            "ehr":{},"series":[{"timestamp":(start+pd.Timedelta(minutes=5*i)).isoformat()+"Z",
                "sourceTimestamp":(start+pd.Timedelta(minutes=5*i-2)).isoformat()+"Z",
                "glucose":100+(i%12),"hr":70+i%3,"hrv":30+i%4,
                "quality":{"glucoseAgeMinutes":2}} for i in range(160)]}


class ResearchTests(unittest.TestCase):
    def test_future_prefix_invariance(self):
        patient=fixture()
        expected=features(patient,100)
        shortened=copy.deepcopy(patient);shortened["series"]=shortened["series"][:101]
        self.assertEqual(expected,features(shortened,100))
        for row in patient["series"][101:]:row.update(glucose=399,hr=200,hrv=250)
        self.assertEqual(expected,features(patient,100))
        self.assertEqual(set(expected),set(FEATURES))

    def test_gap_fill_is_past_only_and_bounded(self):
        patient=fixture()
        for row in patient["series"][99:101]:row["glucose"]=None
        history=causal_history(patient,100)
        self.assertEqual(history[-1]["glucose"],patient["series"][98]["glucose"])
        self.assertEqual(history[-1]["quality"]["glucoseAgeMinutes"],12)
        self.assertIsNone(patient["series"][100]["glucose"])
        for row in patient["series"][95:101]:row["glucose"]=None
        self.assertIsNone(causal_history(patient,100)[-1]["glucose"])

    def test_targets_actual_nearest_and_strictly_future(self):
        patient=fixture()
        times=np.array([pd.Timestamp(row["timestamp"]).timestamp() for row in patient["series"]])
        values=np.array([row["glucose"] for row in patient["series"]])
        data=window_dataset([patient],{"unit-test":(times,values)})
        for i,cursor in enumerate(data["cursors"]):
            now=times[cursor]
            np.testing.assert_array_equal(data["targetTimes"][i]-now,[1800,3600,5400,7200])
        # A future observation outside tolerance must not be invented/interpolated.
        shifted=times+151
        reduced=window_dataset([patient],{"unit-test":(shifted,values)})
        self.assertGreater(len(data["x"]),0)
        self.assertTrue(np.all(reduced["targetTimes"]>times[reduced["cursors"],None]))

    def test_participant_disjoint_and_unknown_sex_not_female(self):
        splits=list(PROTOCOL["splits"].values())
        self.assertEqual(len(set(sum(splits,[]))),sum(map(len,splits)))
        patient=fixture();patient["researchContext"]["sex"]=None
        self.assertIsNone(features(patient,100)["researchSexMale"])

    def test_missingness_only_tree_export_is_strict_json_and_exact(self):
        import json
        from sklearn.ensemble import HistGradientBoostingRegressor
        from train_research import export_tree
        x=np.array([[0.]]*30+[[np.nan]]*30)
        y=np.array([0.]*30+[100.]*30)
        model=HistGradientBoostingRegressor(max_iter=3,max_leaf_nodes=3,min_samples_leaf=5,
                                            early_stopping=False,random_state=1).fit(x,y)
        artifact=export_tree(model)
        json.dumps(artifact,allow_nan=False)
        inputs=np.array([[0.],[100.],[np.finfo(float).max],[np.nan]])
        outputs=[]
        for row in inputs:
            value=artifact["baseline"]
            for tree in artifact["trees"]:
                node=tree["nodes"][0]
                while node[0]!=-1:
                    left=node[5] if not np.isfinite(row[node[0]]) else row[node[0]]<=node[1]
                    node=tree["nodes"][node[2] if left else node[3]]
                value+=node[4]
            outputs.append(value)
        np.testing.assert_allclose(outputs,model.predict(inputs),rtol=0,atol=1e-12)


if __name__=="__main__":unittest.main()
