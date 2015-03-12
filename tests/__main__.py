import unittest
import xmlrunner


if __name__ == '__main__':
    suite = unittest.TestLoader().discover('.')
    runner = xmlrunner.XMLTestRunner(output='reports', verbosity=2,
                                     failfast=False, buffer=False)
    runner.run(suite)
