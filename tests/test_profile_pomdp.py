"""The POMDP belief update over profile conditions follows the stated equation and refuses bad models."""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from eri.profile_pomdp import belief_update, joint_conditions, predict


class BeliefUpdateTest(unittest.TestCase):
    def test_joint_conditions_keep_every_combination(self):
        states = joint_conditions({'supply': ('confirmed', 'unconfirmed'), 'interface': ('met', 'not_met', 'unknown')})
        self.assertEqual(len(states), 6)
        self.assertEqual(states[0], {'supply': 'confirmed', 'interface': 'met'})

    def test_information_action_changes_knowledge_not_condition(self):
        prior = np.array([.5, .5])
        review = np.eye(2)                       # a documentation review does not change the equipment
        posterior = belief_update(prior, review, [.9, .2])
        self.assertTrue(np.allclose(posterior, [.9 / 1.1, .2 / 1.1]))
        self.assertTrue(np.allclose(predict(prior, review), prior))

    def test_development_action_changes_condition(self):
        prior = np.array([0., 1.])               # [requirement met, not met]
        rework = np.array([[1., 0.], [.6, .4]])  # rework can move 'not met' to 'met'
        self.assertTrue(np.allclose(predict(prior, rework), [.6, .4]))
        self.assertTrue(np.allclose(belief_update(prior, rework, [1., 1.]), [.6, .4]))

    def test_invalid_models_fail_loudly(self):
        with self.assertRaises(ValueError):
            belief_update([.5, .6], np.eye(2), [1, 1])
        with self.assertRaises(ValueError):
            belief_update([.5, .5], [[.5, .4], [0, 1]], [1, 1])
        with self.assertRaises(ValueError):
            belief_update([1., 0.], np.eye(2), [0., 1.])   # observation impossible under the models
        with self.assertRaises(ValueError):
            joint_conditions({})


if __name__ == '__main__':
    unittest.main()
