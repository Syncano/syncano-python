import os
import unittest
import xmlrunner


if __name__ == '__main__':
    output = os.path.join(os.getenv('CIRCLE_TEST_REPORTS', ''), 'junit')
    suite = unittest.TestLoader().discover('.')
    runner = xmlrunner.XMLTestRunner(output=output, verbosity=2,
                                     failfast=False, buffer=False)
    runner.run(suite)
