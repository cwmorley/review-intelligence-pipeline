import unittest

from review_intelligence.statistics import beta_posterior, effective_sample_size, recency_weight


class StatisticsTests(unittest.TestCase):
    def test_uniform_prior_without_observations(self):
        estimate = beta_posterior([])
        self.assertAlmostEqual(estimate.mean, 0.5)
        self.assertAlmostEqual(estimate.lower, 0.025, places=3)
        self.assertAlmostEqual(estimate.upper, 0.975, places=3)

    def test_known_beta_posterior(self):
        estimate = beta_posterior([(True, 1), (True, 1), (False, 1)])
        self.assertEqual(estimate.alpha, 3)
        self.assertEqual(estimate.beta, 2)
        self.assertAlmostEqual(estimate.mean, 0.6)

    def test_effective_sample_size_and_half_life(self):
        self.assertEqual(effective_sample_size([1, 1, 1]), 3)
        self.assertAlmostEqual(recency_weight(365, 365), 0.5)


if __name__ == "__main__":
    unittest.main()

